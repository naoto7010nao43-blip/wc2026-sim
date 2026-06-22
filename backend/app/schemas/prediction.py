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
