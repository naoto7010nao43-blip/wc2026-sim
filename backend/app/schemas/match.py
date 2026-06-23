from datetime import datetime

from pydantic import BaseModel, Field


class SimulateMatchRequest(BaseModel):
    home_team_id: str
    away_team_id: str
    home_formation: str | None = None
    away_formation: str | None = None
    seed: int | None = None
    group_id: str | None = None
    round: str = "group"
    bracket_slot: str | None = None
    allow_draw: bool = True


class MatchEventOut(BaseModel):
    minute: int
    event_type: str
    team_id: str
    player_id: str | None
    secondary_player_id: str | None
    x: float | None
    y: float | None
    description: str
    event_metadata: dict | None = None

    model_config = {"from_attributes": True}


class MatchSummary(BaseModel):
    id: str
    group_id: str | None
    round: str
    bracket_slot: str | None
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int
    went_to_penalties: bool
    penalty_home_score: int | None
    penalty_away_score: int | None
    status: str
    played_at: datetime
    is_real: bool = False
    data_source: str | None = None

    model_config = {"from_attributes": True}


class LineupPlayer(BaseModel):
    player_id: str
    name: str
    slot_position: str
    x: float
    y: float


class PlayerRating(BaseModel):
    player_id: str
    name: str
    team_id: str
    rating: float
    is_mom: bool
    is_estimated: bool = False


class TurningPoint(BaseModel):
    minute: int
    team_id: str
    description: str


class MomentumSegment(BaseModel):
    start_minute: int
    end_minute: int
    home_actions: int
    away_actions: int
    dominant_team_id: str | None


class KeyPlayerContribution(BaseModel):
    player_id: str
    name: str
    team_id: str
    rating: float
    is_mom: bool


class MatchAnalysis(BaseModel):
    turning_point: TurningPoint | None
    momentum_segments: list[MomentumSegment]
    key_players: list[KeyPlayerContribution]
    tactical_note: str


class MatchResult(MatchSummary):
    home_formation: str
    away_formation: str
    home_lineup: list[LineupPlayer] = []
    away_lineup: list[LineupPlayer] = []
    seed: int | None
    events: list[MatchEventOut]
    home_possession_pct: float | None = None
    away_possession_pct: float | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_shots_on_target: int | None = None
    away_shots_on_target: int | None = None
    home_yellow_cards: int | None = None
    away_yellow_cards: int | None = None
    home_red_cards: int | None = None
    away_red_cards: int | None = None
    player_ratings: list[PlayerRating] = []
    analysis: MatchAnalysis | None = None


class SimulateRoundRobinRequest(BaseModel):
    # Real groups have 4 teams; capped well above that (combinations grow
    # O(n^2)) so a malicious request can't force the server into simulating
    # an unbounded number of matches in one call.
    team_ids: list[str] = Field(min_length=2, max_length=8)
    seed: int | None = None
