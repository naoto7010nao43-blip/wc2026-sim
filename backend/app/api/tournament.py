import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.match import Match
from app.schemas.match import MatchSummary
from app.schemas.tournament import ROUND_NAMES, RunTournamentRequest, TournamentResult
from app.services.standings import compute_standings
from app.services.tournament import GROUP_LETTERS, match_winner, run_full_tournament

router = APIRouter(prefix="/api/tournament", tags=["tournament"])

# A match is part of a tournament run (as opposed to an ad-hoc single match
# from Mode 2's /api/matches/simulate, which leaves both of these null) if
# it has a group_id (group stage) or a bracket_slot (knockout stage).
_TOURNAMENT_MATCH_FILTER = or_(Match.group_id.isnot(None), Match.bracket_slot.isnot(None))


def _group_standings(db: Session) -> dict:
    return {letter: compute_standings(db, letter) for letter in GROUP_LETTERS}


@router.post("/run", response_model=TournamentResult)
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
