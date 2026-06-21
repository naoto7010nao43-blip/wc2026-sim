"""Penalty shootout resolution for knockout matches still level after extra time.

Standard FIFA shootout rules: 5 kicks per team alternating, sudden death
one-by-one after that, with the option to stop a 5-kick round early once
the outcome is mathematically decided.
"""

import random

from app.engine.events import make_event
from app.engine.state import PlayerState, TeamState

PENALTY_ROUNDS = 5


def compute_penalty_success(shooter: PlayerState, keeper: PlayerState) -> float:
    shooting = shooter.attributes.get("shooting", 50)
    composure = shooter.overall
    gk_reflexes = keeper.attributes.get("gk_reflexes", 50)
    base = 0.76 + (shooting - 60) * 0.003 + (composure - 70) * 0.001 - (gk_reflexes - 60) * 0.004
    return max(0.45, min(0.93, base))


def _taker_order(outfield: list[PlayerState]) -> list[PlayerState]:
    return sorted(outfield, key=lambda p: p.attributes.get("shooting", 0), reverse=True)


def _take_kick(shooter: PlayerState, keeper: PlayerState, rng: random.Random) -> bool:
    return rng.random() < compute_penalty_success(shooter, keeper)


def resolve_shootout(home: TeamState, away: TeamState, rng: random.Random, start_minute: int = 120) -> dict:
    home_order = _taker_order(home.outfield())
    away_order = _taker_order(away.outfield())
    home_keeper = home.goalkeeper()
    away_keeper = away.goalkeeper()

    home_score = 0
    away_score = 0
    home_idx = 0
    away_idx = 0
    events: list[dict] = []

    def kick(shooter: PlayerState, keeper: PlayerState, shooter_team_id: str) -> bool:
        scored = _take_kick(shooter, keeper, rng)
        description = f"{shooter.display_name} が決めた!" if scored else f"{shooter.display_name} は外した。"
        events.append(make_event(
            start_minute, "penalty_kick", shooter_team_id,
            description,
            player_id=shooter.player_id, secondary_player_id=keeper.player_id,
            event_metadata={"scored": scored},
        ))
        return scored

    for round_num in range(1, PENALTY_ROUNDS + 1):
        if home_score != away_score:
            remaining_rounds = PENALTY_ROUNDS - (round_num - 1)
            if home_score > away_score + remaining_rounds or away_score > home_score + remaining_rounds:
                break
        if kick(home_order[home_idx % len(home_order)], away_keeper, home.team_id):
            home_score += 1
        home_idx += 1
        if kick(away_order[away_idx % len(away_order)], home_keeper, away.team_id):
            away_score += 1
        away_idx += 1

    while home_score == away_score:
        if kick(home_order[home_idx % len(home_order)], away_keeper, home.team_id):
            home_score += 1
        home_idx += 1
        if kick(away_order[away_idx % len(away_order)], home_keeper, away.team_id):
            away_score += 1
        away_idx += 1

    winner_team_id = home.team_id if home_score > away_score else away.team_id
    events.append(make_event(
        start_minute, "shootout_winner", winner_team_id,
        f"PK戦は {home_score}-{away_score} で {winner_team_id} が勝利。",
        event_metadata={"home_penalty_score": home_score, "away_penalty_score": away_score},
    ))

    return {
        "home_penalty_score": home_score,
        "away_penalty_score": away_score,
        "winner_team_id": winner_team_id,
        "events": events,
    }
