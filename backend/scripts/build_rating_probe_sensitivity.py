"""Run a read-only sensitivity probe for clean rating-review candidates.

This script asks a narrow question: if the current clean later-proposal
candidates received a tiny hypothetical +2 bump in overall and driver-relevant
attributes, would the prediction benchmark improve in the expected direction?

It does not propose or apply rating changes. The output is only a signal for
whether a future data-changing proposal is worth preparing.

Usage: ./venv/Scripts/python.exe scripts/build_rating_probe_sensitivity.py
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_prediction_benchmark_baseline import (  # noqa: E402
    SEED_DIR,
    build_matchup_row,
    build_player_lookup,
    compute_team_rating_row,
    latest_report,
    load_json,
    summarize_by_bucket,
    summarize_matchups,
    summarize_watchlist,
    top_ranked_teams,
    watchlist_team_ids,
)
from compare_prediction_benchmarks import compare_reports  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

PROBE_DELTA = 2
MAX_RATING_VALUE = 99

DEFENSE_FIELDS = ("defense", "tackling", "interception", "aerialDefense", "strength")
ATTACK_FIELDS = ("attack", "finishing", "shotPower", "chanceCreation", "ballCarrying", "crossing")
MIDFIELD_FIELDS = ("passing", "chanceCreation", "decisionMaking", "composure", "pressing")
GK_FIELDS = ("goalkeeperHandling", "goalkeeperReflexes", "goalkeeperDistribution")


def clamp_rating(value: int | float, delta: int = PROBE_DELTA) -> int:
    return int(min(MAX_RATING_VALUE, round(value + delta)))


def relevant_attribute_fields(position: str | None, driver: str) -> tuple[str, ...]:
    if position == "GK":
        return GK_FIELDS if driver == "defense" else ("goalkeeperDistribution", "passing")
    if driver == "attack":
        return ATTACK_FIELDS if position in {"ST", "LW", "RW", "LM", "RM", "CAM"} else MIDFIELD_FIELDS
    if driver == "defense":
        return DEFENSE_FIELDS if position in {"CB", "LB", "RB", "CDM"} else MIDFIELD_FIELDS
    if driver == "tactical":
        return MIDFIELD_FIELDS
    return ("overall",)


def clean_later_candidates(decision_report: dict | None) -> list[dict]:
    if not decision_report:
        return []
    rows = []
    for team in decision_report.get("teams", []):
        driver = team.get("dominant_negative_driver", "unknown")
        for candidate in team.get("candidate_for_later_proposal", []):
            row = dict(candidate)
            row["team_id"] = team["team_id"]
            row["team_name"] = team["team_name"]
            row["dominant_negative_driver"] = driver
            rows.append(row)
    return rows


def apply_probe_changes(rating_rows: list[dict], candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    modified = copy.deepcopy(rating_rows)
    by_player_id = {row["playerId"]: row for row in modified}
    applied = []
    for candidate in candidates:
        rating = by_player_id.get(candidate["player_id"])
        if rating is None:
            continue
        fields = ["overall", "positionOverall"]
        fields.extend(relevant_attribute_fields(candidate.get("primary_position"), candidate.get("dominant_negative_driver")))
        field_changes = []
        for field in dict.fromkeys(fields):
            if field not in rating or not isinstance(rating[field], (int, float)):
                continue
            before = rating[field]
            after = clamp_rating(before)
            rating[field] = after
            if after != before:
                field_changes.append({"field": field, "before": before, "after": after})
        applied.append({
            "player_id": candidate["player_id"],
            "team_id": candidate["team_id"],
            "name": candidate["name"],
            "primary_position": candidate.get("primary_position"),
            "dominant_negative_driver": candidate.get("dominant_negative_driver"),
            "field_changes": field_changes,
        })
    return modified, applied


def build_benchmark_from_ratings(
    *,
    teams: list[dict],
    seed_players: list[dict],
    rating_rows: list[dict],
    squad_gap_report: dict | None,
    top_team_limit: int,
    watchlist_limit: int,
) -> dict:
    players_by_team = build_player_lookup(seed_players, rating_rows)
    ranked = top_ranked_teams(teams, top_team_limit)
    watchlist_ids = watchlist_team_ids(squad_gap_report, watchlist_limit)
    matchups = []
    for i, home in enumerate(ranked):
        for away in ranked[i + 1:]:
            row = build_matchup_row(home, away, players_by_team)
            if row is not None:
                matchups.append(row)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "modelVersion": "rating-probe-sensitivity",
        "note": (
            "Read-only hypothetical +2 probe for clean rating-review candidates. "
            "This is not a rating proposal and does not change seed data."
        ),
        "sourceReports": [
            {"name": "squad_rating_gap_review", "generatedAt": (squad_gap_report or {}).get("generatedAt")}
        ],
        "scope": {
            "topTeamLimit": top_team_limit,
            "watchlistLimit": watchlist_limit,
            "rankedTeamCount": len(ranked),
            "matchupCount": len(matchups),
        },
        "teamRatings": [
            compute_team_rating_row(team, players_by_team.get(team["id"], []))
            for team in ranked
        ],
        "overallSummary": summarize_matchups(matchups),
        "rankGapBuckets": summarize_by_bucket(matchups),
        "watchlistTeams": summarize_watchlist(matchups, watchlist_ids),
        "benchmarkMatchups": matchups,
    }


def build_report(top_team_limit: int = 20, watchlist_limit: int = 8) -> dict:
    teams = load_json(SEED_DIR / "teams.json")
    seed_players = load_json(SEED_DIR / "players.json")
    rating_rows = load_json(SEED_DIR / "playerRatings2026_estimated.json")
    squad_gap_report = latest_report("squad_rating_gap_review_*.json")
    decision_report = latest_report("rating_decision_audit_*.json")
    baseline_report = latest_report("prediction_benchmark_baseline_*.json")

    candidates = clean_later_candidates(decision_report)
    probed_ratings, applied_changes = apply_probe_changes(rating_rows, candidates)
    probe_benchmark = build_benchmark_from_ratings(
        teams=teams,
        seed_players=seed_players,
        rating_rows=probed_ratings,
        squad_gap_report=squad_gap_report,
        top_team_limit=top_team_limit,
        watchlist_limit=watchlist_limit,
    )
    comparison = compare_reports(baseline_report, probe_benchmark) if baseline_report else None

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "note": (
            "能力値レビュー候補の小幅な仮説補正が予測ベンチマークへ与える影響を見る読み取り専用感度分析です。"
            "これは能力値変更案ではなく、seedデータも予測式も変更しません。"
        ),
        "sourceReports": [
            {"name": "rating_decision_audit", "generatedAt": (decision_report or {}).get("generatedAt")},
            {"name": "prediction_benchmark_baseline", "generatedAt": (baseline_report or {}).get("generatedAt")},
        ],
        "probeDelta": PROBE_DELTA,
        "candidateCount": len(candidates),
        "appliedCandidateCount": len(applied_changes),
        "appliedChanges": applied_changes,
        "probeBenchmarkSummary": {
            "overallSummary": probe_benchmark["overallSummary"],
            "watchlistTeams": probe_benchmark["watchlistTeams"],
        },
        "comparison": comparison,
        "recommendations_ja": [
            "この感度分析で改善が小さい場合、能力値変更だけでなくロスターやモデル式の監査を優先する。",
            "改善が見える場合でも、実際の数値変更は出典確認とベンチマーク比較を通過するまで適用しない。",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-team-limit", type=int, default=20)
    parser.add_argument("--watchlist-limit", type=int, default=8)
    args = parser.parse_args()

    report = build_report(args.top_team_limit, args.watchlist_limit)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"rating_probe_sensitivity_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(
        f"Candidates: {report['candidateCount']} "
        f"applied={report['appliedCandidateCount']} "
        f"probe_delta=+{report['probeDelta']}"
    )
    if report["comparison"]:
        evaluation = report["comparison"]["evaluation"]
        print(
            f"Comparison status={evaluation['status']} "
            f"watchlist_reduction={evaluation['watchlist_implausible_reduction']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
