"""Compare read-only team aggregation variants against the frozen benchmark.

Recent audits found that small player-rating probes do not reduce watchlist
implausibility, while top teams' seed/rating layer is compressed. This script
tests alternate team-strength aggregation variants in memory only so a future
formula spec can be evidence-led instead of guessed.

Read-only: does not mutate seed data, ratings, formulas, or prediction
behavior.

Usage: ./venv/Scripts/python.exe scripts/build_aggregation_calibration_sandbox.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.prediction.model_config import DEFAULT_MODEL_CONFIG  # noqa: E402
from app.prediction.poisson_model import lambdas_from_ratings, score_distribution  # noqa: E402
from app.prediction.ratings import attack_rating, defense_rating, squad_strength_rating  # noqa: E402
from build_prediction_benchmark_baseline import (  # noqa: E402
    SEED_DIR,
    build_player_lookup,
    BENCHMARK_ORDERING_METHOD,
    is_implausible_favorite,
    latest_report,
    load_json,
    minimum_expected_favorite_win_pct,
    rank_gap_bucket,
    summarize_by_bucket,
    summarize_matchups,
    summarize_watchlist,
    top_ranked_teams,
    watchlist_team_ids,
)
from compare_prediction_benchmarks import compare_reports  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

VARIANTS = [
    {
        "id": "rank70_current_squad30",
        "label": "FIFAランク比重70% + 現行ベストXI平均30%",
        "rank_weight": 0.70,
        "squad_method": "current",
    },
    {
        "id": "rank75_current_squad25",
        "label": "FIFAランク比重75% + 現行ベストXI平均25%",
        "rank_weight": 0.75,
        "squad_method": "current",
    },
    {
        "id": "rank65_elite_squad35",
        "label": "FIFAランク比重65% + エリート重視スカッド35%",
        "rank_weight": 0.65,
        "squad_method": "elite_weighted",
    },
    {
        "id": "rank70_elite_squad30",
        "label": "FIFAランク比重70% + エリート重視スカッド30%",
        "rank_weight": 0.70,
        "squad_method": "elite_weighted",
    },
]


def rank_score(fifa_rank: int | None) -> float | None:
    if fifa_rank is None:
        return None
    return max(35.0, 95.0 - 8.0 * ((fifa_rank ** 0.5) - 1))


def top_average(players: list[dict], n: int) -> float:
    if not players:
        return 50.0
    values = [row["overall"] for row in sorted(players, key=lambda row: -row["overall"])[:n]]
    return sum(values) / len(values)


def elite_weighted_squad_strength(players: list[dict]) -> float:
    if not players:
        return 50.0
    top3 = top_average(players, 3)
    top8 = top_average(players, 8)
    top11 = top_average(players, 11)
    return top3 * 0.45 + top8 * 0.35 + top11 * 0.20


def squad_component(players: list[dict], method: str) -> float:
    if method == "current":
        return squad_strength_rating(players)
    if method == "elite_weighted":
        return elite_weighted_squad_strength(players)
    raise ValueError(f"unknown squad method: {method}")


def team_strength_variant(fifa_rank: int | None, players: list[dict], variant: dict) -> tuple[float, str]:
    squad = squad_component(players, variant["squad_method"])
    if fifa_rank is None:
        return squad, "estimated"
    rank = rank_score(fifa_rank)
    rank_weight = variant["rank_weight"]
    return rank * rank_weight + squad * (1 - rank_weight), "estimated"


def team_ratings_for_variant(team: dict, players: list[dict], variant: dict) -> dict:
    strength, confidence = team_strength_variant(team.get("fifa_rank"), players, variant)
    return {
        "team_id": team["id"],
        "team_name": team["name"],
        "fifa_rank": team.get("fifa_rank"),
        "attack": round(attack_rating(players), 1),
        "defense": round(defense_rating(players), 1),
        "strength": round(strength, 1),
        "squad_component": round(squad_component(players, variant["squad_method"]), 1),
        "rank_score": None if team.get("fifa_rank") is None else round(rank_score(team.get("fifa_rank")), 1),
        "data_confidence": confidence,
    }


def matchup_probabilities(lambda_home: float, lambda_away: float) -> tuple[float, float, float, list[dict]]:
    matrix = score_distribution(lambda_home, lambda_away, DEFAULT_MODEL_CONFIG.max_goals)
    size = len(matrix)
    home_win = sum(matrix[h][a] for h in range(size) for a in range(size) if h > a)
    draw = sum(matrix[h][a] for h in range(size) for a in range(size) if h == a)
    away_win = sum(matrix[h][a] for h in range(size) for a in range(size) if h < a)
    scored = sorted(
        ((h, a, matrix[h][a]) for h in range(size) for a in range(size)),
        key=lambda row: -row[2],
    )
    top_scores = [
        {"home_goals": h, "away_goals": a, "probability_pct": round(p * 100, 1)}
        for h, a, p in scored[:3]
    ]
    return round(home_win * 100, 1), round(draw * 100, 1), round(away_win * 100, 1), top_scores


def average_pair(a: float | int, b: float | int, digits: int = 1) -> float:
    return round((float(a) + float(b)) / 2, digits)


def build_variant_matchup_row(home: dict, away: dict, team_ratings: dict[str, dict]) -> dict:
    home_rating = team_ratings[home["id"]]
    away_rating = team_ratings[away["id"]]
    favorite_home_lambda, opponent_away_lambda = lambdas_from_ratings(
        home_rating["attack"],
        home_rating["defense"],
        home_rating["strength"],
        home_rating["data_confidence"],
        away_rating["attack"],
        away_rating["defense"],
        away_rating["strength"],
        away_rating["data_confidence"],
        home.get("tactical_profile"),
        away.get("tactical_profile"),
    )
    opponent_home_lambda, favorite_away_lambda = lambdas_from_ratings(
        away_rating["attack"],
        away_rating["defense"],
        away_rating["strength"],
        away_rating["data_confidence"],
        home_rating["attack"],
        home_rating["defense"],
        home_rating["strength"],
        home_rating["data_confidence"],
        away.get("tactical_profile"),
        home.get("tactical_profile"),
    )
    favorite_home_win_pct, favorite_home_draw_pct, opponent_away_win_pct, top_scores = matchup_probabilities(
        favorite_home_lambda,
        opponent_away_lambda,
    )
    opponent_home_win_pct, favorite_away_draw_pct, favorite_away_win_pct, _ = matchup_probabilities(
        opponent_home_lambda,
        favorite_away_lambda,
    )
    favorite_win_pct = average_pair(favorite_home_win_pct, favorite_away_win_pct)
    draw_pct = average_pair(favorite_home_draw_pct, favorite_away_draw_pct)
    opponent_win_pct = average_pair(opponent_away_win_pct, opponent_home_win_pct)
    gap = (away.get("fifa_rank") or 0) - (home.get("fifa_rank") or 0)
    expected_floor = minimum_expected_favorite_win_pct(gap)
    return {
        "benchmark_ordering_method": BENCHMARK_ORDERING_METHOD,
        "home_team_id": home["id"],
        "away_team_id": away["id"],
        "home_fifa_rank": home.get("fifa_rank"),
        "away_fifa_rank": away.get("fifa_rank"),
        "rank_gap": gap,
        "rank_gap_bucket": rank_gap_bucket(gap),
        "home_win_pct": favorite_win_pct,
        "draw_pct": draw_pct,
        "away_win_pct": opponent_win_pct,
        "home_expected_goals": average_pair(favorite_home_lambda, favorite_away_lambda, digits=2),
        "away_expected_goals": average_pair(opponent_away_lambda, opponent_home_lambda, digits=2),
        "favorite_team_id": home["id"],
        "opponent_team_id": away["id"],
        "favorite_win_pct": favorite_win_pct,
        "favorite_home_win_pct": favorite_home_win_pct,
        "favorite_away_win_pct": favorite_away_win_pct,
        "minimum_expected_favorite_win_pct": expected_floor,
        "implausible_favorite": is_implausible_favorite(favorite_win_pct, gap),
        "most_likely_scores": top_scores,
        "score_ordering_note": "most_likely_scores keep the favorite-home order for readability; probability fields are dual-order averages.",
        "data_confidence": "estimated",
    }


def build_variant_benchmark(variant: dict, top_team_limit: int, watchlist_limit: int) -> dict:
    teams = load_json(SEED_DIR / "teams.json")
    seed_players = load_json(SEED_DIR / "players.json")
    rating_rows = load_json(SEED_DIR / "playerRatings2026_estimated.json")
    squad_gap_report = latest_report("squad_rating_gap_review_*.json")
    players_by_team = build_player_lookup(seed_players, rating_rows)
    ranked = top_ranked_teams(teams, top_team_limit)
    watchlist_ids = watchlist_team_ids(squad_gap_report, watchlist_limit)

    team_ratings = {
        team["id"]: team_ratings_for_variant(team, players_by_team.get(team["id"], []), variant)
        for team in ranked
    }
    matchups = []
    for i, home in enumerate(ranked):
        for away in ranked[i + 1:]:
            if home["id"] in team_ratings and away["id"] in team_ratings:
                matchups.append(build_variant_matchup_row(home, away, team_ratings))
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "modelVersion": f"aggregation-sandbox:{variant['id']}",
        "note": (
            "Read-only aggregation calibration sandbox. This report compares an in-memory formula variant "
            "against the frozen prediction benchmark and does not change production model code."
        ),
        "sourceReports": [
            {"name": "squad_rating_gap_review", "generatedAt": (squad_gap_report or {}).get("generatedAt")}
        ],
        "scope": {
            "topTeamLimit": top_team_limit,
            "watchlistLimit": watchlist_limit,
            "rankedTeamCount": len(ranked),
            "matchupCount": len(matchups),
            "benchmarkOrderingMethod": BENCHMARK_ORDERING_METHOD,
        },
        "teamRatings": list(team_ratings.values()),
        "overallSummary": summarize_matchups(matchups),
        "rankGapBuckets": summarize_by_bucket(matchups),
        "watchlistTeams": summarize_watchlist(matchups, watchlist_ids),
        "benchmarkMatchups": matchups,
    }


def best_variant(variant_rows: list[dict]) -> dict | None:
    if not variant_rows:
        return None
    return sorted(
        variant_rows,
        key=lambda row: (
            -row["comparison"]["evaluation"]["watchlist_implausible_reduction"],
            abs(row["comparison"]["overall"]["average_favorite_win_pct_delta"] or 0),
            row["variant_id"],
        ),
    )[0]


def build_report(top_team_limit: int = 20, watchlist_limit: int = 8) -> dict:
    baseline = latest_report("prediction_benchmark_baseline_*.json")
    rows = []
    for variant in VARIANTS:
        benchmark = build_variant_benchmark(variant, top_team_limit, watchlist_limit)
        comparison = compare_reports(baseline, benchmark) if baseline else None
        rows.append({
            "variant_id": variant["id"],
            "label_ja": variant["label"],
            "rank_weight": variant["rank_weight"],
            "squad_method": variant["squad_method"],
            "benchmark_summary": {
                "overallSummary": benchmark["overallSummary"],
                "watchlistTeams": benchmark["watchlistTeams"],
            },
            "comparison": comparison,
        })
    winner = best_variant([row for row in rows if row["comparison"]])
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "note": (
            "チーム強度集約式の代替案を本番コード変更なしで比較する読み取り専用サンドボックスです。"
            "結果は将来の明示的なフォーミュラ検証specの判断材料であり、このレポート自体は挙動を変えません。"
        ),
        "sourceReports": [
            {"name": "prediction_benchmark_baseline", "generatedAt": (baseline or {}).get("generatedAt")},
        ],
        "variantCount": len(rows),
        "bestVariantId": None if winner is None else winner["variant_id"],
        "variants": rows,
        "recommendations_ja": [
            "watchlist改善がない案は本番式変更候補にしない。",
            "改善がある案でも、全体平均勝率やランク差バケットの動きが大きい場合は別途レビューする。",
            "このサンドボックスで有望な案だけを、次の明示的なフォーミュラ検証specに進める。",
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
    out_path = REPORTS_DIR / f"aggregation_calibration_sandbox_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"Best variant: {report['bestVariantId']}")
    for row in report["variants"]:
        evaluation = row["comparison"]["evaluation"] if row["comparison"] else {}
        overall = row["comparison"]["overall"] if row["comparison"] else {}
        print(
            f"  {row['variant_id']}: "
            f"watchlist_reduction={evaluation.get('watchlist_implausible_reduction')} "
            f"avg_delta={overall.get('average_favorite_win_pct_delta')} "
            f"status={evaluation.get('status')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
