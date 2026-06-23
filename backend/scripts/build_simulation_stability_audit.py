"""Build a read-only Monte Carlo stability audit.

The product exposes tournament odds, but users need to know whether those odds
are stable enough to trust at the current iteration counts. This script samples
the same tournament model at multiple iteration counts and records how much
champion probabilities move as the sample grows.

It does not mutate seed data, ratings, formulas, matches, or DB state.

Usage:
  ./venv/Scripts/python.exe scripts/build_simulation_stability_audit.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base
from app.models.match import Match  # noqa: F401  ensures table registration
from app.models.player import Player
from app.models.team import Team
from app.prediction.monte_carlo import simulate_tournament_outcomes
from app.rating.seed_pipeline import build_player_rows, load_seed_data

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports"

DEFAULT_ITERATION_COUNTS = (200, 500, 1000)
DEFAULT_BASE_SEED = 20260624


def make_seeded_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    teams_raw, players_raw = load_seed_data()
    player_rows = build_player_rows(players_raw)
    for team in teams_raw:
        session.add(Team(
            id=team["id"],
            name=team["name"],
            confederation=team["confederation"],
            fifa_rank=team.get("fifa_rank"),
            default_formation=team["default_formation"],
            group_id=team.get("group_id"),
            tactical_profile=team.get("tactical_profile"),
        ))
    session.flush()
    for player in player_rows:
        session.add(Player(**player))
    session.commit()
    return session


def top_entries(values: dict[str, float], limit: int = 10) -> list[dict]:
    return [
        {"team_id": team_id, "pct": pct}
        for team_id, pct in sorted(values.items(), key=lambda row: (-row[1], row[0]))[:limit]
    ]


def pct_delta(a: float | None, b: float | None) -> float:
    return round((b or 0.0) - (a or 0.0), 1)


def compare_champion_sets(previous: dict[str, float], current: dict[str, float], top_ids: set[str]) -> dict:
    rows = []
    for team_id in sorted(top_ids):
        prev = previous.get(team_id, 0.0)
        curr = current.get(team_id, 0.0)
        rows.append({
            "team_id": team_id,
            "previous_pct": prev,
            "current_pct": curr,
            "delta_pct": pct_delta(prev, curr),
            "abs_delta_pct": abs(pct_delta(prev, curr)),
        })
    rows.sort(key=lambda row: (-row["abs_delta_pct"], row["team_id"]))
    return {
        "max_abs_delta_pct": rows[0]["abs_delta_pct"] if rows else 0.0,
        "average_abs_delta_pct": round(mean(row["abs_delta_pct"] for row in rows), 1) if rows else 0.0,
        "largest_movers": rows[:8],
    }


def stability_band(max_abs_delta_pct: float) -> str:
    if max_abs_delta_pct <= 2.0:
        return "stable"
    if max_abs_delta_pct <= 4.0:
        return "usable"
    return "volatile"


def build_report(iteration_counts: tuple[int, ...] = DEFAULT_ITERATION_COUNTS, base_seed: int = DEFAULT_BASE_SEED) -> dict:
    session = make_seeded_session()
    try:
        samples = []
        for iterations in iteration_counts:
            result = simulate_tournament_outcomes(session, iterations=iterations, base_seed=base_seed)
            champion_top = top_entries(result.champion_pct, limit=12)
            samples.append({
                "iterations": iterations,
                "modelVersion": result.model_version,
                "dataConfidence": result.data_confidence,
                "championCandidateCount": len(result.champion_pct),
                "topChampionCandidates": champion_top,
                "topChampionTeamId": champion_top[0]["team_id"] if champion_top else None,
                "topChampionPct": champion_top[0]["pct"] if champion_top else None,
                "topThreeChampionPct": round(sum(row["pct"] for row in champion_top[:3]), 1),
            })

        comparisons = []
        for previous, current in zip(samples, samples[1:]):
            previous_values = {row["team_id"]: row["pct"] for row in previous["topChampionCandidates"]}
            current_values = {row["team_id"]: row["pct"] for row in current["topChampionCandidates"]}
            top_ids = set(previous_values) | set(current_values)
            comparison = compare_champion_sets(previous_values, current_values, top_ids)
            comparison["fromIterations"] = previous["iterations"]
            comparison["toIterations"] = current["iterations"]
            comparison["stabilityBand"] = stability_band(comparison["max_abs_delta_pct"])
            comparisons.append(comparison)

        final_comparison = comparisons[-1] if comparisons else {"max_abs_delta_pct": 0.0, "stabilityBand": "stable"}
        recommendation = "current_default_usable"
        if final_comparison["stabilityBand"] == "volatile":
            recommendation = "use_higher_iterations_for_public_confidence"
        elif final_comparison["stabilityBand"] == "stable":
            recommendation = "current_default_stable"

        return {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "modelVersion": samples[-1]["modelVersion"] if samples else None,
            "note": (
                "モンテカルロ優勝確率はサンプルに基づく推定値です。この監査は複数の試行回数を同じ基準シードで比較し、"
                "上位候補の確率が表示用の目安として十分に安定しているかを確認します。予測ロジックや試合結果は変更しません。"
            ),
            "scope": {
                "iterationCounts": list(iteration_counts),
                "baseSeed": base_seed,
                "sampleCount": len(samples),
            },
            "samples": samples,
            "comparisons": comparisons,
            "summary": {
                "stabilityBand": final_comparison["stabilityBand"],
                "maxAbsChampionPctDelta": final_comparison["max_abs_delta_pct"],
                "averageAbsChampionPctDelta": final_comparison.get("average_abs_delta_pct", 0.0),
                "recommendation": recommendation,
                "recommendation_ja": {
                    "current_default_stable": "現在の試行回数でも上位候補の揺れは小さく、表示用の目安として安定しています。",
                    "current_default_usable": "現在の試行回数は表示用の目安として使えますが、上位候補の細かな差は幅を持って解釈してください。",
                    "use_higher_iterations_for_public_confidence": "上位候補の揺れが大きいため、公開説明や最終判断では試行回数を増やすべきです。",
                }[recommendation],
            },
            "sourceReports": [],
        }
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, nargs="+", default=list(DEFAULT_ITERATION_COUNTS))
    parser.add_argument("--base-seed", type=int, default=DEFAULT_BASE_SEED)
    args = parser.parse_args()

    report = build_report(tuple(args.iterations), args.base_seed)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"simulation_stability_audit_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = report["summary"]
    print(f"Wrote {out_path}")
    print(
        "Stability: "
        f"{summary['stabilityBand']} "
        f"max_delta={summary['maxAbsChampionPctDelta']} "
        f"recommendation={summary['recommendation']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
