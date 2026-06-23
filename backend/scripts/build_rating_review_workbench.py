"""Read-only player-level rating review workbench: for the top teams flagged
by Spec 012's squad-rating-gap review, explain which individual players most
deserve a Codex-led rating review and why -- market value vs. current
overall, caps/goals vs. current overall, starting probability vs. current
overall, low-confidence attribute count, official-profile coverage vs.
data confidence, and shallow-roster top-contributor status. All signals are
computed from local repository data only.

Outputs review priority and a suggested Codex action label. Never outputs a
numeric rating change and never touches players.json, players2026_official.json,
or playerRatings2026_estimated.json.

Usage: ./venv/Scripts/python.exe scripts/build_rating_review_workbench.py [--limit N]
"""

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

DEFAULT_LIMIT = 8
MAX_CANDIDATES_PER_TEAM = 10

# Every player in the current playerRatings2026_estimated.json carries the
# identical set of 10 "low confidence" attributes -- a uniform pipeline-wide
# baseline, not per-team/per-player variance (same artifact documented in
# build_squad_rating_gap_review.py). Require strictly more than that baseline
# so this signal stays inert until real per-player variance exists, instead
# of firing for every single player.
UNIFORM_LOW_CONFIDENCE_BASELINE = 10

# Percentile-gap thresholds for the value/caps-vs-rating mismatch signals.
# Conservative on purpose: only flag a clear gap, not routine noise.
OUTPACE_PERCENTILE_GAP = 20.0
HIGH_STARTING_PROBABILITY = 65
LOW_OVERALL_VS_MEDIAN_MARGIN = 3

# Score weights. team_rank_underperformance alone (8) cannot reach even the
# medium band (15), let alone high (30) -- a player-level signal must also
# be present, per the spec's "must not become high merely because the team
# has rank underperformance" rule.
WEIGHT_TEAM_RANK_UNDERPERFORMANCE = 8.0
WEIGHT_WEAK_POSITION_GROUP = 12.0
WEIGHT_VALUE_OUTPACES_RATING = 15.0
WEIGHT_RATING_OUTPACES_VALUE = 15.0
WEIGHT_CAPS_OUTPACE_RATING = 12.0
WEIGHT_RATING_OUTPACES_CAPS = 12.0
WEIGHT_HIGH_STARTING_LOW_RATING = 15.0
WEIGHT_MANY_LOW_CONFIDENCE_ATTRIBUTES = 10.0
WEIGHT_SHALLOW_ROSTER_TOP_CONTRIBUTOR = 10.0
# No "official profile coverage but still estimated" signal: verified
# directly that 89% of the entire 669-player pool already matches that
# description (Spec 008/009 already applied the safe official-field merge
# broadly), so it is a dataset-wide baseline, not a per-player differentiator.

HIGH_BAND_THRESHOLD = 30.0
MEDIUM_BAND_THRESHOLD = 15.0

POSITION_GROUP_ORDER = ["GK", "DF", "MF", "FW"]
SEED_POSITION_TO_GROUP = {
    "GK": "GK",
    "CB": "DF", "LB": "DF", "RB": "DF",
    "CDM": "MF", "CM": "MF", "CAM": "MF", "LM": "MF", "RM": "MF",
    "LW": "FW", "RW": "FW", "ST": "FW",
}


def latest_report(pattern: str) -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(pattern))
    if not matches:
        return None
    return json.loads(matches[-1].read_text(encoding="utf-8"))


def position_group_for(primary_position: str) -> str:
    return SEED_POSITION_TO_GROUP.get(primary_position, "MF")


def percentile_ranks(values: dict) -> dict:
    """values: {id: float|None}. Returns {id: percentile 0-100|None}, ranked
    only among entries with a non-None value; None values map to None."""
    present = [(pid, v) for pid, v in values.items() if v is not None]
    if len(present) < 2:
        return {pid: None for pid in values}
    present.sort(key=lambda item: item[1])
    result = {pid: None for pid in values}
    n = len(present)
    for rank, (pid, _value) in enumerate(present):
        result[pid] = round(rank / (n - 1) * 100, 1)
    return result


