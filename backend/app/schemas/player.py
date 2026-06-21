from enum import Enum

from pydantic import BaseModel


class PositionCode(str, Enum):
    GK = "GK"
    CB = "CB"
    LB = "LB"
    RB = "RB"
    CDM = "CDM"
    CM = "CM"
    CAM = "CAM"
    LM = "LM"
    RM = "RM"
    LW = "LW"
    RW = "RW"
    ST = "ST"


class PlayerAttributes(BaseModel):
    pace: int
    shooting: int
    passing: int
    dribbling: int
    defending: int
    physical: int
    gk_reflexes: int | None = None
    gk_handling: int | None = None


class PlayerSummary(BaseModel):
    id: str
    name: str
    name_ja: str | None = None
    age: int
    primary_position: str
    overall: int

    model_config = {"from_attributes": True}


class PlayerOut(BaseModel):
    id: str
    team_id: str
    name: str
    name_ja: str | None = None
    age: int
    primary_position: str
    secondary_positions: list[str]
    overall: int
    attributes: PlayerAttributes
    stamina_max: int
    source_notes: str | None = None

    model_config = {"from_attributes": True}
