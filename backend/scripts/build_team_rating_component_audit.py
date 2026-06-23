"""Audit team-rating components behind prediction benchmark underperformance.

The rating probe showed that small player-level bumps do not materially reduce
watchlist implausibility. This read-only audit breaks each top team's model
rating into rank score, squad strength, attack, defense, and best-XI depth so
future work can decide whether the issue lives in data, roster depth, or the
team aggregation formula.

Read-only: does not mutate seed data, ratings, formulas, or prediction
behavior.

Usage: ./venv/Scripts/python.exe scripts/build_team_rating_component_audit.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.prediction.ratings import attack_rating, defense_rating, squad_strength_rating, team_strength_rating  # noqa: E402
from build_prediction_benchmark_baseline import (  # noqa: E402
    SEED_DIR,
    build_player_lookup,
    latest_report,
    load_json,
    top_ranked_teams,
    watchlist_team_ids,
)

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def rank_score(fifa_rank: int | None) -> float | None:
    if fifa_rank is None:
        return None
    return round(max(35.0, 95.0 - 8.0 * ((fifa_rank ** 0.5) - 1)), 1)


def top_n_average(players: list[dict], n: int) -> float | None:
    if not players:
        return None
    values = [player["overall"] for player in sorted(players, key=lambda row: -row["overall"])[:n]]
    return round(mean(values), 1)


def position_counts(players: list[dict]) -> dict[str, int]:
    counts = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
    for player in players:
        position = player["primary_position"]
        if position == "GK":
            counts["GK"] += 1
        elif position in {"CB", "LB", "RB"}:
            counts["DEF"] += 1
        elif position in {"CDM", "CM", "CAM", "LM", "RM"}:
            counts["MID"] += 1
        else:
            counts["FWD"] += 1
    return counts


def component_flags(row: dict) -> list[str]:
    flags = []
    rank = row["rank_score"]
    squad = row["squad_strength"]
    if rank is not None and squad is not None and rank - squad >= 22:
        flags.append("rank_signal_far_above_squad_strength")
    if row["top_11_avg_overall"] is not None and row["top_11_avg_overall"] < 58:
        flags.append("best_xi_overall_low_for_top_ranked_team")
    if row["count_overall_gte_70"] < 2 and row["fifa_rank"] is not None and row["fifa_rank"] <= 15:
        flags.append("few_elite_seed_players_for_top_15_team")
    counts = row["position_counts"]
    if counts["DEF"] < 4:
        flags.append("thin_defensive_seed_depth")
    if counts["FWD"] < 3:
        flags.append("thin_attacking_seed_depth")
    if row["attack"] < 50:
        flags.append("attack_component_below_neutral")
    if row["defense"] < 50:
        flags.append("defense_component_below_neutral")
    return flags


def build_team_row(team: dict, players: list[dict], watchlist: bool) -> dict:
    strength, confidence = team_strength_rating(team.get("fifa_rank"), players)
    row = {
        "team_id": team["id"],
        "team_name": team["name"],
        "fifa_rank": team.get("fifa_rank"),
        "watchlist": watchlist,
        "player_count": len(players),
        "rank_score": rank_score(team.get("fifa_rank")),
        "squad_strength": round(squad_strength_rating(players), 1),
        "team_strength": round(strength, 1),
        "attack": round(attack_rating(players), 1),
        "defense": round(defense_rating(players), 1),
        "data_confidence": confidence,
        "top_3_avg_overall": top_n_average(players, 3),
        "top_5_avg_overall": top_n_average(players, 5),
        "top_11_avg_overall": top_n_average(players, 11),
        "count_overall_gte_75": sum(1 for player in players if player["overall"] >= 75),
        "count_overall_gte_70": sum(1 for player in players if player["overall"] >= 70),
        "count_overall_lt_55": sum(1 for player in players if player["overall"] < 55),
        "position_counts": position_counts(players),
        "top_players": [
            {
                "player_id": player["id"],
                "name": player["name"],
                "primary_position": player["primary_position"],
                "overall": player["overall"],
            }
            for player in sorted(players, key=lambda row: -row["overall"])[:5]
        ],
    }
    row["diagnostic_flags"] = component_flags(row)
    return row


def summarize_flags(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for flag in row["diagnostic_flags"]:
            counts[flag] = counts.get(flag, 0) + 1
    return dict(sorted(counts.items()))


def build_report(top_team_limit: int = 20, watchlist_limit: int = 8) -> dict:
    teams = load_json(SEED_DIR / "teams.json")
    seed_players = load_json(SEED_DIR / "players.json")
    rating_rows = load_json(SEED_DIR / "playerRatings2026_estimated.json")
    players_by_team = build_player_lookup(seed_players, rating_rows)
    squad_gap_report = latest_report("squad_rating_gap_review_*.json")
    watchlist_ids = set(watchlist_team_ids(squad_gap_report, watchlist_limit))
    ranked = top_ranked_teams(teams, top_team_limit)
    rows = [
        build_team_row(team, players_by_team.get(team["id"], []), team["id"] in watchlist_ids)
        for team in ranked
    ]
    watchlist_rows = [row for row in rows if row["watchlist"]]
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "note": (
            "チーム強度をFIFAランク信号、ベストXI平均、攻撃、守備、ロスター厚みに分解する読み取り専用監査です。"
            "選手能力値、seedデータ、予測式は変更しません。"
        ),
        "sourceReports": [
            {"name": "squad_rating_gap_review", "generatedAt": (squad_gap_report or {}).get("generatedAt")},
        ],
        "scope": {
            "topTeamLimit": top_team_limit,
            "watchlistLimit": watchlist_limit,
            "teamCount": len(rows),
            "watchlistTeamCount": len(watchlist_rows),
        },
        "flagCounts": summarize_flags(rows),
        "watchlistFlagCounts": summarize_flags(watchlist_rows),
        "teams": rows,
        "recommendations_ja": [
            "rank_signal_far_above_squad_strengthが多い場合、個別能力値よりロスター厚みと集約式を優先して確認する。",
            "few_elite_seed_players_for_top_15_teamは、実在の主力級選手がseedに足りない可能性を示す。",
            "attack/defense_component_below_neutralは、該当ポジション属性または集約重みの再監査候補です。",
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
    out_path = REPORTS_DIR / f"team_rating_component_audit_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"Flag counts: {report['flagCounts']}")
    print(f"Watchlist flag counts: {report['watchlistFlagCounts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
