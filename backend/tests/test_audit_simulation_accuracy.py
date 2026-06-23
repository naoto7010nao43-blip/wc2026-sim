import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_simulation_accuracy import (
    concentration_metrics,
    frequent_underperformers,
    host_advantage_delta,
    is_implausible_favorite,
    minimum_expected_win_pct,
)


def test_close_rank_gap_does_not_require_a_strong_favorite():
    # Two adjacently-ranked top teams playing a near-toss-up is normal
    # football -- this must NOT be flagged as implausible.
    assert is_implausible_favorite(39.5, rank_gap=1) is False


def test_large_rank_gap_requires_a_clearer_favorite():
    assert is_implausible_favorite(40.0, rank_gap=15) is True
    assert is_implausible_favorite(60.0, rank_gap=15) is False


def test_minimum_expected_win_pct_is_capped():
    assert minimum_expected_win_pct(0) == 33.0
    assert minimum_expected_win_pct(100) == 55.0


def test_host_advantage_delta_is_simple_difference():
    assert host_advantage_delta(55.0, 50.0) == 5.0
    assert host_advantage_delta(50.0, 50.0) == 0.0


def test_concentration_metrics_flags_too_concentrated():
    champion_pct = {"A": 40.0, "B": 10.0, "C": 5.0}
    metrics = concentration_metrics(champion_pct, total_teams=48)
    assert metrics["top1_champion_pct"] == 40.0
    assert metrics["assessment"] == "too_concentrated"


def test_concentration_metrics_flags_too_flat():
    champion_pct = {f"team_{i}": 100.0 / 48 for i in range(48)}
    metrics = concentration_metrics(champion_pct, total_teams=48)
    assert metrics["assessment"] == "too_flat"


def test_concentration_metrics_reasonable_distribution():
    champion_pct = {"A": 8.0, "B": 6.0, "C": 5.0, "D": 4.0, "E": 3.0}
    for i in range(20):
        champion_pct[f"team_{i}"] = 1.0
    metrics = concentration_metrics(champion_pct, total_teams=48)
    assert metrics["assessment"] == "reasonable"


def test_frequent_underperformers_requires_minimum_occurrences():
    warnings = [{"home_team_id": "NED"}, {"home_team_id": "NED"}, {"home_team_id": "CRO"}]
    assert frequent_underperformers(warnings, min_occurrences=3) == []
    assert frequent_underperformers(warnings, min_occurrences=2) == [{"team_id": "NED", "implausible_matchup_count": 2}]


def test_frequent_underperformers_sorted_by_count_descending():
    warnings = (
        [{"home_team_id": "NED"}] * 5
        + [{"home_team_id": "CRO"}] * 3
        + [{"home_team_id": "POR"}] * 3
    )
    result = frequent_underperformers(warnings, min_occurrences=3)
    assert [r["team_id"] for r in result][0] == "NED"
    assert {r["team_id"] for r in result} == {"NED", "CRO", "POR"}
