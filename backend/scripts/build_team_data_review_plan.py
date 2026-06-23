"""Read-only team data review diagnostic: combines the latest simulation
accuracy audit (Spec 010 Phase 6) and roster reconciliation candidate
report (Spec 010 Phase 8) into one per-team review-priority ranking.

Never touches seed players, ratings, formulas, or simulation behavior --
purely a deterministic re-summary of what those two reports already say,
so Codex can decide where to look next.

Usage: ./venv/Scripts/python.exe scripts/build_team_data_review_plan.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

# Rank-underperformance is the only signal that reflects an actual model
# accuracy concern, so it dominates. Ambiguous name pairs and stale seed
# players are genuinely actionable data-cleanup items, so they carry
# moderate weight. Add-candidate counts are mostly an artifact of this
# project's intentionally shallow (12-19 player) seed rosters versus a
# real 26-man squad, so per the spec they must NOT drive a team to "high"
# on their own -- hence the small weights.
RANK_UNDERPERFORMANCE_WEIGHT = 15.0
AMBIGUOUS_PAIR_WEIGHT = 5.0
STALE_SEED_WEIGHT = 3.0
HIGH_CONFIDENCE_ADD_WEIGHT = 0.5
OTHER_ADD_WEIGHT = 0.1

HIGH_BAND_THRESHOLD = 20.0
MEDIUM_BAND_THRESHOLD = 5.0


def latest_report(pattern: str) -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(pattern))
    if not matches:
        return None
    return json.loads(matches[-1].read_text(encoding="utf-8"))


def rating_lookup(audit_report: dict | None, category: str) -> dict:
    """team_id -> rating value for teams present in the audit's top/bottom-5
    list for that category; absent for every other team (the audit report
    doesn't carry full-team ratings, only the extremes)."""
    if not audit_report:
        return {}
    section = audit_report.get("ratings", {}).get(category, {})
    lookup = {}
    for row in section.get("highest", []) + section.get("lowest", []):
        lookup[row["team_id"]] = row[category]
    return lookup


def underperformance_lookup(audit_report: dict | None) -> dict:
    if not audit_report:
        return {}
    return {row["team_id"]: row["implausible_matchup_count"] for row in audit_report.get("frequentRankUnderperformers", [])}


def roster_lookup(roster_report: dict | None) -> dict:
    if not roster_report:
        return {}
    return {row["team_code"]: row for row in roster_report.get("teamReports", [])}


def compute_priority_score(
    rank_underperformance_flags: int,
    high_confidence_add_count: int,
    other_add_count: int,
    ambiguous_pair_count: int,
    likely_stale_seed_player_count: int,
) -> float:
    return round(
        rank_underperformance_flags * RANK_UNDERPERFORMANCE_WEIGHT
        + ambiguous_pair_count * AMBIGUOUS_PAIR_WEIGHT
        + likely_stale_seed_player_count * STALE_SEED_WEIGHT
        + high_confidence_add_count * HIGH_CONFIDENCE_ADD_WEIGHT
        + other_add_count * OTHER_ADD_WEIGHT,
        1,
    )


def compute_priority_band(priority_score: float) -> str:
    if priority_score >= HIGH_BAND_THRESHOLD:
        return "high"
    if priority_score >= MEDIUM_BAND_THRESHOLD:
        return "medium"
    return "low"


def build_review_reasons(
    rank_underperformance_flags: int,
    ambiguous_pair_count: int,
    likely_stale_seed_player_count: int,
    high_confidence_add_count: int,
) -> list:
    reasons = []
    if rank_underperformance_flags > 0:
        reasons.append(f"FIFAランク比でモデル評価が{rank_underperformance_flags}件の対戦で見劣り")
    if ambiguous_pair_count > 0:
        reasons.append(f"名寄せ候補が{ambiguous_pair_count}件あり")
    if likely_stale_seed_player_count > 0:
        reasons.append(f"未確認の古いシード選手が{likely_stale_seed_player_count}件")
    if high_confidence_add_count > 0:
        reasons.append(f"高信頼度の追加候補が{high_confidence_add_count}件")
    if not reasons:
        reasons.append("特筆すべき指摘なし")
    return reasons


def recommended_next_action(
    rank_underperformance_flags: int,
    ambiguous_pair_count: int,
    likely_stale_seed_player_count: int,
    high_confidence_add_count: int,
    other_add_count: int,
) -> str:
    if rank_underperformance_flags > 0:
        return "スカッド能力値レビュー"
    if ambiguous_pair_count > 0:
        return "名寄せ候補レビュー"
    if likely_stale_seed_player_count > 0 or high_confidence_add_count > 0 or other_add_count > 0:
        return "ロスター候補レビュー"
    return "低優先度"


def build_team_row(team: dict, audit_report: dict | None, roster_report: dict | None) -> dict:
    team_id = team["id"]
    roster_row = roster_lookup(roster_report).get(team_id, {})
    high_confidence_add_count = len(roster_row.get("high_confidence_add_candidates", []))
    other_add_count = len(roster_row.get("other_add_candidates", []))
    ambiguous_pair_count = len(roster_row.get("ambiguous_pairs", []))
    likely_stale_seed_player_count = len(roster_row.get("likely_stale_seed_players", []))
    rank_underperformance_flags = underperformance_lookup(audit_report).get(team_id, 0)

    priority_score = compute_priority_score(
        rank_underperformance_flags, high_confidence_add_count, other_add_count,
        ambiguous_pair_count, likely_stale_seed_player_count,
    )

    return {
        "team_id": team_id,
        "team_name": team["name"],
        "fifa_rank": team.get("fifa_rank"),
        "seed_roster_size": roster_row.get("seed_roster_size"),
        "attack_rating": rating_lookup(audit_report, "attack").get(team_id),
        "defense_rating": rating_lookup(audit_report, "defense").get(team_id),
        "strength_rating": rating_lookup(audit_report, "strength").get(team_id),
        "rank_underperformance_flags": rank_underperformance_flags,
        "high_confidence_add_candidate_count": high_confidence_add_count,
        "other_add_candidate_count": other_add_count,
        "ambiguous_pair_count": ambiguous_pair_count,
        "likely_stale_seed_player_count": likely_stale_seed_player_count,
        "priority_score": priority_score,
        "priority_band": compute_priority_band(priority_score),
        "review_reasons": build_review_reasons(
            rank_underperformance_flags, ambiguous_pair_count, likely_stale_seed_player_count, high_confidence_add_count,
        ),
        "recommended_next_action": recommended_next_action(
            rank_underperformance_flags, ambiguous_pair_count, likely_stale_seed_player_count,
            high_confidence_add_count, other_add_count,
        ),
    }


def build_report(teams: list, audit_report: dict | None, roster_report: dict | None) -> dict:
    rows = [build_team_row(t, audit_report, roster_report) for t in teams]
    rows.sort(key=lambda r: -r["priority_score"])

    source_reports = []
    if audit_report:
        source_reports.append({"name": "simulation_accuracy_audit", "generatedAt": audit_report.get("generatedAt")})
    if roster_report:
        source_reports.append({"name": "roster_reconciliation_candidates", "generatedAt": roster_report.get("generatedAt")})

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceReports": source_reports,
        "note": (
            "Read-only team data review priority ranking derived from the latest simulation accuracy audit and "
            "roster reconciliation candidate reports. Does not change simulation formulas, ratings, or seed data. "
            "This identifies where Codex should review squad/rating data next; formula changes remain frozen "
            "unless a later calibration spec authorizes them."
        ),
        "teamCount": len(rows),
        "teams": rows,
    }


def main() -> int:
    teams = json.loads((SEED_DIR / "teams.json").read_text(encoding="utf-8"))
    audit_report = latest_report("simulation_accuracy_audit_*.json")
    roster_report = latest_report("roster_reconciliation_candidates_*.json")

    if audit_report is None:
        print("Warning: no simulation_accuracy_audit report found; rank-underperformance signal will be empty.")
    if roster_report is None:
        print("Warning: no roster_reconciliation_candidates report found; roster signals will be empty.")

    report = build_report(teams, audit_report, roster_report)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"team_data_review_plan_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    bands = {"high": 0, "medium": 0, "low": 0}
    for row in report["teams"]:
        bands[row["priority_band"]] += 1
    print(f"Wrote {out_path}")
    print(f"Teams: {report['teamCount']} (high={bands['high']}, medium={bands['medium']}, low={bands['low']})")
    print("Top 5 by priority:")
    for row in report["teams"][:5]:
        print(f"  {row['team_id']:4s} score={row['priority_score']:6.1f} band={row['priority_band']:6s} {row['recommended_next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
