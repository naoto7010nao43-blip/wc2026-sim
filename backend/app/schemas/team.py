from pydantic import BaseModel

from app.schemas.player import PlayerSummary


class TeamSummary(BaseModel):
    id: str
    name: str
    confederation: str
    fifa_rank: int | None
    default_formation: str
    group_id: str | None = None
    tactical_profile: dict | None = None

    model_config = {"from_attributes": True}


class TeamOut(TeamSummary):
    players: list[PlayerSummary]
