import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_simulation_stability_audit import (
    compare_champion_sets,
    pct_delta,
    stability_band,
    top_entries,
)


def test_top_entries_sorts_by_probability_then_team_id():
    values = {"B": 10.0, "A": 10.0, "C": 12.0}
    assert top_entries(values, limit=2) == [
        {"team_id": "C", "pct": 12.0},
        {"team_id": "A", "pct": 10.0},
    ]


def test_pct_delta_treats_missing_as_zero_and_rounds():
    assert pct_delta(10.04, 12.08) == 2.0
    assert pct_delta(None, 3.2) == 3.2
    assert pct_delta(4.4, None) == -4.4


def test_compare_champion_sets_reports_largest_movers():
    comparison = compare_champion_sets(
        {"ARG": 18.0, "BRA": 10.0},
        {"ARG": 15.0, "BRA": 14.0},
        {"ARG", "BRA"},
    )
    assert comparison["max_abs_delta_pct"] == 4.0
    assert comparison["average_abs_delta_pct"] == 3.5
    assert comparison["largest_movers"][0]["team_id"] == "BRA"


def test_stability_band_thresholds():
    assert stability_band(2.0) == "stable"
    assert stability_band(4.0) == "usable"
    assert stability_band(4.1) == "volatile"
