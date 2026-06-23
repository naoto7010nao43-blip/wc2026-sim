"""Build an order-neutral v1 vs. rank75 prediction benchmark comparison.

The original rank75 calibration evidence used a synthetic fixture order where
the FIFA-better-ranked team was always passed as the home team. Production
fixtures still use their real order, but synthetic benchmark evidence should
not correlate FIFA rank with the generic home-advantage term.

This script compares the old v1 blend (rank60/squad40) with the current rank75
blend by averaging each matchup in both home/away orders. It is read-only and
does not mutate seed data, ratings, formulas, or prediction behavior.

Usage: ./venv/Scripts/python.exe scripts/build_rank75_order_neutral_comparison.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_aggregation_calibration_sandbox import build_variant_benchmark  # noqa: E402
from build_prediction_benchmark_baseline import BENCHMARK_ORDERING_METHOD  # noqa: E402
from compare_prediction_benchmarks import compare_reports  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

V1_VARIANT = {
    "id": "poisson-v1-rank60",
    "label": "Poisson v1 rank60/squad40 order-neutral benchmark",
    "rank_weight": 0.60,
    "squad_method": "current",
}

RANK75_VARIANT = {
    "id": "poisson-v2-rank75",
    "label": "Poisson v2 rank75/squad25 order-neutral benchmark",
    "rank_weight": 0.75,
    "squad_method": "current",
}


def build_order_neutral_benchmark(
    variant: dict,
    *,
    model_version: str,
    top_team_limit: int,
    watchlist_limit: int,
) -> dict:
    report = build_variant_benchmark(variant, top_team_limit, watchlist_limit)
    report["modelVersion"] = model_version
    report["benchmarkMethod"] = BENCHMARK_ORDERING_METHOD
    report["note"] = (
        "Read-only order-neutral prediction benchmark. Each synthetic matchup "
        "averages favorite-home and favorite-away orderings so FIFA rank is not "
        "correlated with the generic home-advantage term."
    )
    report["sourceReports"].append({"name": "benchmark_method", "generatedAt": report["generatedAt"]})
    return report


def build_report(top_team_limit: int = 20, watchlist_limit: int = 8) -> tuple[dict, dict, dict]:
    before = build_order_neutral_benchmark(
        V1_VARIANT,
        model_version="poisson-v1-rank60-order-neutral",
        top_team_limit=top_team_limit,
        watchlist_limit=watchlist_limit,
    )
    after = build_order_neutral_benchmark(
        RANK75_VARIANT,
        model_version="poisson-v2-rank75-order-neutral",
        top_team_limit=top_team_limit,
        watchlist_limit=watchlist_limit,
    )
    comparison = compare_reports(before, after)
    comparison["generatedAt"] = datetime.now(timezone.utc).isoformat()
    comparison["benchmarkMethod"] = BENCHMARK_ORDERING_METHOD
    comparison["note"] = (
        "Order-neutral comparison for the rank75 calibration. This supersedes "
        "favorite-as-home benchmark framing for methodology decisions, while "
        "leaving production prediction behavior unchanged."
    )
    return before, after, comparison


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-team-limit", type=int, default=20)
    parser.add_argument("--watchlist-limit", type=int, default=8)
    args = parser.parse_args()

    before, after, comparison = build_report(args.top_team_limit, args.watchlist_limit)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    before_path = REPORTS_DIR / f"prediction_benchmark_v1_order_neutral_{date_str}.json"
    after_path = REPORTS_DIR / f"prediction_benchmark_rank75_order_neutral_{date_str}.json"
    comparison_path = REPORTS_DIR / f"prediction_benchmark_comparison_rank75_order_neutral_{date_str}.json"

    before_path.write_text(json.dumps(before, indent=2, ensure_ascii=False), encoding="utf-8")
    after_path.write_text(json.dumps(after, indent=2, ensure_ascii=False), encoding="utf-8")
    comparison_path.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")

    evaluation = comparison["evaluation"]
    overall = comparison["overall"]
    print(f"Wrote {before_path}")
    print(f"Wrote {after_path}")
    print(f"Wrote {comparison_path}")
    print(
        "Order-neutral comparison: "
        f"status={evaluation['status']} "
        f"watchlist_reduction={evaluation['watchlist_implausible_reduction']} "
        f"overall_implausible_delta={overall['implausible_favorite_count_delta']} "
        f"avg_favorite_win_delta={overall['average_favorite_win_pct_delta']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