def percentile_ranks_by_position_group(players: list, field: str) -> dict:
    """Goalkeepers' `overall` is computed from a broad attribute set that
    structurally sits far below outfield positions (median ~49 vs ~52-57 for
    DF/MF/FW in this dataset -- verified directly against the data), while
    market value/caps are comparatively closer across positions. Ranking
    market-value/caps percentile against overall percentile across the full
    mixed-position pool would therefore flag nearly every goalkeeper as
    "underrated" purely from this baseline gap, not from any real per-player
    signal. Percentiles must be computed within each position group so a
    player is only ever compared against positional peers."""
    grouped: dict = {}
    for player in players:
        grouped.setdefault(position_group_for(player["primary_position"]), {})[player["player_id"]] = player.get(field)

    result: dict = {}
    for group_values in grouped.values():
        result.update(percentile_ranks(group_values))
    return result


def load_players_by_team() -> dict:
    players = json.loads((SEED_DIR / "players.json").read_text(encoding="utf-8"))
    official = {o["playerId"]: o for o in json.loads((SEED_DIR / "players2026_official.json").read_text(encoding="utf-8"))}
    ratings = {r["playerId"]: r for r in json.loads((SEED_DIR / "playerRatings2026_estimated.json").read_text(encoding="utf-8"))}

    by_team: dict = {}
    for p in players:
        rating = ratings.get(p["id"], {})
        official_row = official.get(p["id"], {})
        by_team.setdefault(p["team_id"], []).append({
            "player_id": p["id"],
            "name": p["name"],
            "name_ja": p.get("name_ja"),
            "primary_position": p["primary_position"],
            "age": p.get("age"),
            "club_name": official_row.get("clubName"),
            "caps": official_row.get("caps"),
            "national_team_goals": official_row.get("nationalTeamGoals"),
            "market_value_eur": p.get("market_value_eur"),
            "source_citations": p.get("source_citations") or [],
            "qualitative_adjustments": p.get("qualitative_adjustments") or {},
            "current_overall": rating.get("overall"),
            "position_overall": rating.get("positionOverall"),
            "starting_probability": rating.get("startingProbability"),
            "uncertainty": rating.get("uncertainty"),
            "data_confidence": rating.get("dataConfidence"),
            "source_breakdown": rating.get("sourceBreakdown") or {},
            "low_confidence_attributes": rating.get("lowConfidenceAttributes") or [],
        })
    return by_team


def weak_position_groups(diagnostic_flags: list) -> set:
    # Deliberately NOT "lowest avg_overall among the four groups": GK overall
    # is computed from a broad attribute set that sits structurally below
    # outfield positions for every team in this dataset (verified directly --
    # GK would "win" this comparison for 7 of 8 top-priority teams even
    # though none of them have an actual goalkeeping depth problem). Only
    # reuse Spec 012's already-vetted, count-based thresholds, which compare
    # roster depth rather than a rating scale that differs by position.
    weak = set()
    if "thin_defensive_depth" in diagnostic_flags:
        weak.add("DF")
    if "thin_attacking_depth" in diagnostic_flags:
        weak.add("FW")
    return weak


