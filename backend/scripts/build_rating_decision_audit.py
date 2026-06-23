"""Codex-side decision audit for the rating review workbench.

Spec 014 intentionally outputs review candidates, not rating changes. This
script adds a second-level review that identifies which candidates are aligned
with the matchup-driver audit and which ones are counterproductive or need
source-provenance review before any data-changing spec.

Read-only: does not mutate seed data, ratings, formulas, or prediction
behavior.

Usage: ./venv/Scripts/python.exe scripts/build_rating_decision_audit.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

DEFENSIVE_GROUPS = {"GK", "CB", "LB", "RB", "CDM"}
ATTACKING_GROUPS = {"CAM", "LM", "RM", "LW", "RW", "ST"}
MIDFIELD_GROUPS = {"CDM", "CM", "CAM", "LM", "RM"}

SOURCE_RISK_MARKERS = (
    "EA FC",
    "FC26",
    "Fotmob",
    "hat trick",
    "WC2026",
    "World Cup 2026",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report(pattern: str) -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(pattern))
    if not matches:
        return None
    return load_json(matches[-1])


def dominant_driver(summary: dict | None) -> str:
    if not summary:
        return "unknown"
    counts = summary.get("primary_negative_driver_counts") or {}
    if not counts:
        return "none"
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def position_matches_driver(position: str, driver: str) -> bool:
    if driver == "attack":
        return position in ATTACKING_GROUPS or position in MIDFIELD_GROUPS
    if driver == "defense":
        return position in DEFENSIVE_GROUPS or position in MIDFIELD_GROUPS
    if driver == "strength":
        return True
    if driver == "tactical":
        return position in MIDFIELD_GROUPS or position in ATTACKING_GROUPS
    return False


def source_risk_flags(citations: list[str]) -> list[str]:
    flags = []
    joined = " | ".join(citations)
    for marker in SOURCE_RISK_MARKERS:
        if marker.casefold() in joined.casefold():
            flags.append(marker)
    return flags


def classify_candidate(candidate: dict, driver: str) -> dict:
    action = candidate.get("suggested_codex_action")
    position = candidate.get("primary_position")
    review_flags = set(candidate.get("review_flags") or [])
    source_flags = source_risk_flags(candidate.get("source_citations") or [])

    aligned = (
        action == "inspect_for_possible_upgrade"
        and position_matches_driver(position, driver)
        and not source_flags
    )
    counterproductive = (
        action == "inspect_for_possible_downgrade"
        and "team_rank_underperformance" in review_flags
    )
    needs_source_review = bool(source_flags)

    if aligned:
        decision_bucket = "candidate_for_later_proposal"
    elif needs_source_review:
        decision_bucket = "source_review_first"
    elif counterproductive:
        decision_bucket = "do_not_use_for_upgrade_proposal"
    else:
        decision_bucket = "monitor_only"

    return {
        "player_id": candidate["player_id"],
        "name": candidate["name"],
        "primary_position": position,
        "current_overall": candidate.get("current_overall"),
        "review_score": candidate.get("review_score"),
        "review_band": candidate.get("review_band"),
        "suggested_codex_action": action,
        "review_flags": candidate.get("review_flags") or [],
        "source_risk_flags": source_flags,
        "driver_alignment": position_matches_driver(position, driver),
        "counterproductive_for_team_underperformance": counterproductive,
        "decision_bucket": decision_bucket,
    }


def build_team_decision(team: dict, driver_section: dict | None) -> dict:
    driver = dominant_driver((driver_section or {}).get("summary"))
    audited = [classify_candidate(candidate, driver) for candidate in team.get("rating_review_candidates", [])]
    bucket_counts: dict[str, int] = defaultdict(int)
    for row in audited:
        bucket_counts[row["decision_bucket"]] += 1
    return {
        "team_id": team["team_id"],
        "team_name": team["team_name"],
        "dominant_negative_driver": driver,
        "rank_underperformance_flags": team.get("rank_underperformance_flags"),
        "bucketCounts": dict(sorted(bucket_counts.items())),
        "candidate_for_later_proposal": [
            row for row in audited if row["decision_bucket"] == "candidate_for_later_proposal"
        ],
        "source_review_first": [
            row for row in audited if row["decision_bucket"] == "source_review_first"
        ],
        "do_not_use_for_upgrade_proposal": [
            row for row in audited if row["decision_bucket"] == "do_not_use_for_upgrade_proposal"
        ],
        "monitor_only": [
            row for row in audited if row["decision_bucket"] == "monitor_only"
        ],
    }


def build_report(workbench_report: dict | None, driver_report: dict | None) -> dict:
    workbench_teams = (workbench_report or {}).get("teams", [])
    driver_by_team = {
        row["team_id"]: row
        for row in (driver_report or {}).get("watchlistTeams", [])
    }
    teams = [build_team_decision(team, driver_by_team.get(team["team_id"])) for team in workbench_teams]
    total_counts: dict[str, int] = defaultdict(int)
    for team in teams:
        for bucket, count in team["bucketCounts"].items():
            total_counts[bucket] += count
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "note": (
            "能力値レビュー作業台に対するCodex側の読み取り専用判断監査です。"
            "マッチアップ要因と整合する候補、逆効果になりうる候補、出典確認を先に行う候補を分離します。"
            "数値の能力値変更は提案しません。"
        ),
        "sourceReports": [
            {"name": "rating_review_workbench", "generatedAt": (workbench_report or {}).get("generatedAt")},
            {"name": "matchup_driver_audit", "generatedAt": (driver_report or {}).get("generatedAt")},
        ],
        "teamCount": len(teams),
        "bucketCounts": dict(sorted(total_counts.items())),
        "teams": teams,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()

    report = build_report(
        latest_report("rating_review_workbench_*.json"),
        latest_report("matchup_driver_audit_*.json"),
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"rating_decision_audit_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"Bucket counts: {report['bucketCounts']}")
    for team in report["teams"]:
        print(
            f"  {team['team_id']:4s} driver={team['dominant_negative_driver']:8s} "
            f"later={len(team['candidate_for_later_proposal'])} "
            f"source={len(team['source_review_first'])} "
            f"block={len(team['do_not_use_for_upgrade_proposal'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
