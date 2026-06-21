"""Action selection and probability formulas for the possession-event loop."""

import math
import random

from app.engine.pitch import attacking_progress, distance, distance_to_target_goal
from app.engine.state import PlayerState, TeamState


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def clamp_prob(p: float, lo: float = 0.05, hi: float = 0.97) -> float:
    return max(lo, min(hi, p))


def decay_stamina(player: PlayerState, intensity: float = 1.0) -> None:
    base_decay = 0.35 * intensity
    player.current_stamina = max(0.0, player.current_stamina - base_decay)


def recover_stamina_halftime(team: TeamState) -> None:
    for p in team.lineup:
        p.current_stamina = min(p.stamina_max, p.current_stamina + 0.25 * p.stamina_max)


def nearest_player(team: TeamState, x: float, y: float, exclude_gk: bool = False) -> PlayerState:
    candidates = team.outfield() if exclude_gk else team.lineup
    return min(candidates, key=lambda p: distance((p.x, p.y), (x, y)))


def pick_ball_carrier(team: TeamState, ball_x: float, ball_y: float, rng: random.Random) -> PlayerState:
    """Weighted toward players closer to the ball, excluding the GK unless
    the ball is deep in their own defensive zone."""
    outfield = team.outfield()
    weights = []
    for p in outfield:
        d = distance((p.x, p.y), (ball_x, ball_y))
        weights.append(1.0 / (1.0 + d))
    return rng.choices(outfield, weights=weights, k=1)[0]


def compute_pass_success(passer: PlayerState, contest: PlayerState, pass_distance: float, press_intensity: float = 50.0) -> float:
    skill_diff = (passer.attributes["passing"] - contest.attributes["defending"]) * 0.045
    distance_penalty = pass_distance * 0.012
    stamina_bonus = (passer.stamina_factor() - 0.8) * 10
    press_penalty = (press_intensity - 50.0) * 0.012
    z = skill_diff - distance_penalty + stamina_bonus - press_penalty
    return clamp_prob(0.5 + 0.3 * math.tanh(z), 0.35, 0.95)


def compute_dribble_success(carrier: PlayerState, defender: PlayerState, press_intensity: float = 50.0, defensive_line_height: float = 50.0) -> float:
    compactness_bonus = (defensive_line_height - 50.0) * 0.05
    skill_diff = (carrier.attributes["dribbling"] - (defender.attributes["defending"] + compactness_bonus)) * 0.05
    stamina_bonus = (carrier.stamina_factor() - 0.8) * 8
    press_penalty = (press_intensity - 50.0) * 0.012
    z = skill_diff + stamina_bonus - press_penalty
    return clamp_prob(0.5 + 0.3 * math.tanh(z), 0.3, 0.9)


def compute_tackle_success(defender: PlayerState, attacker: PlayerState, press_intensity: float = 50.0) -> float:
    skill_diff = (defender.attributes["defending"] - attacker.attributes["dribbling"]) * 0.045
    stamina_bonus = (defender.stamina_factor() - 0.8) * 8
    press_bonus = (press_intensity - 50.0) * 0.01
    z = skill_diff + stamina_bonus + press_bonus
    return clamp_prob(0.5 + 0.3 * math.tanh(z), 0.15, 0.8)


def compute_shot_xg(
    shooter: PlayerState,
    keeper: PlayerState,
    shot_x: float,
    shot_y: float,
    pressure: float,
    attacking_direction: int,
    defensive_line_height: float = 50.0,
) -> float:
    dist_to_goal = distance_to_target_goal((shot_x, shot_y), attacking_direction)
    angle_penalty = abs(shot_y - 50) * 0.006
    distance_factor = max(0.0, 1.0 - dist_to_goal / 60.0)
    shooting_factor = (shooter.attributes["shooting"] / 99.0) * (shooter.stamina_factor())
    keeper_factor = 1.0 - (keeper.attributes.get("gk_reflexes") or 50) / 160.0
    pressure_penalty = pressure * 0.12 * (1 + (defensive_line_height - 50.0) / 150.0)

    base = 0.05 + 0.50 * distance_factor * shooting_factor * keeper_factor
    base -= angle_penalty + pressure_penalty
    return clamp_prob(base, 0.02, 0.6)


def maybe_foul_card(rng: random.Random, base_rate: float) -> str | None:
    """Returns None, "yellow", or "red" for a defensive challenge that wins
    the ball back. `base_rate` is the probability of any card at all; a
    small fraction of those escalate to red (reckless/last-man fouls,
    second yellows). Calibrated so a full match lands near real-world
    averages of ~3-4 yellows and roughly 1 red every several matches."""
    if rng.random() < base_rate:
        return "red" if rng.random() < 0.05 else "yellow"
    return None


def choose_pass_target(team: TeamState, carrier: PlayerState, rng: random.Random) -> PlayerState:
    """Pick a teammate (not the carrier) to receive the ball, weighted toward
    players who are further advanced in the attacking direction and not too far away."""
    candidates = [p for p in team.outfield() if p.player_id != carrier.player_id]
    weights = []
    for p in candidates:
        progress = attacking_progress(p.x, team.attacking_direction)
        d = distance((p.x, p.y), (carrier.x, carrier.y))
        weights.append(max(0.05, progress / 100.0) / (1.0 + d * 0.08))
    return rng.choices(candidates, weights=weights, k=1)[0]


def advance_position(pos: tuple[float, float], attacking_direction: int, step: float, rng: random.Random) -> tuple[float, float]:
    dx = step * attacking_direction
    dy = rng.uniform(-12, 12)
    return (max(0.0, min(100.0, pos[0] + dx)), max(0.0, min(100.0, pos[1] + dy)))


def choose_action(carrier: PlayerState, ball_x: float, ball_y: float, attacking_direction: int, rng: random.Random, possession_style: float = 50.0) -> str:
    """Choose among SHOOT, PASS, DRIBBLE, LONG_BALL based on zone, dribbling/shooting
    tendency, and the attacking team's possession_style (0=direct/long-ball, 100=possession)."""
    dist_to_goal = distance_to_target_goal((ball_x, ball_y), attacking_direction)

    # Shooting-range radius and trigger probability widened from an earlier,
    # too-conservative version that produced ~half the shots/match of real
    # football (calibrated against scripts/analyze_simulation_quality.py).
    if dist_to_goal < 30 and rng.random() < (0.22 + carrier.attributes["shooting"] / 250):
        return "SHOOT"

    style_shift = (possession_style - 50.0) * 0.004
    weights = {
        "PASS": max(0.1, 0.5 + style_shift),
        "DRIBBLE": 0.25 + carrier.attributes["dribbling"] / 400,
        "LONG_BALL": max(0.02, 0.15 - style_shift),
    }
    total = sum(weights.values())
    r = rng.random() * total
    cumulative = 0.0
    for action, w in weights.items():
        cumulative += w
        if r <= cumulative:
            return action
    return "PASS"
