"""Read-only matchup-driver audit for top squad/rating review teams.

Prediction benchmark reports show *where* the current model undershoots a
better-ranked team. This report explains *which model features* are pulling
those watchlist matchups down: attack, defense, blended strength, tactical
matchup, or the fixed home-order edge.

It does not mutate seed data, ratings, model constants, formulas, or
prediction behavior.

Usage: ./venv/Scripts/python.exe scripts/build_matchup_driver_audit.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.prediction.model_config import DEFAULT_MODEL_CONFIG
from app.prediction.poisson_model import build_match_features, predict_match

from scripts.build_prediction_benchmark_baseline import (
    build_player_lookup,
    is_implausible_favorite,
    latest_report,
    load_json,
    minimum_expected_favorite_win_pct,
    top_ranked_teams,
    watchlist_team_ids,
)

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

DRIVER_ORDER = ("attack", "defense", "strength", "tactical", "home_order")


def contribution_breakdown(features, config=DEFAULT_MODEL_CONFIG) -> dict:
    return {
        "attack": round(config.attack_diff_weight * features.attack_diff, 4),
        "defense": round(config.defense_diff_weight * features.defense_diff, 4),
        "strength": round(config.strength_diff_weight * features.strength_diff, 4),
        "tactical": round(config.tactical_matchup_weight * features.tactical_modifier, 4),
        "home_order": round(config.home_advantage, 4),
    }


def primary_negative_driver(contributions: dict) -> str:
    negatives = {key: value for key, value in contributions.items() if value < 0}
    if not negatives:
        return "none"
    return min(negatives.items(), key=lambda item: item[1])[0]


def driver_summary(rows: list[dict]) -> dict:
    if not rows:
        return {
            "matchup_count": 0,
            "average_contributions": {key: None for key in DRIVER_ORDER},
            "primary_negative_driver_counts": {},
        }
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["primary_negative_driver"]] += 1
    return {
        "matchup_count": len(rows),
        "average_contributions": {
            key: round(mean(row["log_goal_contributions"][key] for row in rows), 4)
            for key in DRIVER_ORDER
        },
        "primary_negative_driver_counts": dict(sorted(counts.items())),
    }


def build_matchup_driver_row(home: dict, away: dict, players_by_team: dict[str, list[dict]]) -> dict | None:
    home_players = players_by_team.get(home["id"], [])
    away_players = players_by_team.get(away["id"], [])
    if len(home_players) < 11 or len(away_players) < 11:
        return None

    features = build_match_features(
        home_players,
        away_players,
        home.get("fifa_rank"),
        away.get("fifa_rank"),
        home.get("tactical_profile"),
        away.get("tactical_profile"),
    )
    prediction = predict_match(
        home["id"],
        away["id"],
        home_players,
        away_players,
        home.get("fifa_rank"),
        away.get("fifa_rank"),
        home.get("tactical_profile"),
        away.get("tactical_profile"),
    )
    rank_gap = (away.get("fifa_rank") or 0) - (home.get("fifa_rank") or 0)
    expected_floor = minimum_expected_favorite_win_pct(rank_gap)
    contributions = contribution_breakdown(features)
    return {
        "favorite_team_id": home["id"],
        "opponent_team_id": away["id"],
        "favorite_fifa_rank": home.get("fifa_rank"),
        "opponent_fifa_rank": away.get("fifa_rank"),
        "rank_gap": rank_gap,
        "favorite_win_pct": prediction.home_win_pct,
        "minimum_expected_favorite_win_pct": expected_floor,
        "implausible_favorite": is_implausible_favorite(prediction.home_win_pct, rank_gap),
        "expected_goals": {
            "favorite": prediction.home_expected_goals,
            "opponent": prediction.away_expected_goals,
        },
        "feature_diffs": {
            "attack_diff": round(features.attack_diff, 2),
            "defense_diff": round(features.defense_diff, 2),
            "strength_diff": round(features.strength_diff, 2),
            "tactical_modifier": round(features.tactical_modifier, 4),
        },
        "log_goal_contributions": contributions,
        "primary_negative_driver": primary_negative_driver(contributions),
    }


def select_watchlist_rows(rows: list[dict], team_id: str, limit: int) -> list[dict]:
    team_rows = [row for row in rows if row["favorite_team_id"] == team_id and row["implausible_favorite"]]
    if not team_rows:
        team_rows = [row for row in rows if row["favorite_team_id"] == team_id]
    return sorted(team_rows, key=lambda row: row["favorite_win_pct"])[:limit]


def build_report(top_team_limit: int = 20, watchlist_limit: int = 8, matchups_per_team: int = 5) -> dict:
    teams = load_json(SEED_DIR / "teams.json")
    seed_players = load_json(SEED_DIR / "players.json")
    rating_rows = load_json(SEED_DIR / "playerRatings2026_estimated.json")
    players_by_team = build_player_lookup(seed_players, rating_rows)
    ranked = top_ranked_teams(teams, top_team_limit)
    squad_gap_report = latest_report("squad_rating_gap_review_*.json")
    watchlist_ids = watchlist_team_ids(squad_gap_report, watchlist_limit)

    all_rows = []
    for i, home in enumerate(ranked):
        for away in ranked[i + 1:]:
            row = build_matchup_driver_row(home, away, players_by_team)
            if row is not None:
                all_rows.append(row)

    watchlist_sections = []
    for team_id in watchlist_ids:
        selected = select_watchlist_rows(all_rows, team_id, matchups_per_team)
        watchlist_sections.append({
            "team_id": team_id,
            "summary": driver_summary([row for row in all_rows if row["favorite_team_id"] == team_id]),
            "lowest_matchup_drivers": selected,
        })

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "modelVersion": DEFAULT_MODEL_CONFIG.model_version,
        "note": (
            "Read-only driver audit for watchlist matchups. It decomposes the current model's log-goal "
            "inputs into attack, defense, strength, tactical, and home-order contributions so future rating "
            "reviews can see which feature is dragging a better-ranked team down. It does not change predictions."
        ),
        "sourceReports": [
            {"name": "squad_rating_gap_review", "generatedAt": (squad_gap_report or {}).get("generatedAt")}
        ],
        "scope": {
            "topTeamLimit": top_team_limit,
            "watchlistLimit": watchlist_limit,
            "matchupsPerTeam": matchups_per_team,
            "rankedTeamCount": len(ranked),
            "allMatchupCount": len(all_rows),
        },
        "overallDriverSummary": driver_summary(all_rows),
        "watchlistTeams": watchlist_sections,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-team-limit", type=int, default=20)
    parser.add_argument("--watchlist-limit", type=int, default=8)
    parser.add_argument("--matchups-per-team", type=int, default=5)
    args = parser.parse_args()

    report = build_report(args.top_team_limit, args.watchlist_limit, args.matchups_per_team)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"matchup_driver_audit_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"All matchups: {report['scope']['allMatchupCount']}")
    for section in report["watchlistTeams"][:5]:
        counts = section["summary"]["primary_negative_driver_counts"]
        print(f"  {section['team_id']:4s} negative_drivers={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
