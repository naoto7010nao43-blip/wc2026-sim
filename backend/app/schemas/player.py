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
    # Rating trust/provenance metadata (v2 rating model) -- None/[] for
    # players seeded before this metadata existed, never fabricated.
    starting_probability: float | None = None
    data_confidence: str | None = None
    uncertainty: float | None = None
    source_breakdown: dict | None = None
    low_confidence_attributes: list[str] = []
    rating_last_updated: str | None = None

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
    starting_probability: float | None = None
    data_confidence: str | None = None
    uncertainty: float | None = None
    source_breakdown: dict | None = None
    low_confidence_attributes: list[str] = []
    rating_last_updated: str | None = None

    model_config = {"from_attributes": True}
