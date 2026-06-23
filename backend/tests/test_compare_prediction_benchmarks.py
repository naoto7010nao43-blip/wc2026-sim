import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from compare_prediction_benchmarks import (
    compare_rank_gap_buckets,
    compare_reports,
    compare_watchlist,
    delta,
    evaluate_change,
)


def sample_report(avg=48.0, implausible=10, watch_implausible=5):
    return {
        "generatedAt": "now",
        "modelVersion": "test",
        "overallSummary": {
            "matchup_count": 2,
            "average_favorite_win_pct": avg,
            "minimum_favorite_win_pct": 30.0,
            "maximum_favorite_win_pct": 60.0,
            "implausible_favorite_count": implausible,
        },
        "rankGapBuckets": [
            {
                "rank_gap_bucket": "00-02",
                "matchup_count": 1,
                "average_favorite_win_pct": avg - 5,
                "implausible_favorite_count": 1,
            },
            {
                "rank_gap_bucket": "03-05",
                "matchup_count": 1,
                "average_favorite_win_pct": avg + 5,
                "implausible_favorite_count": 2,
            },
        ],
        "watchlistTeams": [
            {
                "team_id": "CRO",
                "average_favorite_win_pct": 35.0,
                "minimum_favorite_win_pct": 25.0,
                "implausible_favorite_count": watch_implausible,
            }
        ],
    }


def test_delta_handles_numbers_and_missing_values():
    assert delta(50.4, 48.1) == 2.3
    assert delta(None, 48.1) is None
    assert delta(50.4, None) is None


def test_compare_rank_gap_buckets_includes_bucket_deltas():
    before = sample_report(avg=48.0)
    after = sample_report(avg=50.0)
    rows = compare_rank_gap_buckets(before, after)
    assert rows[0]["rank_gap_bucket"] == "00-02"
    assert rows[0]["average_favorite_win_pct_delta"] == 2.0


def test_compare_watchlist_reports_implausible_reduction():
    before = sample_report(watch_implausible=5)
    after = sample_report(watch_implausible=2)
    rows = compare_watchlist(before, after)
    assert rows[0]["team_id"] == "CRO"
    assert rows[0]["implausible_favorite_count_delta"] == -3.0


def test_evaluate_change_passes_when_watchlist_improves_without_global_shift():
    comparison = compare_reports(sample_report(avg=48.0, watch_implausible=5), sample_report(avg=49.0, watch_implausible=3))
    assert comparison["evaluation"]["status"] == "pass"
    assert comparison["evaluation"]["watchlist_implausible_reduction"] == 2.0


def test_evaluate_change_warns_on_global_shift():
    comparison = compare_reports(sample_report(avg=48.0, watch_implausible=5), sample_report(avg=55.0, watch_implausible=3))
    assert comparison["evaluation"]["status"] == "review"
    assert any("overall average" in warning for warning in comparison["evaluation"]["warnings"])


def test_evaluate_change_warns_when_watchlist_does_not_improve():
    comparison = compare_reports(sample_report(avg=48.0, watch_implausible=5), sample_report(avg=48.0, watch_implausible=5))
    result = evaluate_change(comparison)
    assert result["status"] == "review"
    assert any("watchlist implausible" in warning for warning in result["warnings"])
