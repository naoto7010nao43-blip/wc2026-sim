"""Read-only squad-rating gap diagnostic: explains, using only local data,
why Spec 011's highest-priority teams (CRO/NED/POR/etc.) are flagged --
shallow roster coverage, position-group thinness, low-confidence
attributes, stale seed players, or missing official profile fields --
before any seed data, rating, or formula change is considered.

Never touches seed players, ratings, formulas, or simulation behavior.

Usage: ./venv/Scripts/python.exe scripts/build_squad_rating_gap_review.py [--limit N]
"""

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

SEED_POSITION_TO_GROUP = {
    "GK": "GK",
    "CB": "DF", "LB": "DF", "RB": "DF",
    "CDM": "MF", "CM": "MF", "CAM": "MF", "LM": "MF", "RM": "MF",
    "LW": "FW", "RW": "FW", "ST": "FW",
}
POSITION_GROUP_ORDER = ["GK", "DF", "MF", "FW"]

# Same dataset-relative shallow-roster threshold used by Spec 010 Phase 8 --
# this seed dataset only carries 12-19 players/team, not a real 26-man squad.
LOW_ROSTER_THRESHOLD = 15
# Every player in the current playerRatings2026_estimated.json carries the
# identical set of 10 "low confidence" attributes -- see build_diagnostic_flags.
UNIFORM_LOW_CONFIDENCE_BASELINE_PER_PLAYER = 10
OFFICIAL_COVERAGE_FIELDS = {
    "club": "clubName",
    "caps": "caps",
    "goals": "nationalTeamGoals",
    "height": "heightCm",
    "dateOfBirth": "dateOfBirth",
}
DEFAULT_LIMIT = 8


def latest_report(pattern: str) -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(pattern))
    if not matches:
        return None
    return json.loads(matches[-1].read_text(encoding="utf-8"))


def median(values: list) -> float | None:
    if not values:
        return None
    return round(statistics.median(values), 1)


def position_group_for(primary_position: str) -> str:
    return SEED_POSITION_TO_GROUP.get(primary_position, "MF")


def build_position_groups(players: list) -> dict:
    """players: list of dicts with at least primary_position, overall,
    starting_probability, name."""
    groups: dict = {g: [] for g in POSITION_GROUP_ORDER}
    for p in players:
        groups[position_group_for(p["primary_position"])].append(p)

    result = {}
    for group, members in groups.items():
        if not members:
            result[group] = {"count": 0, "avg_overall": None, "avg_starting_probability": None, "top_player": None}
            continue
        overalls = [m["overall"] for m in members if m["overall"] is not None]
        starting_probs = [m["starting_probability"] for m in members if m["starting_probability"] is not None]
        top = max(members, key=lambda m: m["overall"] if m["overall"] is not None else -1)
        result[group] = {
            "count": len(members),
            "avg_overall": round(sum(overalls) / len(overalls), 1) if overalls else None,
            "avg_starting_probability": round(sum(starting_probs) / len(starting_probs), 1) if starting_probs else None,
            "top_player": {"name": top["name"], "overall": top["overall"]} if top["overall"] is not None else None,
        }
    return result


def build_rating_distribution(players: list) -> dict:
    overalls = [p["overall"] for p in players if p["overall"] is not None]
    top5 = sorted((p for p in players if p["overall"] is not None), key=lambda p: -p["overall"])[:5]
    return {
        "min_overall": min(overalls) if overalls else None,
        "median_overall": median(overalls),
        "max_overall": max(overalls) if overalls else None,
        "top_5_players": [{"name": p["name"], "overall": p["overall"]} for p in top5],
        "count_overall_gte_75": sum(1 for v in overalls if v >= 75),
        "count_overall_gte_70": sum(1 for v in overalls if v >= 70),
        "count_overall_lt_60": sum(1 for v in overalls if v < 60),
    }


def build_trust_profile(players: list, official_lookup: dict) -> dict:
    confidence_counts = Counter(p["data_confidence"] for p in players if p["data_confidence"])
    uncertainties = [p["uncertainty"] for p in players if p["uncertainty"] is not None]
    low_confidence_attribute_count = sum(len(p.get("low_confidence_attributes") or []) for p in players)

    coverage = {key: 0 for key in OFFICIAL_COVERAGE_FIELDS}
    for p in players:
        official = official_lookup.get(p["player_id"])
        if not official:
            continue
        for label, field in OFFICIAL_COVERAGE_FIELDS.items():
            if official.get(field) is not None:
                coverage[label] += 1

    return {
        "data_confidence_counts": dict(confidence_counts),
        "average_uncertainty": round(sum(uncertainties) / len(uncertainties), 2) if uncertainties else None,
        "low_confidence_attribute_count": low_confidence_attribute_count,
        "official_profile_coverage": coverage,
    }


