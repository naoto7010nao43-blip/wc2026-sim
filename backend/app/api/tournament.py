import itertools
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.matches import team_players_as_dicts
from app.database import get_db
from app.models.match import Match
from app.models.team import Team
from app.prediction.monte_carlo import simulate_tournament_outcomes
from app.prediction.model_config import DEFAULT_MODEL_CONFIG
from app.prediction.poisson_model import predict_match
from app.rate_limit import rate_limit
from app.schemas.match import MatchSummary
from app.schemas.prediction import (
    SimulateMonteCarloRequest,
    TournamentSimulationOut,
    TournamentUpsetWatchMatchOut,
    TournamentUpsetWatchOut,
)
from app.schemas.tournament import ROUND_NAMES, RunTournamentRequest, TournamentResult
from app.services.standings import compute_standings
from app.services.tournament import GROUP_LETTERS, match_winner, run_full_tournament

router = APIRouter(prefix="/api/tournament", tags=["tournament"])
HOST_NATIONS = {"USA", "MEX", "CAN"}

# A match is part of a tournament run (as opposed to an ad-hoc single match
# from Mode 2's /api/matches/simulate, which leaves both of these null) if
# it has a group_id (group stage) or a bracket_slot (knockout stage).
_TOURNAMENT_MATCH_FILTER = or_(Match.group_id.isnot(None), Match.bracket_slot.isnot(None))


def _group_standings(db: Session) -> dict:
    return {letter: compute_standings(db, letter) for letter in GROUP_LETTERS}


@router.post("/run", response_model=TournamentResult, dependencies=[Depends(rate_limit(6))])
def run_tournament(req: RunTournamentRequest, db: Session = Depends(get_db)):
    # Each run starts a fresh tournament: clear matches left over from a
    # previous run so /state always reflects exactly one tournament's worth.
    # Ad-hoc single matches from Mode 2 are left alone so their shareable
    # /matches/:id links keep working.
    db.query(Match).filter(_TOURNAMENT_MATCH_FILTER).delete(synchronize_session=False)
    db.commit()

    base_seed = req.seed if req.seed is not None else uuid.uuid4().int & 0xFFFFFFFF
    result = run_full_tournament(db, base_seed=base_seed)

    return TournamentResult(
        champion_team_id=result["champion_team_id"],
        qualifying_third_groups=result["qualifying_third_groups"],
        matches={
            round_name: [MatchSummary.model_validate(m) for m in result["matches"][round_name]]
            for round_name in ROUND_NAMES
        },
        group_standings=result["group_standings"],
    )


@router.post("/simulate-monte-carlo", response_model=TournamentSimulationOut, dependencies=[Depends(rate_limit(3))])
def simulate_monte_carlo(req: SimulateMonteCarloRequest, db: Session = Depends(get_db)):
    return simulate_tournament_outcomes(db, iterations=req.iterations, base_seed=req.seed)


def _upset_reason(underdog_win_pct: float, draw_pct: float, expected_goal_gap: float) -> str:
    if expected_goal_gap <= 0.15:
        return "期待得点差がかなり小さく、モデル上は実力差より展開差が出やすいカードです。"
    if underdog_win_pct >= 30:
        return "格下側にも明確な勝ち筋があり、単純な順位差だけでは読みにくいカードです。"
    if draw_pct >= 29:
        return "引き分け確率が高く、終盤の一点やPK相当の分岐で結果が揺れやすいカードです。"
    return "本命が優位ですが、相手側の勝率も残っており取りこぼし候補として監視できます。"