def compute_player_signals(
    player: dict,
    *,
    team_rank_underperformance: bool,
    is_weak_position_group: bool,
    value_percentile: float | None,
    caps_percentile: float | None,
    overall_percentile: float | None,
    team_median_overall: float | None,
    shallow_roster: bool,
    is_top_contributor: bool,
) -> dict:
    current_overall = player["current_overall"]

    value_outpaces_rating = (
        value_percentile is not None and overall_percentile is not None
        and value_percentile - overall_percentile > OUTPACE_PERCENTILE_GAP
    )
    rating_outpaces_value = (
        value_percentile is not None and overall_percentile is not None
        and overall_percentile - value_percentile > OUTPACE_PERCENTILE_GAP
    )
    caps_outpace_rating = (
        caps_percentile is not None and overall_percentile is not None
        and caps_percentile - overall_percentile > OUTPACE_PERCENTILE_GAP
    )
    rating_outpaces_caps = (
        caps_percentile is not None and overall_percentile is not None
        and overall_percentile - caps_percentile > OUTPACE_PERCENTILE_GAP
    )
    high_starting_low_rating = (
        player["starting_probability"] is not None and player["starting_probability"] >= HIGH_STARTING_PROBABILITY
        and current_overall is not None and team_median_overall is not None
        and current_overall < team_median_overall - LOW_OVERALL_VS_MEDIAN_MARGIN
    )
    many_low_confidence_attributes = len(player["low_confidence_attributes"]) > UNIFORM_LOW_CONFIDENCE_BASELINE
    shallow_roster_top_contributor = shallow_roster and is_top_contributor

    return {
        "team_rank_underperformance": team_rank_underperformance,
        "weak_position_group": is_weak_position_group,
        "value_outpaces_rating": value_outpaces_rating,
        "rating_outpaces_value": rating_outpaces_value,
        "caps_outpace_rating": caps_outpace_rating,
        "rating_outpaces_caps": rating_outpaces_caps,
        "high_starting_probability_low_rating": high_starting_low_rating,
        "many_low_confidence_attributes": many_low_confidence_attributes,
        "shallow_roster_top_contributor": shallow_roster_top_contributor,
    }


SIGNAL_WEIGHTS = {
    "team_rank_underperformance": WEIGHT_TEAM_RANK_UNDERPERFORMANCE,
    "weak_position_group": WEIGHT_WEAK_POSITION_GROUP,
    "value_outpaces_rating": WEIGHT_VALUE_OUTPACES_RATING,
    "rating_outpaces_value": WEIGHT_RATING_OUTPACES_VALUE,
    "caps_outpace_rating": WEIGHT_CAPS_OUTPACE_RATING,
    "rating_outpaces_caps": WEIGHT_RATING_OUTPACES_CAPS,
    "high_starting_probability_low_rating": WEIGHT_HIGH_STARTING_LOW_RATING,
    "many_low_confidence_attributes": WEIGHT_MANY_LOW_CONFIDENCE_ATTRIBUTES,
    "shallow_roster_top_contributor": WEIGHT_SHALLOW_ROSTER_TOP_CONTRIBUTOR,
}


def compute_review_score(signals: dict) -> float:
    return round(sum(SIGNAL_WEIGHTS[key] for key, active in signals.items() if active), 1)


def review_band(score: float) -> str:
    if score >= HIGH_BAND_THRESHOLD:
        return "high"
    if score >= MEDIUM_BAND_THRESHOLD:
        return "medium"
    return "low"


def build_review_flags(signals: dict) -> list:
    return [key for key, active in signals.items() if active]


REASON_LABELS_JA = {
    "team_rank_underperformance": "所属チームがFIFAランク比でモデル評価が見劣りしています。",
    "weak_position_group": "手薄なポジショングループに所属しています。",
    "value_outpaces_rating": "市場価値が現在の能力値評価に対して高めです。",
    "rating_outpaces_value": "現在の能力値評価が市場価値に対して高めです。",
    "caps_outpace_rating": "代表キャップ数が現在の能力値評価に対して多めです。",
    "rating_outpaces_caps": "現在の能力値評価が代表キャップ数に対して高めです。",
    "high_starting_probability_low_rating": "先発確率は高いものの、チーム内の能力値中央値より低めです。",
    "many_low_confidence_attributes": "低信頼度の能力値項目が多めです。",
    "shallow_roster_top_contributor": "シードロスターが浅いチームの主力級選手です。",
}


def build_review_summary_ja(flags: list) -> list:
    summary = [REASON_LABELS_JA[flag] for flag in flags if flag in REASON_LABELS_JA]
    if not summary:
        summary.append("現時点で能力値レビューを要する明確な指摘はありません。")
    return summary[:3]


