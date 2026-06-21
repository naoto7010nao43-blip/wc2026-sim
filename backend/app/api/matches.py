import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.engine.simulator import simulate_match
from app.models.match import Match, MatchEvent
from app.models.player import Player
from app.models.team import Team
from app.schemas.match import MatchEventOut, MatchResult, SimulateMatchRequest
from app.services.player_ratings import compute_player_ratings

router = APIRouter(prefix="/api/matches", tags=["matches"])


def _team_players_as_dicts(db: Session, team_id: str) -> list[dict]:
    players = db.scalars(select(Player).where(Player.team_id == team_id)).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "name_ja": p.name_ja,
            "primary_position": p.primary_position,
            "secondary_positions": p.secondary_positions,
            "overall": p.overall,
            "attributes": p.attributes,
            "stamina_max": p.stamina_max,
        }
        for p in players
    ]


def run_and_persist_match(db: Session, req: SimulateMatchRequest) -> Match:
    home_team = db.get(Team, req.home_team_id)
    away_team = db.get(Team, req.away_team_id)
    if home_team is None or away_team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    home_formation = req.home_formation or home_team.default_formation
    away_formation = req.away_formation or away_team.default_formation
    seed = req.seed if req.seed is not None else uuid.uuid4().int & 0xFFFFFFFF

    home_players = _team_players_as_dicts(db, req.home_team_id)
    away_players = _team_players_as_dicts(db, req.away_team_id)
    if len(home_players) < 11 or len(away_players) < 11:
        raise HTTPException(status_code=400, detail="Both teams need at least 11 players")

    result = simulate_match(
        home_team_id=req.home_team_id,
        away_team_id=req.away_team_id,
        home_players=home_players,
        away_players=away_players,
        home_formation=home_formation,
        away_formation=away_formation,
        seed=seed,
        allow_draw=req.allow_draw,
        home_tactical_profile=home_team.tactical_profile,
        away_tactical_profile=away_team.tactical_profile,
    )

    match = Match(
        id=str(uuid.uuid4()),
        group_id=req.group_id,
        round=req.round,
        bracket_slot=req.bracket_slot,
        home_team_id=req.home_team_id,
        away_team_id=req.away_team_id,
        home_formation=home_formation,
        away_formation=away_formation,
        home_lineup=result["home_lineup"],
        away_lineup=result["away_lineup"],
        home_roster=result["home_roster"],
        away_roster=result["away_roster"],
        home_score=result["home_score"],
        away_score=result["away_score"],
        went_to_penalties=result["went_to_penalties"],
        penalty_home_score=result["penalty_home_score"],
        penalty_away_score=result["penalty_away_score"],
        status="completed",
        seed=seed,
        home_possession_pct=result["home_possession_pct"],
        away_possession_pct=result["away_possession_pct"],
        home_shots=result["home_shots"],
        away_shots=result["away_shots"],
        home_shots_on_target=result["home_shots_on_target"],
        away_shots_on_target=result["away_shots_on_target"],
        home_yellow_cards=result["home_yellow_cards"],
        away_yellow_cards=result["away_yellow_cards"],
    )
    db.add(match)
    for e in result["events"]:
        db.add(MatchEvent(match_id=match.id, **e))
    db.commit()
    db.refresh(match)
    return match


def to_match_result(db: Session, match: Match) -> MatchResult:
    events = db.scalars(
        select(MatchEvent).where(MatchEvent.match_id == match.id).order_by(MatchEvent.id)
    ).all()
    player_ratings = compute_player_ratings(
        [
            {
                "event_type": e.event_type,
                "player_id": e.player_id,
                "secondary_player_id": e.secondary_player_id,
                "event_metadata": e.event_metadata,
            }
            for e in events
        ],
        match.home_roster or {},
        match.away_roster or {},
        match.home_team_id,
        match.away_team_id,
    )
    return MatchResult(
        id=match.id,
        group_id=match.group_id,
        round=match.round,
        bracket_slot=match.bracket_slot,
        home_team_id=match.home_team_id,
        away_team_id=match.away_team_id,
        home_score=match.home_score,
        away_score=match.away_score,
        went_to_penalties=match.went_to_penalties,
        penalty_home_score=match.penalty_home_score,
        penalty_away_score=match.penalty_away_score,
        status=match.status,
        played_at=match.played_at,
        home_formation=match.home_formation,
        away_formation=match.away_formation,
        home_lineup=match.home_lineup or [],
        away_lineup=match.away_lineup or [],
        seed=match.seed,
        events=[MatchEventOut.model_validate(e) for e in events],
        is_real=match.is_real,
        data_source=match.data_source,
        home_possession_pct=match.home_possession_pct,
        away_possession_pct=match.away_possession_pct,
        home_shots=match.home_shots,
        away_shots=match.away_shots,
        home_shots_on_target=match.home_shots_on_target,
        away_shots_on_target=match.away_shots_on_target,
        home_yellow_cards=match.home_yellow_cards,
        away_yellow_cards=match.away_yellow_cards,
        player_ratings=player_ratings,
    )


@router.post("/simulate", response_model=MatchResult)
def simulate(req: SimulateMatchRequest, db: Session = Depends(get_db)):
    match = run_and_persist_match(db, req)
    return to_match_result(db, match)


@router.get("/{match_id}", response_model=MatchResult)
def get_match(match_id: str, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return to_match_result(db, match)


@router.get("/{match_id}/events", response_model=list[MatchEventOut])
def get_match_events(match_id: str, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    events = db.scalars(
        select(MatchEvent).where(MatchEvent.match_id == match_id).order_by(MatchEvent.id)
    ).all()
    return events