def build_diagnostic_flags(seed_roster_size: int | None, position_groups: dict, trust_profile: dict, roster_recon: dict) -> list:
    flags = []
    if seed_roster_size is not None and seed_roster_size < LOW_ROSTER_THRESHOLD:
        flags.append("shallow_seed_roster")
    if position_groups["DF"]["count"] < 4:
        flags.append("thin_defensive_depth")
    if position_groups["FW"]["count"] < 2:
        flags.append("thin_attacking_depth")

    coverage = trust_profile["official_profile_coverage"]
    roster_size = seed_roster_size or 0
    if roster_size > 0:
        avg_coverage_fraction = sum(coverage.values()) / (len(coverage) * roster_size)
        if avg_coverage_fraction < 0.5:
            flags.append("low_official_profile_coverage")

    # Every player in the current dataset carries the identical set of 10
    # "low confidence" attributes (a pipeline-wide baseline, not per-team
    # variance), so a >=1-per-player bar would trivially fire for 100% of
    # teams and provide zero discrimination. Require strictly more than
    # that uniform baseline so this flag stays inert until real per-team
    # variance exists, rather than misclassifying every team.
    if roster_size > 0 and trust_profile["low_confidence_attribute_count"] > roster_size * UNIFORM_LOW_CONFIDENCE_BASELINE_PER_PLAYER:
        flags.append("many_low_confidence_attributes")

    if roster_recon.get("likely_stale_seed_player_count", 0) > 0:
        flags.append("stale_seed_review_needed")
    if roster_recon.get("ambiguous_pair_count", 0) > 0:
        flags.append("name_pair_review_needed")

    return flags


def build_review_summary(rank_underperformance_flags: int, diagnostic_flags: list, roster_recon: dict, seed_roster_size: int | None) -> list:
    summary = []
    if rank_underperformance_flags > 0:
        summary.append(
            f"FIFAランク比でモデル評価が{rank_underperformance_flags}件の対戦で見劣りしており、能力値データの精査が必要です。"
        )
    if "low_official_profile_coverage" in diagnostic_flags:
        summary.append("公式プロフィール情報(クラブ・キャップ数・得点・身長・生年月日)の反映率が低めです。")
    if "many_low_confidence_attributes" in diagnostic_flags:
        summary.append("低信頼度の能力値項目が多く、データ精度に注意が必要です。")
    if "shallow_seed_roster" in diagnostic_flags:
        summary.append(f"シードロスターが{seed_roster_size}人と少なく、選手データの網羅性が低い可能性があります。")
    if "thin_defensive_depth" in diagnostic_flags:
        summary.append("守備ポジションの登録選手が少なく、守備評価が不安定になりやすい可能性があります。")
    if "thin_attacking_depth" in diagnostic_flags:
        summary.append("攻撃ポジションの登録選手が少なく、攻撃評価が不安定になりやすい可能性があります。")
    if roster_recon.get("likely_stale_seed_player_count", 0) > 0:
        summary.append(f"{roster_recon['likely_stale_seed_player_count']}人の古いシード選手の確認が必要です。")
    if roster_recon.get("ambiguous_pair_count", 0) > 0:
        summary.append(f"{roster_recon['ambiguous_pair_count']}件の名寄せ候補があります。")
    if not summary:
        summary.append("特筆すべき指摘はありません。継続的なモニタリングのみで十分です。")
    return summary[:4]


def recommended_next_action(rank_underperformance_flags: int, diagnostic_flags: list, roster_recon: dict) -> str:
    if rank_underperformance_flags > 0 or "low_official_profile_coverage" in diagnostic_flags or "many_low_confidence_attributes" in diagnostic_flags:
        return "rating_data_review"
    if roster_recon.get("ambiguous_pair_count", 0) > 0:
        return "name_matching_review"
    if (
        roster_recon.get("likely_stale_seed_player_count", 0) > 0
        or roster_recon.get("high_confidence_add_candidate_count", 0) > 0
        or roster_recon.get("other_add_candidate_count", 0) > 0
    ):
        return "roster_reconciliation_review"
    return "monitor_only"