def suggested_codex_action(signals: dict) -> str:
    downgrade_signals = signals["rating_outpaces_value"] or signals["rating_outpaces_caps"]
    upgrade_signals = (
        signals["value_outpaces_rating"]
        or signals["caps_outpace_rating"]
        or signals["high_starting_probability_low_rating"]
    )
    if downgrade_signals and not upgrade_signals:
        return "inspect_for_possible_downgrade"
    if upgrade_signals:
        return "inspect_for_possible_upgrade"
    if signals["shallow_roster_top_contributor"] or signals["many_low_confidence_attributes"]:
        return "verify_roster_role_first"
    return "monitor_only"


def build_candidate_row(player: dict, signals: dict) -> dict:
    score = compute_review_score(signals)
    flags = build_review_flags(signals)
    return {
        "player_id": player["player_id"],
        "name": player["name"],
        "name_ja": player["name_ja"],
        "primary_position": player["primary_position"],
        "age": player["age"],
        "club_name": player["club_name"],
        "caps": player["caps"],
        "national_team_goals": player["national_team_goals"],
        "market_value_eur": player["market_value_eur"],
        "source_citations": player["source_citations"],
        "current_overall": player["current_overall"],
        "position_overall": player["position_overall"],
        "starting_probability": player["starting_probability"],
        "uncertainty": player["uncertainty"],
        "data_confidence": player["data_confidence"],
        "source_breakdown": player["source_breakdown"],
        "low_confidence_attributes": player["low_confidence_attributes"],
        "qualitative_adjustments": player["qualitative_adjustments"],
        "review_score": score,
        "review_band": review_band(score),
        "review_flags": flags,
        "review_summary_ja": build_review_summary_ja(flags),
        "suggested_codex_action": suggested_codex_action(signals),
    }


def build_position_group_summary(position_groups: dict, weak_groups: set, candidates: list) -> dict:
    candidate_count_by_group: dict = {g: 0 for g in POSITION_GROUP_ORDER}
    for candidate in candidates:
        group = position_group_for(candidate["primary_position"])
        candidate_count_by_group[group] += 1

    summary = {}
    for group in POSITION_GROUP_ORDER:
        info = position_groups.get(group, {})
        summary[group] = {
            "count": info.get("count", 0),
            "avg_overall": info.get("avg_overall"),
            "top_player": info.get("top_player"),
            "is_weak_group": group in weak_groups,
            "review_candidate_count": candidate_count_by_group[group],
        }
    return summary


def build_team_row(
    squad_gap_row: dict,
    players: list,
    value_percentiles: dict,
    caps_percentiles: dict,
    overall_percentiles: dict,
) -> dict:
    position_groups = squad_gap_row.get("position_groups", {})
    diagnostic_flags = squad_gap_row.get("diagnostic_flags", [])
    weak_groups = weak_position_groups(diagnostic_flags)
    team_rank_underperformance = squad_gap_row.get("rank_underperformance_flags", 0) > 0
    shallow_roster = "shallow_seed_roster" in diagnostic_flags

    overalls = [p["current_overall"] for p in players if p["current_overall"] is not None]
    top_overall = max(overalls) if overalls else None

    # Position-group-local median, not team-wide median: a team's overall
    # median is pulled down by its goalkeepers' structurally lower baseline
    # (see percentile_ranks_by_position_group), so comparing every player
    # against the team-wide figure would flag starting goalkeepers as
    # "underrated" by construction. Require at least 2 same-group players on
    # the team before trusting a local median; otherwise skip the signal.
    group_overalls: dict = {}
    for player in players:
        group = position_group_for(player["primary_position"])
        if player["current_overall"] is not None:
            group_overalls.setdefault(group, []).append(player["current_overall"])
    group_median_overall = {
        group: round(statistics.median(values), 1)
        for group, values in group_overalls.items()
        if len(values) >= 2
    }

    candidates = []
    for player in players:
        group = position_group_for(player["primary_position"])
        is_weak_group = group in weak_groups
        is_top_contributor = (
            top_overall is not None and player["current_overall"] is not None
            and player["current_overall"] >= top_overall - 2
        )
        signals = compute_player_signals(
            player,
            team_rank_underperformance=team_rank_underperformance,
            is_weak_position_group=is_weak_group,
            value_percentile=value_percentiles.get(player["player_id"]),
            caps_percentile=caps_percentiles.get(player["player_id"]),
            overall_percentile=overall_percentiles.get(player["player_id"]),
            team_median_overall=group_median_overall.get(group),
            shallow_roster=shallow_roster,
            is_top_contributor=is_top_contributor,
        )
        if any(signals.values()):
            candidates.append(build_candidate_row(player, signals))

    candidates.sort(key=lambda row: (-row["review_score"], row["player_id"]))
    candidates = candidates[:MAX_CANDIDATES_PER_TEAM]

    return {
        "team_id": squad_gap_row["team_id"],
        "team_name": squad_gap_row["team_name"],
        "fifa_rank": squad_gap_row.get("fifa_rank"),
        "squad_gap_priority_score": squad_gap_row.get("priority_score"),
        "rank_underperformance_flags": squad_gap_row.get("rank_underperformance_flags", 0),
        "recommended_next_action": squad_gap_row.get("recommended_next_action"),
        "position_group_summary": build_position_group_summary(position_groups, weak_groups, candidates),
        "rating_review_candidates": candidates,
    }


