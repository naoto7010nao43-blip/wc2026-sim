"""Derives a plausible, clearly-simulated match narrative (starting XIs,
possession, shots, goal scorers) on top of a Poisson-model scoreline.

The Poisson model (poisson_model.py) outputs only a scoreline -- the most
accurate predictor we have -- but a user inspecting a simulated tournament
fixture wants to see *how* it might have played out: who scored, how the
possession split, how many shots each side took. This module layers those
supporting stats on top WITHOUT changing the scoreline: the number of goal
events it emits always equals the Poisson scoreline, and every figure is a
deterministic function of the match seed (re-fetching a match is stable).

These are simulation outputs, never presented as real-world data -- the
match's data_source stays "poisson-model" and the prediction disclaimer
still applies.
"""

import random

from app.engine.events import make_event
from app.engine.state import build_team_state

# Per-formation-slot goal propensity (relative). Multiplied by a player's
# overall to weight scorer selection: forwards score most, defenders rarely,
# the goalkeeper effectively never.
SLOT_GOAL_WEIGHTS: dict[str, float] = {
    "ST": 1.0,
    "LW": 0.70, "RW": 0.70,
    "CAM": 0.55,
    "LM": 0.45, "RM": 0.45,
    "CM": 0.32,
    "CDM": 0.16,
    "LB": 0.12, "RB": 0.12,
    "CB": 0.16,
    "GK": 0.0,
}
DEFAULT_GOAL_WEIGHT = 0.30


def _lineup_snapshot(team_state) -> list[dict]:
    return [
        {
            "player_id": p.player_id,
            "name": p.display_name,
            "slot_position": p.slot_position,
            "x": round(p.x, 1),
            "y": round(p.y, 1),
        }
        for p in team_state.lineup
    ]


def _possession_split(home_state, away_state, rng: random.Random) -> tuple[int, int]:
    """Possession share from each side's average starting-XI overall and its
    possession_style tactical profile, plus a small seeded jitter. Clamped to
    a realistic 35-65 band and forced to sum to 100."""
    def control(state) -> float:
        if not state.lineup:
            return 1.0
        avg_overall = sum(p.overall for p in state.lineup) / len(state.lineup)
        possession_style = state.tactical_profile.get("possession_style", 50.0)
        return avg_overall * (0.80 + 0.40 * possession_style / 100.0)

    ch, ca = control(home_state), control(away_state)
    raw_home = 100.0 * ch / (ch + ca) + rng.uniform(-2.5, 2.5)
    home_pct = round(max(35.0, min(65.0, raw_home)))
    return home_pct, 100 - home_pct


def _shots(expected_goals: float, actual_goals: int, rng: random.Random) -> tuple[int, int]:
    """A plausible shot count from the Poisson expected goals, with shots on
    target between the actual goals scored and the total shot count."""
    shots = round(expected_goals * rng.uniform(8.5, 11.5)) + rng.randint(2, 5)
    shots = max(shots, actual_goals + 2)
    on_target = round(shots * rng.uniform(0.30, 0.42))
    on_target = max(on_target, actual_goals)
    on_target = min(on_target, shots)
    return shots, on_target


def _yellow_cards(state, rng: random.Random) -> int:
    press = state.tactical_profile.get("press_intensity", 50.0)
    base = 1.0 + press / 50.0
    return max(0, min(5, round(rng.gauss(base, 1.0))))


def _scorer_events(team_state, n_goals: int, team_id: str, rng: random.Random) -> list[dict]:
    """Emit n_goals goal events, each attributed to a starting-XI player
    chosen (with replacement -- a player can score a brace) weighted by slot
    goal propensity x overall. Minutes are random and sorted."""
    if n_goals == 0 or not team_state.lineup:
        return []
    players = list(team_state.lineup)
    weights = [
        max(SLOT_GOAL_WEIGHTS.get(p.slot_position, DEFAULT_GOAL_WEIGHT) * p.overall, 0.0)
        for p in players
    ]
    if sum(weights) <= 0:
        weights = [1.0] * len(players)
    events = []
    for minute in sorted(rng.randint(1, 90) for _ in range(n_goals)):
        scorer = rng.choices(players, weights=weights, k=1)[0]
        events.append(make_event(
            minute, "goal", team_id,
            f"{scorer.display_name} がゴール!",
            player_id=scorer.player_id,
        ))
    return events


def build_predicted_narrative(
    home_team_id: str,
    away_team_id: str,
    home_players: list[dict],
    away_players: list[dict],
    home_formation: str,
    away_formation: str,
    home_tactical_profile: dict | None,
    away_tactical_profile: dict | None,
    home_score: int,
    away_score: int,
    lambda_home: float,
    lambda_away: float,
    rng: random.Random,
) -> dict:
    """Build the starting XIs, supporting stats and goal-scorer timeline for a
    Poisson-predicted fixture. Returns a dict of the fields persist needs;
    `events` is [kickoff, ...sorted goals] (the caller appends any penalty
    shootout event and the fulltime event)."""
    home_state = build_team_state(home_team_id, home_players, home_formation, 1, home_tactical_profile)
    away_state = build_team_state(away_team_id, away_players, away_formation, -1, away_tactical_profile)

    home_lineup = _lineup_snapshot(home_state)
    away_lineup = _lineup_snapshot(away_state)

    home_poss, away_poss = _possession_split(home_state, away_state, rng)
    home_shots, home_sot = _shots(lambda_home, home_score, rng)
    away_shots, away_sot = _shots(lambda_away, away_score, rng)

    goal_events = (
        _scorer_events(home_state, home_score, home_team_id, rng)
        + _scorer_events(away_state, away_score, away_team_id, rng)
    )
    goal_events.sort(key=lambda e: e["minute"])

    events = [make_event(0, "kickoff", home_team_id, "キックオフ。", x=50, y=50)]
    events.extend(goal_events)

    return {
        "home_lineup": home_lineup,
        "away_lineup": away_lineup,
        "home_roster": {p["player_id"]: p["name"] for p in home_lineup},
        "away_roster": {p["player_id"]: p["name"] for p in away_lineup},
        "home_possession_pct": home_poss,
        "away_possession_pct": away_poss,
        "home_shots": home_shots,
        "away_shots": away_shots,
        "home_shots_on_target": home_sot,
        "away_shots_on_target": away_sot,
        "home_yellow_cards": _yellow_cards(home_state, rng),
        "away_yellow_cards": _yellow_cards(away_state, rng),
        "events": events,
    }
