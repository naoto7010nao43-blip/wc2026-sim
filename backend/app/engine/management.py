"""In-match manager decisions: a pre-match game plan based on the strength
gap between the two sides, in-match tactical shifts based on score state
and time remaining, and substitutions for tired/depleted starters.

These exist so a simulation's outcome reflects how real managers actually
behave (a clear underdog sits deeper and concedes possession; a team
protecting a late lead gets more conservative; a team chasing the game
pushes players forward) rather than two sides playing a fixed, opponent-
blind tactic for the full 90 minutes.
"""

import random

from app.engine.events import make_event
from app.engine.formations import SLOT_POSITION_ALIASES
from app.engine.state import PlayerState, TeamState

MAX_SUBS = 3
# How far below the squad's freshest outfield player the most-fatigued one
# must be before a substitution is even considered. A relative gap (rather
# than an absolute stamina_factor threshold) is used because this engine's
# decay rates are deliberately mild — an absolute cutoff calibrated once
# tends to silently stop firing if decay constants or halftime recovery
# change later.
SUB_FATIGUE_GAP = 0.02
SUB_WINDOW = (55, 88)
SUB_CHANCE_PER_MINUTE = 0.10


def _clamp_pct(value: float) -> float:
    return max(5.0, min(95.0, value))


def _avg_overall(team: TeamState) -> float:
    outfield = team.outfield()
    return sum(p.overall for p in outfield) / len(outfield) if outfield else 50.0


def apply_game_plan(home: TeamState, away: TeamState) -> None:
    """One-time pre-match adjustment: the weaker side plays more
    conservatively (lower press/possession/line height), the stronger side
    leans further into its natural tactical identity. Mutates each team's
    tactical_profile and re-baselines base_tactical_profile so later
    score-state shifts apply on top of the game-plan, not the raw researched
    values."""
    gap = _avg_overall(home) - _avg_overall(away)
    for team, signed_gap in ((home, gap), (away, -gap)):
        delta = max(-15.0, min(15.0, signed_gap * 1.1))
        profile = dict(team.tactical_profile)
        profile["press_intensity"] = _clamp_pct(profile.get("press_intensity", 50.0) + delta * 0.6)
        profile["possession_style"] = _clamp_pct(profile.get("possession_style", 50.0) + delta * 0.7)
        profile["defensive_line_height"] = _clamp_pct(profile.get("defensive_line_height", 50.0) + delta * 0.6)
        team.tactical_profile = profile
        team.base_tactical_profile = dict(profile)


def update_score_state_tactics(team: TeamState, opponent: TeamState, clock: float, final_minute: float) -> None:
    """Per-minute-tick adjustment on top of the game-plan baseline: protect
    a late lead by getting more conservative, chase a late deficit by
    pushing players forward."""
    time_left = max(0.0, final_minute - clock)
    window = 25.0
    if time_left >= window:
        urgency = 0.0
    else:
        urgency = (window - time_left) / window

    diff = team.score - opponent.score
    if diff > 0:
        delta = -15.0 * urgency
    elif diff < 0:
        delta = 15.0 * urgency
    else:
        delta = 0.0

    base = team.base_tactical_profile
    profile = dict(team.tactical_profile)
    profile["press_intensity"] = _clamp_pct(base.get("press_intensity", 50.0) + delta * 0.6)
    profile["possession_style"] = _clamp_pct(base.get("possession_style", 50.0) + delta * 0.5)
    profile["defensive_line_height"] = _clamp_pct(base.get("defensive_line_height", 50.0) + delta * 0.7)
    team.tactical_profile = profile


def _build_sub_player(p: dict, out_player: PlayerState) -> PlayerState:
    return PlayerState(
        player_id=p["id"],
        name=p["name"],
        name_ja=p.get("name_ja"),
        slot_position=out_player.slot_position,
        primary_position=p["primary_position"],
        attributes=p["attributes"],
        overall=p["overall"],
        stamina_max=p["stamina_max"],
        current_stamina=float(p["stamina_max"]),
        home_x=out_player.home_x,
        home_y=out_player.home_y,
        x=out_player.x,
        y=out_player.y,
    )


