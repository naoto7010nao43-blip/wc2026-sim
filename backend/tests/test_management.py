import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.management import apply_game_plan, maybe_substitute, update_score_state_tactics
from app.engine.state import NEUTRAL_SUBSTITUTION_PROFILE, build_team_state
from tests.test_simulator import make_squad


def _deep_bench_team(team_id: str, base_overall: int = 60, bench_overall: int = 70, substitution_profile=None):
    squad = make_squad(team_id, base_overall) + make_squad(team_id, bench_overall)[:5]
    for i, p in enumerate(squad):
        p["id"] = f"{p['id']}_{i}"
    team = build_team_state(team_id, squad, "4-3-3", attacking_direction=1, substitution_profile=substitution_profile)
    for i, p in enumerate(team.outfield()):
        p.current_stamina = p.stamina_max * (0.3 + 0.05 * i)
    return team


def _sub_count_over_window(team, seed: int, opponent_score: int = 0) -> int:
    rng = random.Random(seed)
    count = 0
    for minute in range(40, 89):
        if team.subs_made >= 3:
            break
        if maybe_substitute(team, minute, rng, opponent_score=opponent_score) is not None:
            count += 1
    return count


def test_apply_game_plan_favors_stronger_side():
    strong = build_team_state("STRONG", make_squad("STRONG", 75), "4-3-3", attacking_direction=1, tactical_profile={"press_intensity": 50, "possession_style": 50, "defensive_line_height": 50})
    weak = build_team_state("WEAK", make_squad("WEAK", 55), "4-3-3", attacking_direction=-1, tactical_profile={"press_intensity": 50, "possession_style": 50, "defensive_line_height": 50})

    apply_game_plan(strong, weak)

    assert strong.tactical_profile["possession_style"] > 50
    assert weak.tactical_profile["possession_style"] < 50
    assert strong.tactical_profile["defensive_line_height"] > weak.tactical_profile["defensive_line_height"]


def test_apply_game_plan_leaves_equal_sides_unchanged():
    a = build_team_state("A", make_squad("A", 65), "4-3-3", attacking_direction=1, tactical_profile={"press_intensity": 60, "possession_style": 40, "defensive_line_height": 50})
    b = build_team_state("B", make_squad("B", 65), "4-3-3", attacking_direction=-1, tactical_profile={"press_intensity": 60, "possession_style": 40, "defensive_line_height": 50})

    apply_game_plan(a, b)

    assert a.tactical_profile == {"press_intensity": 60, "possession_style": 40, "defensive_line_height": 50}
    assert b.tactical_profile == a.tactical_profile


def test_score_state_pushes_trailing_team_forward_late():
    team = build_team_state("HOME", make_squad("HOME", 65), "4-3-3", attacking_direction=1, tactical_profile={"press_intensity": 50, "possession_style": 50, "defensive_line_height": 50})
    opponent = build_team_state("AWAY", make_squad("AWAY", 65), "4-3-3", attacking_direction=-1, tactical_profile={"press_intensity": 50, "possession_style": 50, "defensive_line_height": 50})
    opponent.score = 1  # `team` is trailing

    update_score_state_tactics(team, opponent, clock=85.0, final_minute=90.0)

    assert team.tactical_profile["press_intensity"] > team.base_tactical_profile["press_intensity"]
    assert team.tactical_profile["defensive_line_height"] > team.base_tactical_profile["defensive_line_height"]


def test_score_state_makes_leading_team_conservative_late():
    team = build_team_state("HOME", make_squad("HOME", 65), "4-3-3", attacking_direction=1, tactical_profile={"press_intensity": 50, "possession_style": 50, "defensive_line_height": 50})
    opponent = build_team_state("AWAY", make_squad("AWAY", 65), "4-3-3", attacking_direction=-1, tactical_profile={"press_intensity": 50, "possession_style": 50, "defensive_line_height": 50})
    team.score = 1  # `team` is leading

    update_score_state_tactics(team, opponent, clock=85.0, final_minute=90.0)

    assert team.tactical_profile["press_intensity"] < team.base_tactical_profile["press_intensity"]
    assert team.tactical_profile["defensive_line_height"] < team.base_tactical_profile["defensive_line_height"]