def build_report(
    squad_gap_report: dict | None,
    team_review_report: dict | None,
    roster_report: dict | None,
    players_by_team: dict,
    limit: int = DEFAULT_LIMIT,
) -> dict:
    squad_gap_rows = (squad_gap_report or {}).get("teams", [])[:limit]

    all_players = [p for players in players_by_team.values() for p in players]
    value_percentiles = percentile_ranks_by_position_group(all_players, "market_value_eur")
    caps_percentiles = percentile_ranks_by_position_group(all_players, "caps")
    overall_percentiles = percentile_ranks_by_position_group(all_players, "current_overall")

    teams = [
        build_team_row(
            row,
            players_by_team.get(row["team_id"], []),
            value_percentiles,
            caps_percentiles,
            overall_percentiles,
        )
        for row in squad_gap_rows
    ]

    source_reports = []
    if squad_gap_report:
        source_reports.append({"name": "squad_rating_gap_review", "generatedAt": squad_gap_report.get("generatedAt")})
    if team_review_report:
        source_reports.append({"name": "team_data_review_plan", "generatedAt": team_review_report.get("generatedAt")})
    if roster_report:
        source_reports.append({"name": "roster_reconciliation_candidates", "generatedAt": roster_report.get("generatedAt")})

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceReports": source_reports,
        "note": (
            "優先度の高いチームについて、どの選手の能力値レビューが必要そうかを示す読み取り専用の作業台です。"
            "市場価値・代表キャップ数・先発確率・データの信頼度などのローカルデータのみから算出した、"
            "レビュー優先度の提案です。能力値そのものを変更するものではなく、"
            "Codexが次に確認すべき選手を絞り込むための一次資料です。"
        ),
        "teamCount": len(teams),
        "teams": teams,
    }


def _load_team_players(players_by_team: dict, team_id: str) -> list:
    return players_by_team.get(team_id, [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args()

    squad_gap_report = latest_report("squad_rating_gap_review_*.json")
    if squad_gap_report is None:
        print("Warning: no squad_rating_gap_review report found; run build_squad_rating_gap_review.py first.")
        return 1
    team_review_report = latest_report("team_data_review_plan_*.json")
    roster_report = latest_report("roster_reconciliation_candidates_*.json")

    players_by_team = load_players_by_team()

    report = build_report(squad_gap_report, team_review_report, roster_report, players_by_team, limit=args.limit)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"rating_review_workbench_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    for row in report["teams"]:
        print(f"  {row['team_id']:4s} candidates={len(row['rating_review_candidates'])}")
        for candidate in row["rating_review_candidates"][:3]:
            print(f"      {candidate['player_id']:20s} score={candidate['review_score']:5.1f} band={candidate['review_band']:6s} action={candidate['suggested_codex_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
