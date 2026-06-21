import itertools

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.matches import run_and_persist_match, to_match_result
from app.database import get_db
from app.models.match import Match
from app.rate_limit import rate_limit
from app.schemas.match import MatchResult, MatchSummary, SimulateMatchRequest, SimulateRoundRobinRequest
from app.schemas.standings import StandingsRow
from app.services.standings import compute_standings

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.post("/{group_id}/simulate-round-robin", response_model=dict, dependencies=[Depends(rate_limit(10))])
def simulate_round_robin(group_id: str, req: SimulateRoundRobinRequest, db: Session = Depends(get_db)):
    base_seed = req.seed if req.seed is not None else 0
    results: list[MatchResult] = []

    for i, (home_id, away_id) in enumerate(itertools.combinations(req.team_ids, 2)):
        match_seed = base_seed + i
        match_req = SimulateMatchRequest(
            home_team_id=home_id,
            away_team_id=away_id,
            seed=match_seed,
            group_id=group_id,
        )
        match = run_and_persist_match(db, match_req)
        results.append(to_match_result(db, match))

    standings = compute_standings(db, group_id)
    return {
        "matches": [MatchSummary.model_validate(m) for m in results],
        "standings": standings,
    }


@router.get("/{group_id}/standings", response_model=list[StandingsRow])
def get_standings(group_id: str, db: Session = Depends(get_db)):
    return compute_standings(db, group_id)


@router.get("/{group_id}/matches", response_model=list[MatchSummary])
def get_group_matches(group_id: str, db: Session = Depends(get_db)):
    matches = db.scalars(
        select(Match).where(Match.group_id == group_id).order_by(Match.played_at)
    ).all()
    return matches
