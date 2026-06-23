"""Compare two prediction benchmark baseline reports.

Use this after a future rating-data proposal generates a new
prediction_benchmark_baseline_*.json. The script highlights whether the
change reduced watchlist implausibility without making the overall model too
flat or too concentrated. It is read-only and does not import app code.

Usage:
  ./venv/Scripts/python.exe scripts/compare_prediction_benchmarks.py before.json after.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_MAX_OVERALL_AVG_WIN_SHIFT = 4.0
DEFAULT_MAX_BUCKET_AVG_WIN_SHIFT = 6.0
DEFAULT_MIN_WATCHLIST_IMPLAUSIBLE_REDUCTION = 1


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def delta(after_value: float | int | None, before_value: float | int | None) -> float | None:
    if after_value is None or before_value is None:
        return None
    return round(float(after_value) - float(before_value), 1)


def index_by(rows: list[dict], key: str) -> dict:
    return {row[key]: row for row in rows}


def compare_overall(before: dict, after: dict) -> dict:
    before_summary = before["overallSummary"]
    after_summary = after["overallSummary"]
    return {
        "before_matchup_count": before_summary["matchup_count"],
        "after_matchup_count": after_summary["matchup_count"],
        "average_favorite_win_pct_delta": delta(
            after_summary["average_favorite_win_pct"], before_summary["average_favorite_win_pct"],
        ),
        "implausible_favorite_count_delta": delta(
            after_summary["implausible_favorite_count"], before_summary["implausible_favorite_count"],
        ),
        "minimum_favorite_win_pct_delta": delta(
            after_summary["minimum_favorite_win_pct"], before_summary["minimum_favorite_win_pct"],
        ),
        "maximum_favorite_win_pct_delta": delta(
            after_summary["maximum_favorite_win_pct"], before_summary["maximum_favorite_win_pct"],
        ),
    }


def compare_rank_gap_buckets(before: dict, after: dict) -> list[dict]:
    before_buckets = index_by(before.get("rankGapBuckets", []), "rank_gap_bucket")
    after_buckets = index_by(after.get("rankGapBuckets", []), "rank_gap_bucket")
    bucket_ids = sorted(set(before_buckets) | set(after_buckets))
    rows = []
    for bucket_id in bucket_ids:
        before_row = before_buckets.get(bucket_id, {})
        after_row = after_buckets.get(bucket_id, {})
        rows.append({
            "rank_gap_bucket": bucket_id,
            "before_matchup_count": before_row.get("matchup_count"),
            "after_matchup_count": after_row.get("matchup_count"),
            "average_favorite_win_pct_delta": delta(
                after_row.get("average_favorite_win_pct"), before_row.get("average_favorite_win_pct"),
            ),
            "implausible_favorite_count_delta": delta(
                after_row.get("implausible_favorite_count"), before_row.get("implausible_favorite_count"),
            ),
        })
    return rows


def compare_watchlist(before: dict, after: dict) -> list[dict]:
    before_watch = index_by(before.get("watchlistTeams", []), "team_id")
    after_watch = index_by(after.get("watchlistTeams", []), "team_id")
    team_ids = sorted(set(before_watch) | set(after_watch))
    rows = []
    for team_id in team_ids:
        before_row = before_watch.get(team_id, {})
        after_row = after_watch.get(team_id, {})
        rows.append({
            "team_id": team_id,
            "average_favorite_win_pct_delta": delta(
                after_row.get("average_favorite_win_pct"), before_row.get("average_favorite_win_pct"),
            ),
            "implausible_favorite_count_delta": delta(
                after_row.get("implausible_favorite_count"), before_row.get("implausible_favorite_count"),
            ),
            "minimum_favorite_win_pct_delta": delta(
                after_row.get("minimum_favorite_win_pct"), before_row.get("minimum_favorite_win_pct"),
            ),
        })
    return rows


def evaluate_change(
    comparison: dict,
    *,
    max_overall_avg_win_shift: float = DEFAULT_MAX_OVERALL_AVG_WIN_SHIFT,
    max_bucket_avg_win_shift: float = DEFAULT_MAX_BUCKET_AVG_WIN_SHIFT,
    min_watchlist_implausible_reduction: int = DEFAULT_MIN_WATCHLIST_IMPLAUSIBLE_REDUCTION,
) -> dict:
    warnings = []
    overall_delta = comparison["overall"]["average_favorite_win_pct_delta"]
    if overall_delta is not None and abs(overall_delta) > max_overall_avg_win_shift:
        warnings.append(
            f"overall average favorite win probability moved {overall_delta:+.1f}pp, above {max_overall_avg_win_shift:.1f}pp"
        )

    for row in comparison["rankGapBuckets"]:
        bucket_delta = row["average_favorite_win_pct_delta"]
        if bucket_delta is not None and abs(bucket_delta) > max_bucket_avg_win_shift:
            warnings.append(
                f"rank-gap bucket {row['rank_gap_bucket']} moved {bucket_delta:+.1f}pp, above {max_bucket_avg_win_shift:.1f}pp"
            )

    watchlist_reduction = -sum(
        row["implausible_favorite_count_delta"] or 0
        for row in comparison["watchlistTeams"]
        if (row["implausible_favorite_count_delta"] or 0) < 0
    )
    if watchlist_reduction < min_watchlist_implausible_reduction:
        warnings.append(
            f"watchlist implausible-favorite cases improved by only {watchlist_reduction}, below required {min_watchlist_implausible_reduction}"
        )

    return {
        "status": "review" if warnings else "pass",
        "watchlist_implausible_reduction": watchlist_reduction,
        "warnings": warnings,
    }


def compare_reports(before: dict, after: dict) -> dict:
    comparison = {
        "beforeGeneratedAt": before.get("generatedAt"),
        "afterGeneratedAt": after.get("generatedAt"),
        "modelVersionBefore": before.get("modelVersion"),
        "modelVersionAfter": after.get("modelVersion"),
        "benchmarkMethod": after.get("benchmarkMethod")
        or after.get("scope", {}).get("benchmarkOrderingMethod")
        or before.get("benchmarkMethod")
        or before.get("scope", {}).get("benchmarkOrderingMethod"),
        "overall": compare_overall(before, after),
        "rankGapBuckets": compare_rank_gap_buckets(before, after),
        "watchlistTeams": compare_watchlist(before, after),
    }
    comparison["evaluation"] = evaluate_change(comparison)
    return comparison


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    comparison = compare_reports(load_report(args.before), load_report(args.after))
    text = json.dumps(comparison, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
