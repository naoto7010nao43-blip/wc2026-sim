from pydantic import BaseModel, Field


class MatchPredictionOut(BaseModel):
    home_team_id: str
    away_team_id: str
    home_win_pct: float
    draw_pct: float
    away_win_pct: float
    home_expected_goals: float
    away_expected_goals: float
    most_likely_scores: list[tuple[int, int, float]]
    data_confidence: str
    explanation: list[str]
    model_version: str
    disclaimer: str

    model_config = {"from_attributes": True}


class MatchupBreakdownFactorOut(BaseModel):
    key: str
    label: str
    home_value: float | None
    away_value: float | None
    edge: float
    edge_team_id: str | None
    model_impact: float
    description_ja: str


class MatchupBreakdownLineupOut(BaseModel):
    team_id: str
    formation: str
    starter_count: int
    avg_starting_probability: float | None
    low_probability_starter_count: int
    full_xi: bool


class MatchupBreakdownOut(BaseModel):
    home_team_id: str
    away_team_id: str
    favorite_team_id: str | None
    summary_ja: str
    factors: list[MatchupBreakdownFactorOut]
    lineups: list[MatchupBreakdownLineupOut]
    model_version: str
    disclaimer: str

    model_config = {"from_attributes": True}


class TournamentSimulationOut(BaseModel):
    iterations: int
    model_version: str
    round_of_32_pct: dict[str, float]
    round_of_16_pct: dict[str, float]
    quarterfinal_pct: dict[str, float]
    semifinal_pct: dict[str, float]
    final_pct: dict[str, float]
    champion_pct: dict[str, float]
    data_confidence: str
    explanation: list[str]
    disclaimer: str

    model_config = {"from_attributes": True}


class SimulateMonteCarloRequest(BaseModel):
    # Benchmarked at ~8ms/iteration (see test_monte_carlo_performance_benchmark);
    # 3000 is ~24s, the practical ceiling for a single synchronous request
    # before risking a platform request timeout.
    iterations: int = Field(default=1000, ge=100, le=3000)
    seed: int = 0


class TournamentUpsetWatchMatchOut(BaseModel):
    group_id: str
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    favorite_team_id: str
    underdog_team_id: str
    favorite_win_pct: float
    underdog_win_pct: float
    draw_pct: float
    upset_score: float
    expected_goal_gap: float
    model_version: str
    reason_ja: str


class TournamentUpsetWatchOut(BaseModel):
    match_count: int
    candidates: list[TournamentUpsetWatchMatchOut]
    model_version: str
    disclaimer: str


class GroupDifficultyTeamOut(BaseModel):
    team_id: str
    team_name: str
    fifa_rank: int | None
    strength_rating: float


class GroupDifficultyOut(BaseModel):
    group_id: str
    difficulty_score: float
    difficulty_band: str
    average_strength: float
    top_strength: float
    strength_spread: float
    average_favorite_gap_pct: float
    average_draw_pct: float
    upset_pressure: float
    top_team_id: str
    teams: list[GroupDifficultyTeamOut]
    reason_ja: str


class TournamentGroupDifficultyOut(BaseModel):
    group_count: int
    groups: list[GroupDifficultyOut]
    model_version: str
    disclaimer: str
