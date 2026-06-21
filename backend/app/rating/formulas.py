"""Composite player rating pipeline.

This module derives the 6 core attributes (pace, shooting, passing,
dribbling, defending, physical) for each player from public statistical
inputs, NOT from any commercial video game's proprietary rating database.

Stage A - statistical base score (0-99) per attribute, from per-90 stats
           normalized as a percentile within the player's position group.
Stage B - market value percentile within the position group, applied as a
           bounded +/-4 point correction (captures market consensus signals
           like big-game pedigree or injury risk that raw stats miss).
Stage C - a small human-curated qualitative adjustment (+/-3 per attribute),
           the only place general "how good is this player perceived to be"
           judgment enters, and only as a bounded nudge on top of A+B.

See RATING_METHODOLOGY.md for the full rationale and the explicit
non-derivation-from-EA-FC disclaimer.
"""

from dataclasses import dataclass

POSITION_GROUPS: dict[str, str] = {
    "GK": "GK",
    "CB": "DEF", "LB": "DEF", "RB": "DEF",
    "CDM": "MID", "CM": "MID", "CAM": "MID", "LM": "MID", "RM": "MID",
    "LW": "FWD", "RW": "FWD", "ST": "FWD",
}

# Position-specific weights for the headline "overall" number.
OVERALL_WEIGHTS: dict[str, dict[str, float]] = {
    "GK":  {"pace": 0.05, "shooting": 0.0, "passing": 0.15, "dribbling": 0.05, "defending": 0.25, "physical": 0.20, "gk": 0.30},
    "DEF": {"pace": 0.15, "shooting": 0.0, "passing": 0.15, "dribbling": 0.05, "defending": 0.40, "physical": 0.25},
    "MID": {"pace": 0.15, "shooting": 0.15, "passing": 0.30, "dribbling": 0.20, "defending": 0.15, "physical": 0.05},
    "FWD": {"pace": 0.20, "shooting": 0.35, "passing": 0.10, "dribbling": 0.20, "defending": 0.0, "physical": 0.15},
}

CORE_ATTRS = ["pace", "shooting", "passing", "dribbling", "defending", "physical"]


def clamp(value: float, lo: float = 0, hi: float = 99) -> int:
    return int(round(max(lo, min(hi, value))))


def percentile_rank(value: float, population: list[float]) -> float:
    """Return value's percentile (0-1) within population. Population includes value."""
    if not population:
        return 0.5
    sorted_pop = sorted(population)
    n = len(sorted_pop)
    if n == 1:
        return 0.5
    # count of values strictly below + half of equal values, normalized
    below = sum(1 for v in sorted_pop if v < value)
    equal = sum(1 for v in sorted_pop if v == value)
    rank = (below + 0.5 * equal) / n
    return rank


@dataclass
class StageAInputs:
    position_group: str
    age: int
    goals_per90: float
    assists_per90: float
    key_passes_per90: float
    successful_dribbles_per90: float
    tackles_per90: float
    interceptions_per90: float
    aerial_duels_won_pct: float
    pass_completion_pct: float
    minutes_per_appearance: float
    save_pct: float | None = None
    goals_conceded_per90: float | None = None


