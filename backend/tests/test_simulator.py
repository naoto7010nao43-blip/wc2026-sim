import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.actions import choose_action
from app.engine.simulator import simulate_match
from app.engine.state import build_team_state


def make_squad(team_id: str, base_overall: int) -> list[dict]:
    """Builds a minimal 11+ player squad with uniform attributes for deterministic testing."""
    positions = ["GK", "GK", "CB", "CB", "LB", "RB", "CDM", "CM", "CM", "LW", "ST", "RW"]
    squad = []
    for i, pos in enumerate(positions):
        attrs = {
            "pace": base_overall, "shooting": base_overall, "passing": base_overall,
            "dribbling": base_overall, "defending": base_overall, "physical": base_overall,
            "gk_reflexes": base_overall if pos == "GK" else None,
            "gk_handling": base_overall if pos == "GK" else None,
        }
        squad.append({
            "id": f"{team_id}_{pos}_{i}",
            "name": f"{team_id} {pos} {i}",
            "primary_position": pos,
            "secondary_positions": [],
            "overall": base_overall,
            "attributes": attrs,
            "stamina_max": 90,
        })
    return squad


def test_same_seed_produces_identical_result():
    home = make_squad("HOME", 70)
    away = make_squad("AWAY", 60)

    r1 = simulate_match("HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=123)
    r2 = simulate_match("HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=123)

    assert r1["home_score"] == r2["home_score"]
    assert r1["away_score"] == r2["away_score"]
    assert r1["events"] == r2["events"]


def test_different_seeds_can_produce_different_results():
    home = make_squad("HOME", 70)
    away = make_squad("AWAY", 60)

    results = {
        (r["home_score"], r["away_score"])
        for seed in range(10)
        for r in [simulate_match("HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=seed)]
    }
    assert len(results) > 1


def _is_goal(e: dict) -> bool:
    # A scored penalty kick is a goal too, just logged under its own event
    # type (penalty_kick) rather than "goal", so it carries shot/PK-specific
    # metadata (the taker, the keeper, scored True/False).
    if e["event_type"] == "goal":
        return True
    return e["event_type"] == "penalty_kick" and (e.get("event_metadata") or {}).get("scored") is True


def test_event_log_goal_count_matches_score():
    home = make_squad("HOME", 75)
    away = make_squad("AWAY", 55)
    result = simulate_match("HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=5)

    home_goals = sum(1 for e in result["events"] if _is_goal(e) and e["team_id"] == "HOME")
    away_goals = sum(1 for e in result["events"] if _is_goal(e) and e["team_id"] == "AWAY")

    assert home_goals == result["home_score"]
    assert away_goals == result["away_score"]
    assert result["events"][0]["event_type"] == "kickoff"
    assert result["events"][-1]["event_type"] == "fulltime"
    assert any(e["event_type"] == "halftime" for e in result["events"])


def test_penalty_kick_in_regular_play_is_reflected_in_score_and_shots():
    home = make_squad("HOME", 75)
    away = make_squad("AWAY", 55)
    found_pk = False
    for seed in range(60):
        result = simulate_match("HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=seed)
        pks = [e for e in result["events"] if e["event_type"] == "penalty_kick"]
        if not pks:
            continue
        found_pk = True
        home_goals = sum(1 for e in result["events"] if _is_goal(e) and e["team_id"] == "HOME")
        away_goals = sum(1 for e in result["events"] if _is_goal(e) and e["team_id"] == "AWAY")
        assert home_goals == result["home_score"]
        assert away_goals == result["away_score"]
        # Every PK attempt (scored or saved) must count as a shot and a
        # shot-on-target for its team.
        for pk in pks:
            shots_key = "home_shots" if pk["team_id"] == "HOME" else "away_shots"
            sot_key = "home_shots_on_target" if pk["team_id"] == "HOME" else "away_shots_on_target"
            assert result[shots_key] >= 1
            assert result[sot_key] >= 1
        break
    assert found_pk  # at least one of these seeds should produce an in-box foul


def test_stronger_team_wins_more_often_but_not_always():
    # A ~15-point overall gap (comparable to the biggest real gaps in the
    # seed data, e.g. Brazil vs USA) is enough to show dominance without
    # being so extreme that randomness can never produce an upset.
    strong = make_squad("STRONG", 70)
    weak = make_squad("WEAK", 55)

    strong_wins = 0
    weak_wins = 0
    for seed in range(40):
        r = simulate_match("STRONG", "WEAK", strong, weak, "4-3-3", "4-3-3", seed=seed)
        if r["home_score"] > r["away_score"]:
            strong_wins += 1
        elif r["home_score"] < r["away_score"]:
            weak_wins += 1

    assert strong_wins > weak_wins
    assert weak_wins > 0  # not deterministic


def test_allow_draw_false_never_returns_a_tie():
    # Knockout matches (allow_draw=False) must always resolve to a winner,
    # via extra time and then penalties if still level after 90'.
    home = make_squad("HOME", 65)
    away = make_squad("AWAY", 65)

    for seed in range(15):
        r = simulate_match("HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=seed, allow_draw=False)
        if r["went_to_penalties"]:
            assert r["home_score"] == r["away_score"]
            assert r["penalty_home_score"] != r["penalty_away_score"]
        else:
            assert r["home_score"] != r["away_score"]


def test_allow_draw_false_extends_match_when_tied_at_90():
    home = make_squad("HOME", 65)
    away = make_squad("AWAY", 65)

    found_extra_time = False
    for seed in range(15):
        r = simulate_match("HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=seed, allow_draw=False)
        if r["went_to_extra_time"]:
            found_extra_time = True
            assert any(e["event_type"] == "extra_time_start" for e in r["events"])
            assert r["events"][-1]["event_type"] in ("fulltime", "shootout_winner")
    assert found_extra_time  # at least one of these seeds should reach extra time


def test_high_press_defense_suppresses_equal_strength_opponent_scoring():
    # Same overall rating on both sides, but the away team presses very
    # aggressively (press_intensity=95) — it should concede fewer goals on
    # average than a neutral-press baseline, since presses harder makes
    # the home team's passes/dribbles fail more often.
    home = make_squad("HOME", 65)
    away = make_squad("AWAY", 65)

    baseline_home_goals = 0
    pressed_home_goals = 0
    trials = 25
    for seed in range(trials):
        r_baseline = simulate_match("HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=seed)
        baseline_home_goals += r_baseline["home_score"]

        r_pressed = simulate_match(
            "HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=seed,
            away_tactical_profile={"press_intensity": 95, "possession_style": 50, "defensive_line_height": 50},
        )
        pressed_home_goals += r_pressed["home_score"]

    assert pressed_home_goals < baseline_home_goals


def test_possession_style_shifts_action_mix_toward_passing():
    squad = make_squad("HOME", 65)
    team = build_team_state("HOME", squad, "4-3-3", attacking_direction=1)
    carrier = team.outfield()[0]

    rng_direct = random.Random(99)
    rng_possession = random.Random(99)

    direct_counts = {"PASS": 0, "LONG_BALL": 0, "DRIBBLE": 0, "SHOOT": 0}
    possession_counts = {"PASS": 0, "LONG_BALL": 0, "DRIBBLE": 0, "SHOOT": 0}
    for _ in range(500):
        direct_counts[choose_action(carrier, 50.0, 50.0, 1, rng_direct, possession_style=5)] += 1
        possession_counts[choose_action(carrier, 50.0, 50.0, 1, rng_possession, possession_style=95)] += 1

    assert possession_counts["PASS"] > direct_counts["PASS"]
    assert possession_counts["LONG_BALL"] < direct_counts["LONG_BALL"]


def test_allow_draw_true_can_end_in_a_tie_and_skips_extra_time():
    home = make_squad("HOME", 65)
    away = make_squad("AWAY", 65)

    found_tie = False
    for seed in range(15):
        r = simulate_match("HOME", "AWAY", home, away, "4-3-3", "4-3-3", seed=seed)
        assert not r["went_to_extra_time"]
        assert not r["went_to_penalties"]
        if r["home_score"] == r["away_score"]:
            found_tie = True
    assert found_tie