def build_team_row(review_row: dict, players: list, official_lookup: dict, roster_row: dict | None) -> dict:
    roster_recon = {
        "high_confidence_add_candidate_count": len((roster_row or {}).get("high_confidence_add_candidates", [])),
        "other_add_candidate_count": len((roster_row or {}).get("other_add_candidates", [])),
        "ambiguous_pair_count": len((roster_row or {}).get("ambiguous_pairs", [])),
        "likely_stale_seed_player_count": len((roster_row or {}).get("likely_stale_seed_players", [])),
        "top_ambiguous_pairs": sorted(
            (roster_row or {}).get("ambiguous_pairs", []), key=lambda p: -p.get("shared_token_count", 0)
        )[:3],
    }

    position_groups = build_position_groups(players)
    rating_distribution = build_rating_distribution(players)
    trust_profile = build_trust_profile(players, official_lookup)
    seed_roster_size = review_row.get("seed_roster_size") or len(players)
    diagnostic_flags = build_diagnostic_flags(seed_roster_size, position_groups, trust_profile, roster_recon)
    rank_underperformance_flags = review_row.get("rank_underperformance_flags", 0)

    return {
        "team_id": review_row["team_id"],
        "team_name": review_row["team_name"],
        "fifa_rank": review_row.get("fifa_rank"),
        "priority_score": review_row.get("priority_score"),
        "rank_underperformance_flags": rank_underperformance_flags,
        "seed_roster_size": seed_roster_size,
        "position_groups": position_groups,
        "rating_distribution": rating_distribution,
        "trust_profile": trust_profile,
        "roster_reconciliation": roster_recon,
        "diagnostic_flags": diagnostic_flags,
        "review_summary_ja": build_review_summary(rank_underperformance_flags, diagnostic_flags, roster_recon, seed_roster_size),
        "recommended_next_action": recommended_next_action(rank_underperformance_flags, diagnostic_flags, roster_recon),
    }


def build_report(
    review_plan: dict | None,
    roster_report: dict | None,
    players_by_team: dict,
    official_lookup: dict,
    limit: int = DEFAULT_LIMIT,
) -> dict:
    review_rows = (review_plan or {}).get("teams", [])[:limit]
    roster_by_team = {row["team_code"]: row for row in (roster_report or {}).get("teamReports", [])}

    teams = [
        build_team_row(row, players_by_team.get(row["team_id"], []), official_lookup, roster_by_team.get(row["team_id"]))
        for row in review_rows
    ]

    source_reports = []
    if review_plan:
        source_reports.append({"name": "team_data_review_plan", "generatedAt": review_plan.get("generatedAt")})
    if roster_report:
        source_reports.append({"name": "roster_reconciliation_candidates", "generatedAt": roster_report.get("generatedAt")})

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceReports": source_reports,
        "note": (
            "優先度の高いチームについて、能力値データのどこに問題がありそうかを示す読み取り専用の診断です。"
            "ロスターが浅いことによる候補数の多さと、実際のモデル/順位差の問題を区別しています。"
            "シード選手・能力値・フォーミュラ・試合予測は変更しません。"
            "フォーミュラの調整は別途の検証スペックがない限り凍結されたままです。"
        ),
        "teams": teams,
    }


def _load_players_by_team() -> dict:
    players = json.loads((SEED_DIR / "players.json").read_text(encoding="utf-8"))
    ratings = {r["playerId"]: r for r in json.loads((SEED_DIR / "playerRatings2026_estimated.json").read_text(encoding="utf-8"))}

    by_team: dict = {}
    for p in players:
        rating = ratings.get(p["id"], {})
        by_team.setdefault(p["team_id"], []).append({
            "player_id": p["id"],
            "name": p["name"],
            "primary_position": p["primary_position"],
            "overall": rating.get("overall"),
            "starting_probability": rating.get("startingProbability"),
            "data_confidence": rating.get("dataConfidence"),
            "uncertainty": rating.get("uncertainty"),
            "low_confidence_attributes": rating.get("lowConfidenceAttributes"),
        })
    return by_team


def _load_official_lookup() -> dict:
    official = json.loads((SEED_DIR / "players2026_official.json").read_text(encoding="utf-8"))
    return {o["playerId"]: o for o in official}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args()

    review_plan = latest_report("team_data_review_plan_*.json")
    roster_report = latest_report("roster_reconciliation_candidates_*.json")
    if review_plan is None:
        print("Warning: no team_data_review_plan report found; run build_team_data_review_plan.py first.")
        return 1

    players_by_team = _load_players_by_team()
    official_lookup = _load_official_lookup()

    report = build_report(review_plan, roster_report, players_by_team, official_lookup, limit=args.limit)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"squad_rating_gap_review_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    for row in report["teams"]:
        print(f"  {row['team_id']:4s} action={row['recommended_next_action']:26s} flags={row['diagnostic_flags']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