def test_score_state_no_change_early_in_match():
    team = build_team_state("HOME", make_squad("HOME", 65), "4-3-3", attacking_direction=1, tactical_profile={"press_intensity": 50, "possession_style": 50, "defensive_line_height": 50})
    opponent = build_team_state("AWAY", make_squad("AWAY", 65), "4-3-3", attacking_direction=-1, tactical_profile={"press_intensity": 50, "possession_style": 50, "defensive_line_height": 50})
    team.score = 1

    update_score_state_tactics(team, opponent, clock=30.0, final_minute=90.0)

    assert team.tactical_profile == team.base_tactical_profile


def test_maybe_substitute_swaps_tired_starter_for_bench_player():
    squad = make_squad("HOME", 60)
    # Give the squad extra bench depth beyond the 11 used in the 4-3-3 formation.
    squad += make_squad("HOME", 70)[:3]
    for i, p in enumerate(squad):
        p["id"] = f"{p['id']}_{i}"
    team = build_team_state("HOME", squad, "4-3-3", attacking_direction=1)
    assert team.bench, "expected leftover squad players on the bench"

    tired = team.outfield()[0]
    tired.current_stamina = tired.stamina_max * 0.3  # well below the substitution threshold

    rng = random.Random(0)
    sub_event = None
    for _ in range(200):  # repeated rolls at a single in-window minute to overcome the per-roll chance
        sub_event = maybe_substitute(team, 60, rng)
        if sub_event is not None:
            break

    assert sub_event is not None
    assert sub_event["event_type"] == "substitution"
    assert team.subs_made == 1
    assert tired not in team.lineup


def test_maybe_substitute_respects_max_subs_and_window():
    squad = make_squad("HOME", 60) + make_squad("HOME", 70)[:5]
    for i, p in enumerate(squad):
        p["id"] = f"{p['id']}_{i}"
    team = build_team_state("HOME", squad, "4-3-3", attacking_direction=1)
    # Staggered stamina so there's always a clearly-most-tired outfield player
    # relative to the freshest one (uniform fatigue across the XI would never
    # clear the relative-gap check, which real matches never produce anyway).
    for i, p in enumerate(team.outfield()):
        p.current_stamina = p.stamina_max * (0.3 + 0.05 * i)

    rng = random.Random(1)
    # Outside the substitution window, no sub should ever be made.
    assert maybe_substitute(team, 10, rng) is None
    assert maybe_substitute(team, 89, rng) is None

    rng = random.Random(1)
    for minute in range(55, 89):
        for _ in range(20):  # several rolls per minute to overcome the per-roll chance
            if team.subs_made >= 3:
                break
            maybe_substitute(team, minute, rng)

    assert team.subs_made <= 3


def test_build_team_state_defaults_to_neutral_substitution_profile():
    team = build_team_state("HOME", make_squad("HOME", 60), "4-3-3", attacking_direction=1)
    assert team.substitution_profile == NEUTRAL_SUBSTITUTION_PROFILE


def test_build_team_state_merges_partial_substitution_profile_onto_neutral_defaults():
    team = build_team_state(
        "HOME", make_squad("HOME", 60), "4-3-3", attacking_direction=1,
        substitution_profile={"trailing_aggression": 0.8},
    )
    assert team.substitution_profile["trailing_aggression"] == 0.8
    assert team.substitution_profile["bench_trust"] == NEUTRAL_SUBSTITUTION_PROFILE["bench_trust"]
    assert team.substitution_profile["like_for_like_preference"] == NEUTRAL_SUBSTITUTION_PROFILE["like_for_like_preference"]


def test_neutral_profile_substitution_count_is_unaffected_by_score_state():
    """A neutral profile must behave identically whether trailing, level,
    or leading -- only a non-neutral trailing_aggression/leading_defensive_bias
    should change substitution likelihood by score state."""
    level_team = _deep_bench_team("HOME", substitution_profile=None)
    trailing_team = _deep_bench_team("HOME", substitution_profile=None)
    leading_team = _deep_bench_team("HOME", substitution_profile=None)

    level_count = _sub_count_over_window(level_team, seed=7, opponent_score=0)
    trailing_count = _sub_count_over_window(trailing_team, seed=7, opponent_score=5)
    leading_team.score = 5
    leading_count = _sub_count_over_window(leading_team, seed=7, opponent_score=0)

    assert level_count == trailing_count == leading_count