def _effective_sub_window(profile: dict) -> tuple[int, int]:
    """Shift the substitution window's start by the profile's
    first_sub_minute_bias (minutes earlier(-)/later(+)), clamped so the
    window can never invert or start implausibly early. A neutral (0.0)
    bias reproduces SUB_WINDOW exactly."""
    bias = profile.get("first_sub_minute_bias", 0.0)
    start = SUB_WINDOW[0] + bias
    start = max(40, min(SUB_WINDOW[1], start))
    return (int(round(start)), SUB_WINDOW[1])


def _effective_sub_chance(team: TeamState, opponent_score: int, profile: dict) -> float:
    """Neutral profile values reproduce SUB_CHANCE_PER_MINUTE exactly
    (bench_trust=0.5 -> *1.0 multiplier; trailing_aggression/
    leading_defensive_bias=0.0 -> no score-state add-on)."""
    bench_trust = profile.get("bench_trust", 0.5)
    chance = SUB_CHANCE_PER_MINUTE * (0.5 + bench_trust)

    score_diff = team.score - opponent_score
    if score_diff < 0:
        chance *= 1.0 + profile.get("trailing_aggression", 0.0)
    elif score_diff > 0:
        chance *= 1.0 + profile.get("leading_defensive_bias", 0.0) * 0.5

    return max(0.0, min(0.9, chance))


def maybe_substitute(team: TeamState, minute: int, rng: random.Random, opponent_score: int = 0) -> dict | None:
    """With small per-minute odds inside the substitution window, swap the
    most fatigued eligible starter for the best matching bench player.
    Returns a substitution event dict, or None if no sub was made.

    `team.substitution_profile` (estimated/external metadata, never
    'official') can nudge the window, the per-minute chance, and the bench
    selection's positional strictness; the default NEUTRAL_SUBSTITUTION_PROFILE
    reproduces the original fatigue-only, fixed-window behavior exactly."""
    profile = team.substitution_profile
    if team.subs_made >= MAX_SUBS or not team.bench:
        return None
    window = _effective_sub_window(profile)
    if not (window[0] <= minute <= window[1]):
        return None
    if rng.random() > _effective_sub_chance(team, opponent_score, profile):
        return None

    outfield = team.outfield()
    if not outfield:
        return None
    tired = min(outfield, key=lambda p: p.stamina_factor())
    freshest_factor = max(p.stamina_factor() for p in outfield)
    if tired.stamina_factor() > freshest_factor - SUB_FATIGUE_GAP:
        return None

    aliases = SLOT_POSITION_ALIASES.get(tired.slot_position, [tired.slot_position])
    like_for_like_preference = profile.get("like_for_like_preference", 1.0)
    position_candidates = [
        p for p in team.bench
        if p["primary_position"] == tired.slot_position or p["primary_position"] in aliases
    ]
    non_gk_candidates = [p for p in team.bench if p["primary_position"] != "GK"]
    # The neutral default (1.0) never rolls -- this keeps the original
    # behavior's RNG consumption identical when no profile is customized.
    prefers_position_match = (
        like_for_like_preference >= 1.0 or rng.random() < like_for_like_preference
    )
    if position_candidates and prefers_position_match:
        candidates = position_candidates
    else:
        candidates = non_gk_candidates or position_candidates
    if not candidates:
        return None

    replacement_raw = max(candidates, key=lambda p: p["overall"])
    team.bench.remove(replacement_raw)
    replacement = _build_sub_player(replacement_raw, tired)

    idx = team.lineup.index(tired)
    team.lineup[idx] = replacement
    team.subs_made += 1

    return make_event(
        minute, "substitution", team.team_id,
        f"選手交代: {tired.display_name} に代わって {replacement.display_name} が入る。",
        player_id=replacement.player_id, secondary_player_id=tired.player_id,
        x=tired.home_x, y=tired.home_y,
    )
