import itertools
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.matches import team_players_as_dicts
from app.database import get_db
from app.models.match import Match
from app.models.team import Team
from app.prediction.monte_carlo import project_final_matchups, project_team_tournament_path, simulate_tournament_outcomes
from app.prediction.model_config import DEFAULT_MODEL_CONFIG
from app.prediction.poisson_model import predict_match
from app.prediction.ratings import team_strength_rating
from app.rate_limit import rate_limit
from app.schemas.match import MatchSummary
from app.schemas.prediction import (
    GroupDifficultyOut,
    GroupDifficultyTeamOut,
    SimulateMonteCarloRequest,
    TournamentGroupDifficultyOut,
    TournamentFinalMatchupsOut,
    TournamentPathProjectionOut,
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


@router.get("/path-projection", response_model=TournamentPathProjectionOut, dependencies=[Depends(rate_limit(12))])
def get_tournament_path_projection(
    team_id: str = Query(..., min_length=2, max_length=3),
    iterations: int = Query(default=1000, ge=100, le=3000),
    seed: int = Query(default=0),
    db: Session = Depends(get_db),
):
    try:
        return project_team_tournament_path(db, team_id=team_id.upper(), iterations=iterations, base_seed=seed)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found") from exc


@router.get("/final-matchups", response_model=TournamentFinalMatchupsOut, dependencies=[Depends(rate_limit(12))])
def get_tournament_final_matchups(
    iterations: int = Query(default=1000, ge=100, le=3000),
    seed: int = Query(default=0),
    limit: int = Query(default=8, ge=1, le=16),
    db: Session = Depends(get_db),
):
    return project_final_matchups(db, iterations=iterations, base_seed=seed, limit=limit)


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


def _group_difficulty_band(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 65:
        return "medium"
    return "low"


def _group_difficulty_reason(group: GroupDifficultyOut) -> str:
    if group.difficulty_band == "high":
        return "平均戦力が高く、カードごとの勝率差も小さいため、順位変動が起きやすいグループです。"
    if group.average_favorite_gap_pct <= 9:
        return "突出した本命が少なく、直接対決の一試合で通過順が大きく変わりやすいグループです。"
    if group.upset_pressure >= 40:
        return "本命は存在しますが、格下側の勝率と引き分け確率が高く、取りこぼしの圧力があります。"
    return "上位候補は比較的見えていますが、通過順位や3位争いでは細かい分岐が残るグループです。"


@router.get("/group-difficulty", response_model=TournamentGroupDifficultyOut, dependencies=[Depends(rate_limit(20))])
def get_tournament_group_difficulty(db: Session = Depends(get_db)):
    teams = db.scalars(select(Team).where(Team.group_id.isnot(None)).order_by(Team.group_id, Team.id)).all()
    teams_by_group: dict[str, list[Team]] = {}
    players_by_team = {team.id: team_players_as_dicts(db, team.id) for team in teams}
    for team in teams:
        teams_by_group.setdefault(team.group_id or "", []).append(team)

    groups: list[GroupDifficultyOut] = []
    model_version = DEFAULT_MODEL_CONFIG.model_version
    disclaimer = "これは既存のチーム強度と試合前予測から作った比較指標であり、実際の順位を保証するものではありません。"

    for group_id in GROUP_LETTERS:
        group_teams = teams_by_group.get(group_id, [])
        if len(group_teams) != 4:
            continue

        team_rows: list[GroupDifficultyTeamOut] = []
        for team in group_teams:
            strength, _confidence = team_strength_rating(team.fifa_rank, players_by_team[team.id])
            team_rows.append(
                GroupDifficultyTeamOut(
                    team_id=team.id,
                    team_name=team.name,
                    fifa_rank=team.fifa_rank,
                    strength_rating=round(strength, 1),
                )
            )
        team_rows.sort(key=lambda row: (-row.strength_rating, row.fifa_rank or 999, row.team_id))

        favorite_gaps: list[float] = []
        draw_pcts: list[float] = []
        upset_scores: list[float] = []
        for home_team, away_team in itertools.combinations(group_teams, 2):
            host_bump_home = DEFAULT_MODEL_CONFIG.host_advantage if home_team.id in HOST_NATIONS else 0.0
            host_bump_away = DEFAULT_MODEL_CONFIG.host_advantage if away_team.id in HOST_NATIONS else 0.0
            prediction = predict_match(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_players=players_by_team[home_team.id],
                away_players=players_by_team[away_team.id],
                home_fifa_rank=home_team.fifa_rank,
                away_fifa_rank=away_team.fifa_rank,
                home_tactical_profile=home_team.tactical_profile,
                away_tactical_profile=away_team.tactical_profile,
                host_bump_home=host_bump_home,
                host_bump_away=host_bump_away,
            )
            model_version = prediction.model_version
            favorite_gaps.append(abs(prediction.home_win_pct - prediction.away_win_pct))
            draw_pcts.append(prediction.draw_pct)
            upset_scores.append(min(prediction.home_win_pct, prediction.away_win_pct) + prediction.draw_pct * 0.35)

        strengths = [row.strength_rating for row in team_rows]
        average_strength = sum(strengths) / len(strengths)
        average_favorite_gap = sum(favorite_gaps) / len(favorite_gaps)
        average_draw_pct = sum(draw_pcts) / len(draw_pcts)
        upset_pressure = sum(upset_scores) / len(upset_scores)
        difficulty_score = round(
            average_strength + max(0.0, 18.0 - average_favorite_gap) * 0.7 + upset_pressure * 0.18,
            1,
        )

        row = GroupDifficultyOut(
            group_id=group_id,
            difficulty_score=difficulty_score,
            difficulty_band=_group_difficulty_band(difficulty_score),
            average_strength=round(average_strength, 1),
            top_strength=round(max(strengths), 1),
            strength_spread=round(max(strengths) - min(strengths), 1),
            average_favorite_gap_pct=round(average_favorite_gap, 1),
            average_draw_pct=round(average_draw_pct, 1),
            upset_pressure=round(upset_pressure, 1),
            top_team_id=team_rows[0].team_id,
            teams=team_rows,
            reason_ja="",
        )
        row.reason_ja = _group_difficulty_reason(row)
        groups.append(row)

    groups.sort(key=lambda row: (-row.difficulty_score, row.group_id))
    return TournamentGroupDifficultyOut(
        group_count=len(groups),
        groups=groups,
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