def test_trailing_aggression_increases_substitution_likelihood_when_trailing():
    profile = {**NEUTRAL_SUBSTITUTION_PROFILE, "trailing_aggression": 1.0}

    counts = []
    for seed in range(30):
        team = _deep_bench_team("HOME", substitution_profile=dict(profile))
        counts.append(_sub_count_over_window(team, seed=seed, opponent_score=3))  # team is trailing 0-3
    aggressive_total = sum(counts)

    neutral_counts = []
    for seed in range(30):
        team = _deep_bench_team("HOME", substitution_profile=None)
        neutral_counts.append(_sub_count_over_window(team, seed=seed, opponent_score=3))
    neutral_total = sum(neutral_counts)

    assert aggressive_total > neutral_total


def test_leading_defensive_bias_increases_substitution_likelihood_when_leading():
    profile = {**NEUTRAL_SUBSTITUTION_PROFILE, "leading_defensive_bias": 1.0}

    biased_total = 0
    neutral_total = 0
    for seed in range(30):
        biased_team = _deep_bench_team("HOME", substitution_profile=dict(profile))
        biased_team.score = 2  # team is leading 2-0
        biased_total += _sub_count_over_window(biased_team, seed=seed, opponent_score=0)

        neutral_team = _deep_bench_team("HOME", substitution_profile=None)
        neutral_team.score = 2
        neutral_total += _sub_count_over_window(neutral_team, seed=seed, opponent_score=0)

    assert biased_total > neutral_total


def test_first_sub_minute_bias_shifts_window_start_but_respects_floor():
    early_team = _deep_bench_team("HOME", substitution_profile={"first_sub_minute_bias": -20.0})
    rng = random.Random(3)
    # The window start would go below 40 without the floor; minute 40 should
    # now be eligible (it never was at the original window start of 55).
    saw_sub_before_55 = False
    for minute in range(35, 55):
        if maybe_substitute(early_team, minute, rng) is not None:
            saw_sub_before_55 = True
            break
    assert saw_sub_before_55

    # The window can never start before minute 40 regardless of how large
    # the negative bias is.
    floored_team = _deep_bench_team("HOME", substitution_profile={"first_sub_minute_bias": -9999.0})
    rng = random.Random(3)
    assert maybe_substitute(floored_team, 39, rng) is None


def test_max_subs_and_window_invariants_hold_with_non_neutral_profile():
    profile = {
        "first_sub_minute_bias": -10.0,
        "trailing_aggression": 1.0,
        "leading_defensive_bias": 1.0,
        "bench_trust": 1.0,
        "like_for_like_preference": 0.0,
        "late_penalty_prep_bias": 0.0,
    }
    team = _deep_bench_team("HOME", substitution_profile=profile)
    team.score = 0
    rng = random.Random(11)

    assert maybe_substitute(team, 5, rng, opponent_score=2) is None  # still before any plausible window
    assert maybe_substitute(team, 89, rng, opponent_score=2) is None  # still after SUB_WINDOW[1]

    for minute in range(40, 89):
        for _ in range(20):
            if team.subs_made >= 3:
                break
            maybe_substitute(team, minute, rng, opponent_score=2)

    assert team.subs_made <= 3


def test_like_for_like_preference_zero_can_pick_non_positional_bench_player():
    squad = make_squad("HOME", 60)
    bench_extra = make_squad("HOME", 90)[:2]
    for i, p in enumerate(bench_extra):
        p["id"] = f"BENCH_{i}"
        p["primary_position"] = "ST"  # deliberately not a positional match for most slots
    full_squad = squad + bench_extra
    team = build_team_state(
        "HOME", full_squad, "4-3-3", attacking_direction=1,
        substitution_profile={"like_for_like_preference": 0.0},
    )
    keeper = team.goalkeeper()
    keeper.current_stamina = keeper.stamina_max * 0.1

    other_outfield = [p for p in team.outfield()]
    for p in other_outfield:
        p.current_stamina = p.stamina_max

    tired_defender = min(team.outfield(), key=lambda p: p.stamina_factor())
    tired_defender.current_stamina = tired_defender.stamina_max * 0.2

    rng = random.Random(5)
    sub_event = None
    for _ in range(200):
        sub_event = maybe_substitute(team, 60, rng)
        if sub_event is not None:
            break

    assert sub_event is not None
    sub_in = next(p for p in team.lineup if p.player_id == sub_event["player_id"])
    # With like_for_like_preference=0.0 the high-overall ST bench players are
    # eligible even though the tired player was not an ST.
    assert sub_in.primary_position == "ST"
