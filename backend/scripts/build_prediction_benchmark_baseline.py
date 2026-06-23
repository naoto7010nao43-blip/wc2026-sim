"""Read-only prediction benchmark baseline for future rating-data changes.

This script freezes a deterministic set of current Poisson-model outputs so
Codex can later compare any proposed player-rating update against a known
baseline. It does not mutate seed data, rating data, formulas, model config,
or prediction behavior.

Usage: ./venv/Scripts/python.exe scripts/build_prediction_benchmark_baseline.py
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
from app.prediction.poisson_model import predict_match
from app.prediction.ratings import attack_rating, defense_rating, team_strength_rating

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report(pattern: str) -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(pattern))
    if not matches:
        return None
    return load_json(matches[-1])


def rank_gap_bucket(rank_gap: int) -> str:
    if rank_gap <= 2:
        return "00-02"
    if rank_gap <= 5:
        return "03-05"
    if rank_gap <= 10:
        return "06-10"
    if rank_gap <= 20:
        return "11-20"
    return "21+"


def minimum_expected_favorite_win_pct(rank_gap: int) -> float:
    """Same deliberately gentle plausibility bar as the simulation audit:
    a better-ranked side should not always dominate, but a large rank gap
    should usually show a visible favorite."""
    return min(33.0 + max(rank_gap, 0) * 1.2, 55.0)


def is_implausible_favorite(favorite_win_pct: float, rank_gap: int) -> bool:
    return favorite_win_pct < minimum_expected_favorite_win_pct(rank_gap)


def rating_attributes(rating: dict) -> dict:
    ignored = {
        "playerId", "teamId", "overall", "positionOverall", "startingProbability",
        "uncertainty", "dataConfidence", "sourceBreakdown", "lowConfidenceAttributes",
        "lastUpdated",
    }
    return {k: v for k, v in rating.items() if k not in ignored and isinstance(v, (int, float))}


def build_player_lookup(seed_players: list[dict], rating_rows: list[dict]) -> dict[str, list[dict]]:
    ratings_by_id = {row["playerId"]: row for row in rating_rows}
    by_team: dict[str, list[dict]] = defaultdict(list)
    for player in seed_players:
        rating = ratings_by_id.get(player["id"])
        if rating is None:
            continue
        by_team[player["team_id"]].append({
            "id": player["id"],
            "name": player["name"],
            "primary_position": player["primary_position"],
            "secondary_positions": player.get("secondary_positions", []),
            "overall": rating["overall"],
            "attributes": rating_attributes(rating),
            "stamina_max": player.get("stamina_max", rating.get("stamina", 50)),
        })
    return dict(by_team)


def top_ranked_teams(teams: list[dict], limit: int) -> list[dict]:
    ranked = [team for team in teams if team.get("fifa_rank") is not None]
    return sorted(ranked, key=lambda row: (row["fifa_rank"], row["id"]))[:limit]


def watchlist_team_ids(squad_gap_report: dict | None, limit: int = 8) -> list[str]:
    if not squad_gap_report:
        return []
    return [row["team_id"] for row in squad_gap_report.get("teams", [])[:limit]]


def compute_team_rating_row(team: dict, players: list[dict]) -> dict:
    strength, confidence = team_strength_rating(team.get("fifa_rank"), players)
    return {
        "team_id": team["id"],
        "team_name": team["name"],
        "fifa_rank": team.get("fifa_rank"),
        "player_count": len(players),
        "attack": round(attack_rating(players), 1),
        "defense": round(defense_rating(players), 1),
        "strength": round(strength, 1),
        "data_confidence": confidence,
    }


def build_matchup_row(home: dict, away: dict, players_by_team: dict[str, list[dict]]) -> dict | None:
    home_players = players_by_team.get(home["id"], [])
    away_players = players_by_team.get(away["id"], [])
    if len(home_players) < 11 or len(away_players) < 11:
        return None

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
    favorite_win_pct = prediction.home_win_pct
    expected_floor = minimum_expected_favorite_win_pct(rank_gap)
    return {
        "home_team_id": home["id"],
        "away_team_id": away["id"],
        "home_fifa_rank": home.get("fifa_rank"),
        "away_fifa_rank": away.get("fifa_rank"),
        "rank_gap": rank_gap,
        "rank_gap_bucket": rank_gap_bucket(rank_gap),
        "home_win_pct": prediction.home_win_pct,
        "draw_pct": prediction.draw_pct,
        "away_win_pct": prediction.away_win_pct,
        "home_expected_goals": prediction.home_expected_goals,
        "away_expected_goals": prediction.away_expected_goals,
        "favorite_team_id": home["id"],
        "favorite_win_pct": favorite_win_pct,
        "minimum_expected_favorite_win_pct": expected_floor,
        "implausible_favorite": is_implausible_favorite(favorite_win_pct, rank_gap),
        "most_likely_scores": [
            {"home_goals": h, "away_goals": a, "probability_pct": pct}
            for h, a, pct in prediction.most_likely_scores
        ],
        "data_confidence": prediction.data_confidence,
    }


def summarize_matchups(rows: list[dict]) -> dict:
    if not rows:
        return {
            "matchup_count": 0,
            "average_favorite_win_pct": None,
            "minimum_favorite_win_pct": None,
            "maximum_favorite_win_pct": None,
            "implausible_favorite_count": 0,
        }
    favorite_win_values = [row["favorite_win_pct"] for row in rows]
    return {
        "matchup_count": len(rows),
        "average_favorite_win_pct": round(mean(favorite_win_values), 1),
        "minimum_favorite_win_pct": min(favorite_win_values),
        "maximum_favorite_win_pct": max(favorite_win_values),
        "implausible_favorite_count": sum(1 for row in rows if row["implausible_favorite"]),
    }


def summarize_by_bucket(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["rank_gap_bucket"]].append(row)
    return [
        {"rank_gap_bucket": bucket, **summarize_matchups(grouped[bucket])}
        for bucket in sorted(grouped)
    ]


def summarize_watchlist(rows: list[dict], watchlist_ids: list[str]) -> list[dict]:
    output = []
    for team_id in watchlist_ids:
        team_rows = [row for row in rows if row["favorite_team_id"] == team_id]
        summary = summarize_matchups(team_rows)
        output.append({
            "team_id": team_id,
            **summary,
            "lowest_favorite_matchups": sorted(
                (
                    {
                        "away_team_id": row["away_team_id"],
                        "rank_gap": row["rank_gap"],
                        "favorite_win_pct": row["favorite_win_pct"],
                        "minimum_expected_favorite_win_pct": row["minimum_expected_favorite_win_pct"],
                    }
                    for row in team_rows
                ),
                key=lambda row: row["favorite_win_pct"],
            )[:5],
        })
    return output


def build_report(top_team_limit: int = 20, watchlist_limit: int = 8) -> dict:
    teams = load_json(SEED_DIR / "teams.json")
    seed_players = load_json(SEED_DIR / "players.json")
    rating_rows = load_json(SEED_DIR / "playerRatings2026_estimated.json")
    players_by_team = build_player_lookup(seed_players, rating_rows)
    ranked = top_ranked_teams(teams, top_team_limit)
    squad_gap_report = latest_report("squad_rating_gap_review_*.json")
    watchlist_ids = watchlist_team_ids(squad_gap_report, watchlist_limit)

    matchups = []
    for i, home in enumerate(ranked):
        for away in ranked[i + 1:]:
            row = build_matchup_row(home, away, players_by_team)
            if row is not None:
                matchups.append(row)

    team_ratings = [
        compute_team_rating_row(team, players_by_team.get(team["id"], []))
        for team in ranked
    ]

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "modelVersion": DEFAULT_MODEL_CONFIG.model_version,
        "note": (
            "Future rating changes should be compared against this read-only baseline before approval. "
            "The report freezes current prediction outputs for a deterministic top-ranked-team sample; "
            "it does not change seed data, ratings, formulas, or prediction behavior."
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
        "teamRatings": team_ratings,
        "overallSummary": summarize_matchups(matchups),
        "rankGapBuckets": summarize_by_bucket(matchups),
        "watchlistTeams": summarize_watchlist(matchups, watchlist_ids),
        "benchmarkMatchups": matchups,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-team-limit", type=int, default=20)
    parser.add_argument("--watchlist-limit", type=int, default=8)
    args = parser.parse_args()

    report = build_report(args.top_team_limit, args.watchlist_limit)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"prediction_benchmark_baseline_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = report["overallSummary"]
    print(f"Wrote {out_path}")
    print(
        "Matchups: "
        f"{summary['matchup_count']} "
        f"avg_favorite_win={summary['average_favorite_win_pct']} "
        f"implausible={summary['implausible_favorite_count']}"
    )
    print("Watchlist teams:")
    for row in report["watchlistTeams"]:
        print(f"  {row['team_id']:4s} matchups={row['matchup_count']:2d} min_win={row['minimum_favorite_win_pct']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