@router.get("/upset-watch", response_model=TournamentUpsetWatchOut, dependencies=[Depends(rate_limit(20))])
def get_tournament_upset_watch(
    limit: int = Query(default=12, ge=1, le=24),
    db: Session = Depends(get_db),
):
    teams = db.scalars(select(Team).where(Team.group_id.isnot(None)).order_by(Team.group_id, Team.id)).all()
    teams_by_group: dict[str, list[Team]] = {}
    for team in teams:
        teams_by_group.setdefault(team.group_id, []).append(team)

    candidates: list[TournamentUpsetWatchMatchOut] = []
    model_version = DEFAULT_MODEL_CONFIG.model_version
    disclaimer = ""

    for group_id in GROUP_LETTERS:
        group_teams = teams_by_group.get(group_id, [])
        if len(group_teams) != 4:
            continue
        for home_team, away_team in itertools.combinations(group_teams, 2):
            host_bump_home = DEFAULT_MODEL_CONFIG.host_advantage if home_team.id in HOST_NATIONS else 0.0
            host_bump_away = DEFAULT_MODEL_CONFIG.host_advantage if away_team.id in HOST_NATIONS else 0.0
            prediction = predict_match(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_players=team_players_as_dicts(db, home_team.id),
                away_players=team_players_as_dicts(db, away_team.id),
                home_fifa_rank=home_team.fifa_rank,
                away_fifa_rank=away_team.fifa_rank,
                home_tactical_profile=home_team.tactical_profile,
                away_tactical_profile=away_team.tactical_profile,
                host_bump_home=host_bump_home,
                host_bump_away=host_bump_away,
            )
            model_version = prediction.model_version
            disclaimer = prediction.disclaimer
            home_is_favorite = prediction.home_win_pct >= prediction.away_win_pct
            favorite_win_pct = prediction.home_win_pct if home_is_favorite else prediction.away_win_pct
            underdog_win_pct = prediction.away_win_pct if home_is_favorite else prediction.home_win_pct
            favorite_team = home_team if home_is_favorite else away_team
            underdog_team = away_team if home_is_favorite else home_team
            expected_goal_gap = round(abs(prediction.home_expected_goals - prediction.away_expected_goals), 2)
            upset_score = round(underdog_win_pct + prediction.draw_pct * 0.35, 1)
            candidates.append(
                TournamentUpsetWatchMatchOut(
                    group_id=group_id,
                    home_team_id=home_team.id,
                    home_team_name=home_team.name,
                    away_team_id=away_team.id,
                    away_team_name=away_team.name,
                    favorite_team_id=favorite_team.id,
                    underdog_team_id=underdog_team.id,
                    favorite_win_pct=favorite_win_pct,
                    underdog_win_pct=underdog_win_pct,
                    draw_pct=prediction.draw_pct,
                    upset_score=upset_score,
                    expected_goal_gap=expected_goal_gap,
                    model_version=prediction.model_version,
                    reason_ja=_upset_reason(underdog_win_pct, prediction.draw_pct, expected_goal_gap),
                )
            )

    candidates.sort(key=lambda row: (-row.upset_score, -row.underdog_win_pct, -row.draw_pct, row.group_id))
    return TournamentUpsetWatchOut(
        match_count=len(candidates),
        candidates=candidates[:limit],
        model_version=model_version,
        disclaimer=disclaimer,
    )


@router.get("/state", response_model=TournamentResult | None)
def get_tournament_state(db: Session = Depends(get_db)):
    matches_by_round = {round_name: [] for round_name in ROUND_NAMES}
    all_matches = db.scalars(
        select(Match).where(_TOURNAMENT_MATCH_FILTER).order_by(Match.played_at)
    ).all()
    if not all_matches:
        return None

    for m in all_matches:
        matches_by_round.setdefault(m.round, []).append(m)

    final_matches = matches_by_round.get("FINAL", [])
    champion_team_id = match_winner(final_matches[-1]) if final_matches else None

    return TournamentResult(
        champion_team_id=champion_team_id,
        qualifying_third_groups=None,
        matches={
            round_name: [MatchSummary.model_validate(m) for m in matches_by_round[round_name]]
            for round_name in ROUND_NAMES
        },
        group_standings=_group_standings(db),
    )
