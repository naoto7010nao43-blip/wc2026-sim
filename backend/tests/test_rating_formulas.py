import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rating.formulas import (
    StageAInputs,
    apply_pipeline,
    clamp,
    compute_overall,
    percentile_rank,
    stage_a_raw_attributes,
)


def make_inputs(**overrides) -> StageAInputs:
    base = dict(
        position_group="FWD",
        age=25,
        goals_per90=0.3,
        assists_per90=0.2,
        key_passes_per90=1.0,
        successful_dribbles_per90=1.0,
        tackles_per90=0.5,
        interceptions_per90=0.3,
        aerial_duels_won_pct=45.0,
        pass_completion_pct=80.0,
        minutes_per_appearance=75.0,
    )
    base.update(overrides)
    return StageAInputs(**base)


def test_clamp_bounds():
    assert clamp(150) == 99
    assert clamp(-50) == 0
    assert clamp(50) == 50


def test_stage_a_outputs_within_bounds_for_extreme_inputs():
    low = stage_a_raw_attributes(make_inputs(
        goals_per90=0, assists_per90=0, key_passes_per90=0,
        successful_dribbles_per90=0, tackles_per90=0, interceptions_per90=0,
        aerial_duels_won_pct=0, pass_completion_pct=40, age=40,
    ))
    high = stage_a_raw_attributes(make_inputs(
        goals_per90=5, assists_per90=5, key_passes_per90=10,
        successful_dribbles_per90=10, tackles_per90=10, interceptions_per90=10,
        aerial_duels_won_pct=100, pass_completion_pct=100, age=20,
    ))
    for attrs in (low, high):
        for v in attrs.values():
            assert 0 <= v <= 99


def test_percentile_rank_basic():
    population = [10, 20, 30, 40, 50]
    assert percentile_rank(30, population) == 0.5
    assert percentile_rank(10, population) == 0.1
    assert percentile_rank(50, population) == 0.9


def test_apply_pipeline_respects_qualitative_cap():
    stage_a = {"pace": 50.0, "shooting": 50.0, "passing": 50.0, "dribbling": 50.0, "defending": 50.0, "physical": 50.0}
    # Even with an absurd qualitative adjustment request, output must stay capped to +/-6 before the market modifier.
    result = apply_pipeline(stage_a, market_value_percentile=0.5, qualitative_adjustments={"pace": 99})
    assert result["pace"] <= 56


def test_compute_overall_within_bounds():
    attrs = {"pace": 90, "shooting": 90, "passing": 90, "dribbling": 90, "defending": 90, "physical": 90}
    assert 0 <= compute_overall(attrs, "ST") <= 99
    attrs_low = {"pace": 10, "shooting": 10, "passing": 10, "dribbling": 10, "defending": 10, "physical": 10}
    assert 0 <= compute_overall(attrs_low, "CB") <= 99
