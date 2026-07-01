from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.matches import team_players_as_dicts
from app.database import get_db
from app.models.team import Team
from app.prediction.model_config import DEFAULT_MODEL_CONFIG
from app.prediction.poisson_model import predict_match
from app.rate_limit import rate_limit
from app.schemas.prediction import MatchPredictionOut, MatchupBreakdownOut
from app.services.matchup_breakdown import build_matchup_breakdown

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

HOST_NATIONS = {"USA", "MEX", "CAN"}


@router.get("/{home_team_id}/{away_team_id}", response_model=MatchPredictionOut, dependencies=[Depends(rate_limit(30))])
def get_match_prediction(home_team_id: str, away_team_id: str, db: Session = Depends(get_db)):
    home_team = db.get(Team, home_team_id)
    away_team = db.get(Team, away_team_id)
    if home_team is None or away_team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    home_players = team_players_as_dicts(db, home_team_id)
    away_players = team_players_as_dicts(db, away_team_id)
    host_bump_home = DEFAULT_MODEL_CONFIG.host_advantage if home_team_id in HOST_NATIONS else 0.0
    host_bump_away = DEFAULT_MODEL_CONFIG.host_advantage if away_team_id in HOST_NATIONS else 0.0

    return predict_match(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_players=home_players,
        away_players=away_players,
        home_fifa_rank=home_team.fifa_rank,
        away_fifa_rank=away_team.fifa_rank,
        home_tactical_profile=home_team.tactical_profile,
        away_tactical_profile=away_team.tactical_profile,
        host_bump_home=host_bump_home,
        host_bump_away=host_bump_away,
    )


@router.get("/{home_team_id}/{away_team_id}/breakdown", response_model=MatchupBreakdownOut, dependencies=[Depends(rate_limit(30))])
def get_matchup_breakdown(home_team_id: str, away_team_id: str, db: Session = Depends(get_db)):
    home_team = db.get(Team, home_team_id)
    away_team = db.get(Team, away_team_id)
    if home_team is None or away_team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    home_players = team_players_as_dicts(db, home_team_id)
    away_players = team_players_as_dicts(db, away_team_id)
    host_bump_home = DEFAULT_MODEL_CONFIG.host_advantage if home_team_id in HOST_NATIONS else 0.0
    host_bump_away = DEFAULT_MODEL_CONFIG.host_advantage if away_team_id in HOST_NATIONS else 0.0

    return build_matchup_breakdown(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_players=home_players,
        away_players=away_players,
        home_fifa_rank=home_team.fifa_rank,
        away_fifa_rank=away_team.fifa_rank,
        home_formation=home_team.default_formation,
        away_formation=away_team.default_formation,
        home_tactical_profile=home_team.tactical_profile,
        away_tactical_profile=away_team.tactical_profile,
        host_bump_home=host_bump_home,
        host_bump_away=host_bump_away,
    )
