"""One-off analysis: runs the match engine many times across a spread of
real seeded matchups (favourite-vs-underdog, evenly matched, etc.) and
reports aggregate statistics, compared against known real-world football
benchmarks. Read-only -- does not touch the database.

Usage: ./venv/Scripts/python.exe scripts/analyze_simulation_quality.py
"""

import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.engine.simulator import simulate_match
from app.models.player import Player
from app.models.team import Team

N_SEEDS = 60

# A spread of matchups: (home, away, label) -- picked from the actual 2026
# field to cover big-favourite, mid-tier, and close-on-paper pairings.
MATCHUPS = [
    ("ARG", "FRA", "top vs top"),
    ("BRA", "ENG", "top vs top"),
    ("ESP", "GER", "top vs top"),
    ("ARG", "NZL", "favourite vs minnow"),
    ("FRA", "PAN", "favourite vs minnow"),
    ("BRA", "JOR", "favourite vs minnow"),
    ("JPN", "KOR", "evenly matched"),
    ("MEX", "USA", "evenly matched"),
    ("NED", "BEL", "evenly matched"),
    ("POR", "MAR", "mid vs mid"),
]


def team_players_as_dicts(db, team_id: str) -> list[dict]:
    players = db.scalars(select(Player).where(Player.team_id == team_id)).all()
    return [
        {
            "id": p.id, "name": p.name, "name_ja": p.name_ja,
            "primary_position": p.primary_position,
            "secondary_positions": p.secondary_positions,
            "overall": p.overall, "attributes": p.attributes,
            "stamina_max": p.stamina_max,
        }
        for p in players
    ]


def main():
    db = SessionLocal()
    all_goals_per_match = []
    all_draws = 0
    all_matches = 0
    home_wins = 0
    away_wins = 0
    possession_diffs = []
    shots_per_match = []
    sot_conversion_rates = []
    yellow_per_match = []
    overall_gap_to_outcome = []  # (overall_gap, result) for calibration check

    print(f"{'matchup':22s} {'label':22s} {'avgGoals':>9s} {'drawRate':>9s} {'favWinRate':>11s} {'avgPoss(home)':>14s}")

    for home_id, away_id, label in MATCHUPS:
        home_team = db.get(Team, home_id)
        away_team = db.get(Team, away_id)
        if home_team is None or away_team is None:
            print(f"skip {home_id}-{away_id}: team not found")
            continue
        home_players = team_players_as_dicts(db, home_id)
        away_players = team_players_as_dicts(db, away_id)
        if len(home_players) < 11 or len(away_players) < 11:
            print(f"skip {home_id}-{away_id}: insufficient players")
            continue

        home_overall_avg = statistics.mean(p["overall"] for p in home_players)
        away_overall_avg = statistics.mean(p["overall"] for p in away_players)
        gap = home_overall_avg - away_overall_avg

        goals, draws, h_wins, a_wins = [], 0, 0, 0
        poss, shots, sot, yellows = [], [], [], []

        for seed in range(N_SEEDS):
            result = simulate_match(
                home_team_id=home_id, away_team_id=away_id,
                home_players=home_players, away_players=away_players,
                home_formation=home_team.default_formation,
                away_formation=away_team.default_formation,
                seed=seed, allow_draw=True,
                home_tactical_profile=home_team.tactical_profile,
                away_tactical_profile=away_team.tactical_profile,
            )
            hs, asc = result["home_score"], result["away_score"]
            goals.append(hs + asc)
            if hs > asc:
                h_wins += 1
            elif asc > hs:
                a_wins += 1
            else:
                draws += 1
            poss.append(result["home_possession_pct"])
            shots.append(result["home_shots"] + result["away_shots"])
            total_sot = result["home_shots_on_target"] + result["away_shots_on_target"]
            total_goals = hs + asc
            if total_sot > 0:
                sot.append(total_goals / total_sot)
            yellows.append(result["home_yellow_cards"] + result["away_yellow_cards"])

        avg_goals = statistics.mean(goals)
        draw_rate = draws / N_SEEDS
        fav_win_rate = (h_wins if gap >= 0 else a_wins) / N_SEEDS
        avg_poss_home = statistics.mean(poss)

        print(f"{home_id+'-'+away_id:22s} {label:22s} {avg_goals:9.2f} {draw_rate:9.1%} {fav_win_rate:11.1%} {avg_poss_home:14.1f}")

        all_goals_per_match.extend(goals)
        all_draws += draws
        all_matches += N_SEEDS
        home_wins += h_wins
        away_wins += a_wins
        possession_diffs.append(abs(avg_poss_home - 50.0))
        shots_per_match.extend(shots)
        sot_conversion_rates.extend(sot)
        yellow_per_match.extend(yellows)
        overall_gap_to_outcome.append((gap, h_wins / N_SEEDS, draw_rate, a_wins / N_SEEDS))

    print()
    print("=== Aggregate (all matchups, all seeds) ===")
    print(f"avg goals/match:        {statistics.mean(all_goals_per_match):.2f}  (real W.Cup benchmark: ~2.5-2.8)")
    print(f"draw rate:              {all_draws/all_matches:.1%}  (real group-stage benchmark: ~20-27%)")
    print(f"home win rate:          {home_wins/all_matches:.1%}")
    print(f"away win rate:          {away_wins/all_matches:.1%}")
    print(f"avg |possession-50|:    {statistics.mean(possession_diffs):.1f}  (sanity: should scale with skill gap, not be ~0 always)")
    print(f"avg shots/match (both): {statistics.mean(shots_per_match):.1f}  (real benchmark: ~22-26 combined)")
    print(f"goals per shot-on-target: {statistics.mean(sot_conversion_rates):.2f}  (real benchmark: ~0.3 i.e. 30% conv, so this ratio ~0.3)")
    print(f"avg yellows/match:      {statistics.mean(yellow_per_match):.2f}  (real benchmark: ~3-4)")
    print()
    print("=== Calibration: skill gap (home_overall - away_overall) vs outcome rate ===")
    for gap, hwr, dr, awr in sorted(overall_gap_to_outcome, key=lambda t: t[0]):
        print(f"  gap={gap:+6.2f}  home_win={hwr:.1%}  draw={dr:.1%}  away_win={awr:.1%}")

    db.close()


if __name__ == "__main__":
    main()