def stage_a_raw_attributes(inp: StageAInputs) -> dict[str, float]:
    """Heuristic per-attribute base formulas (0-99 scale, pre-percentile-shaping).

    These are intentionally simple, transparent formulas over public per-90
    stats. They are deliberately NOT calibrated to match any specific game's
    published ratings.
    """
    age_factor = 1.0 if inp.age <= 29 else max(0.75, 1.0 - 0.025 * (inp.age - 29))

    pace = 50 + 18 * min(inp.successful_dribbles_per90 / 2.5, 1.5) * age_factor
    shooting = 40 + 30 * min(inp.goals_per90 / 0.6, 1.4)
    passing = 35 + 10 * min(inp.assists_per90 / 0.4, 1.5) + 12 * min(inp.key_passes_per90 / 2.5, 1.5) + 0.2 * (inp.pass_completion_pct - 75)
    dribbling = 40 + 22 * min(inp.successful_dribbles_per90 / 2.5, 1.6) * age_factor
    defending = 35 + 18 * min(inp.tackles_per90 / 2.5, 1.5) + 14 * min(inp.interceptions_per90 / 2.0, 1.5) + 0.15 * (inp.aerial_duels_won_pct - 40)
    physical = 45 + 0.25 * (inp.aerial_duels_won_pct - 40) + 10 * min(inp.minutes_per_appearance / 80, 1.2)

    raw = {
        "pace": pace,
        "shooting": shooting,
        "passing": passing,
        "dribbling": dribbling,
        "defending": defending,
        "physical": physical,
    }
    return {k: max(20.0, min(95.0, v)) for k, v in raw.items()}


def stage_a_gk_attributes(inp: StageAInputs) -> dict[str, float]:
    save_pct = inp.save_pct if inp.save_pct is not None else 70.0
    goals_conceded = inp.goals_conceded_per90 if inp.goals_conceded_per90 is not None else 1.2
    gk_reflexes = 40 + 0.6 * (save_pct - 60) + 8 * max(0, 1.3 - goals_conceded)
    gk_handling = 45 + 0.5 * (save_pct - 60) + 0.15 * (inp.aerial_duels_won_pct - 30)
    return {
        "gk_reflexes": max(30.0, min(95.0, gk_reflexes)),
        "gk_handling": max(30.0, min(95.0, gk_handling)),
    }


def stage_b_market_modifier(market_value_percentile: float, age: int = 27) -> float:
    """Map a 0-1 percentile within the position group to a +/-10 point shift.

    Market value is the strongest public signal of true ability gaps that
    raw per-90 stats miss entirely: per-90 stats are not adjusted for the
    strength of a player's league/opposition, so a domestic-league regular
    in a weaker footballing nation can post numbers similar to an elite
    player without the same actual quality. Market value already prices in
    league strength, so widening this band (vs. the original +/-4) is the
    most direct fix for unrealistic upsets without re-deriving ratings from
    any game's database.

    The downside is damped for players 32+: transfer/resale value collapses
    much faster with age than actual on-pitch ability does, especially for
    a veteran who took a lower-revenue-league move (MLS, Saudi Pro League,
    etc.) -- applying the full penalty there would punish retained quality
    as if per-90 stats had also shown a steep decline, which they often
    haven't. The upside (a high market value boosting a young/peak player)
    is left untouched since that direction isn't subject to the same bias.
    """
    raw = (market_value_percentile - 0.5) * 20.0
    if raw < 0 and age >= 32:
        damp = max(0.4, 1.0 - 0.05 * (age - 32))
        raw *= damp
    return raw


def apply_pipeline(
    stage_a: dict[str, float],
    market_value_percentile: float,
    qualitative_adjustments: dict[str, int],
    age: int = 27,
) -> dict[str, int]:
    """Combine Stage A + B (uniform market modifier across attrs) + C (per-attr human nudge)."""
    b_mod = stage_b_market_modifier(market_value_percentile, age)
    final: dict[str, int] = {}
    for attr, raw_value in stage_a.items():
        c_adj = qualitative_adjustments.get(attr, 0)
        c_adj = max(-6, min(6, c_adj))
        final[attr] = clamp(raw_value + b_mod + c_adj)
    return final


def compute_overall(attributes: dict[str, int], position: str) -> int:
    group = POSITION_GROUPS.get(position, "MID")
    weights = OVERALL_WEIGHTS[group]
    total = 0.0
    for attr in CORE_ATTRS:
        total += weights.get(attr, 0.0) * attributes.get(attr, 50)
    if group == "GK":
        gk_avg = (attributes.get("gk_reflexes", 50) + attributes.get("gk_handling", 50)) / 2
        total += weights.get("gk", 0.0) * gk_avg
    return clamp(total)
