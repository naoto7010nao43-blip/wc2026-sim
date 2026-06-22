from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.matches import team_players_as_dicts
from app.database import get_db
from app.models.team import Team
from app.rating_v2.lineup_builder import build_likely_lineup
from app.schemas.team import LikelyLineupOut, TeamOut, TeamSummary

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=list[TeamSummary])
def list_teams(db: Session = Depends(get_db)):
    teams = db.scalars(select(Team)).all()
    return teams


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: str, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.get("/{team_id}/likely-lineup", response_model=LikelyLineupOut)
def get_likely_lineup(team_id: str, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    players = team_players_as_dicts(db, team_id)
    lineup = build_likely_lineup(players, team.default_formation)
    return LikelyLineupOut(team_id=team_id, formation=team.default_formation, lineup=lineup)
