"""Action selection and probability formulas for the possession-event loop."""

import math
import random

from app.engine.pitch import attacking_progress, distance, distance_to_target_goal, zone_for_progress
from app.engine.state import PlayerState, TeamState

# Role group used to weight ball-carrier selection by zone, so a center-back
# rarely ends up as the one dribbling deep into the attacking third during
# open play (real CB goals are overwhelmingly set-piece headers, not
# self-created dribbles) -- the bench/lineup picker still allows a CB
# secondary-position fallback, this only governs in-possession positioning.
_ROLE_GROUP: dict[str, str] = {
    "GK": "GK", "CB": "DEF", "LB": "DEF", "RB": "DEF",
    "CDM": "MID", "CM": "MID", "CAM": "MID", "LM": "MID", "RM": "MID",
    "ST": "ATT", "LW": "ATT", "RW": "ATT",
}
_ZONE_ROLE_WEIGHT: dict[str, dict[str, float]] = {
    "DEF_THIRD": {"DEF": 1.0, "MID": 0.9, "ATT": 0.6},
    "MID_THIRD": {"DEF": 0.75, "MID": 1.0, "ATT": 0.95},
    "ATT_THIRD": {"DEF": 0.4, "MID": 0.95, "ATT": 1.0},
}
# Defenders snap back to shape quickly (real positional discipline); midfield
# and attacking roles recover more slowly so a CAM/winger making a forward
# run can sustain an advanced position long enough to credibly be the one
# who arrives to finish -- otherwise every chance funnels to whichever
# player's *nominal* slot happens to sit nearest goal (the striker) instead
# of reflecting an actual attacking sequence.
_GRAVITY_BY_ROLE: dict[str, float] = {"GK": 0.05, "DEF": 0.18, "MID": 0.06, "ATT": 0.04}


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
    """Weighted toward players closer to the ball, scaled by how well their
    role fits the current zone (a CB is much less likely than a midfielder
    or forward to be the one carrying the ball deep into the attacking
    third, even if they happen to be nearby)."""
    outfield = team.outfield()
    progress = attacking_progress(ball_x, team.attacking_direction)
    role_weights = _ZONE_ROLE_WEIGHT[zone_for_progress(progress)]
    weights = []
    for p in outfield:
        # Dampened (sqrt) distance penalty: a flat 1/(1+d) let whichever
        # attacker's *nominal* slot is literally nearest the goal point
        # (almost always the central striker) dominate every chance near
        # goal, crowding out wingers/attacking mids arriving from the side
        # or from deeper -- real attacking sequences involve more than the
        # single closest player.
        d = distance((p.x, p.y), (ball_x, ball_y))
        role = _ROLE_GROUP.get(p.slot_position, "MID")
        weights.append(role_weights.get(role, 0.8) / (1.0 + d ** 0.5))
    return rng.choices(outfield, weights=weights, k=1)[0]


def apply_positional_gravity(team: TeamState, exclude: PlayerState | None) -> None:
    """Pulls every outfield player (except the one currently on the ball)
    a step back toward their formation slot's nominal position each tick.
    Without this, a single successful dribble would permanently relocate a
    player (e.g. a CB who broke forward once) for the rest of the match,
    instead of them recovering defensive shape within a few minutes like a
    real team would."""
    for p in team.outfield():
        if p is exclude:
            continue
        g = _GRAVITY_BY_ROLE.get(_ROLE_GROUP.get(p.slot_position, "MID"), 0.08)
        p.x += (p.home_x - p.x) * g
        p.y += (p.home_y - p.y) * g


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

    base = 0.05 + 0.54 * distance_factor * shooting_factor * keeper_factor
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
    # Re-widened again after the positional-realism fix (pick_ball_carrier's
    # sqrt-damped distance weighting + role-aware gravity) added more
    # friction to reaching the box at all, which had pulled shot/goal volume
    # back down below benchmark.
    if dist_to_goal < 34 and rng.random() < (0.27 + carrier.attributes["shooting"] / 220):
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
