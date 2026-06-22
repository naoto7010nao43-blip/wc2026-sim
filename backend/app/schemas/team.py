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


class LikelyLineupSlot(BaseModel):
    slot_position: str
    player_id: str
    name: str
    name_ja: str | None = None
    primary_position: str
    starting_probability: float


class LikelyLineupOut(BaseModel):
    team_id: str
    formation: str
    lineup: list[LikelyLineupSlot]
    disclaimer: str = (
        "これは公式発表のスタメンではなく、出場時間・市場価値・能力値から推定した予測です。"
    )
