"""Externalized, named coefficients for the Poisson expected-goals model.

These weights are reasoned, conservative starting values -- they have NOT
yet been backtested against historical results (that calibration work is
explicitly future scope; see the project roadmap). Versioned via
`model_version` so any future tuning can be tracked and compared.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    model_version: str
    base_goals: float  # average goals for an evenly-matched team in a neutral fixture
    attack_diff_weight: float
    defense_diff_weight: float
    strength_diff_weight: float
    tactical_matchup_weight: float
    home_advantage: float  # small generic fixture-order edge (not host-nation specific)
    host_advantage: float  # additional bump for a team playing in its own host nation
    max_goals: int  # truncation point for the scoreline probability matrix


DEFAULT_MODEL_CONFIG = ModelConfig(
    model_version="poisson-v2-rank75",
    base_goals=1.35,
    attack_diff_weight=0.022,
    defense_diff_weight=0.022,
    strength_diff_weight=0.012,
    tactical_matchup_weight=0.10,
    home_advantage=0.05,
    host_advantage=0.18,
    max_goals=8,
)
