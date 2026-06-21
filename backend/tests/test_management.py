import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.management import apply_game_plan, maybe_substitute, update_score_state_tactics
from app.engine.state import build_team_state
from tests.test_simulator import make_squad


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
