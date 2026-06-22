"""Pitch coordinate helpers. x: 0 (own goal) - 100 (opponent goal). y: 0-100 (touchline to touchline)."""

import math

ZONES = ["DEF_THIRD", "MID_THIRD", "ATT_THIRD"]


def zone_for_x(x: float) -> str:
    if x < 33.3:
        return "DEF_THIRD"
    if x < 66.6:
        return "MID_THIRD"
    return "ATT_THIRD"


def distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def distance_to_goal(pos: tuple[float, float]) -> float:
    """Distance from pos to the attacking goal at (100, 50)."""
    return distance(pos, (100.0, 50.0))


def target_goal(attacking_direction: int) -> tuple[float, float]:
    return (100.0, 50.0) if attacking_direction == 1 else (0.0, 50.0)


def distance_to_target_goal(pos: tuple[float, float], attacking_direction: int) -> float:
    return distance(pos, target_goal(attacking_direction))


def attacking_progress(x: float, attacking_direction: int) -> float:
    """Normalize x so 0 = own goal, 100 = opponent goal, regardless of attacking_direction."""
    return x if attacking_direction == 1 else 100.0 - x


def zone_for_progress(progress: float) -> str:
    return zone_for_x(progress)


def is_in_penalty_box(x: float, y: float, attacking_direction: int) -> bool:
    """Proportional approximation of an 18-yard box (16.5m deep of a ~105m
    pitch, 40.3m wide of 68m, centered) in the 0-100 coordinate system."""
    progress = attacking_progress(x, attacking_direction)
    return progress >= 84.0 and 21.0 <= y <= 79.0


def clamp_coord(value: float) -> float:
    return max(0.0, min(100.0, value))
