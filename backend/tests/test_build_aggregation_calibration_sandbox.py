import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_aggregation_calibration_sandbox import (
    best_variant,
    elite_weighted_squad_strength,
    rank_score,
    squad_component,
    team_strength_variant,
    top_average,
)


def player(overall: int):
    return {
        "id": f"P{overall}",
        "name": f"Player {overall}",
        "primary_position": "CM",
        "overall": overall,
        "attributes": {},
        "stamina_max": 60,
    }


def test_rank_score_is_monotonic():
    assert rank_score(1) > rank_score(10)
    assert rank_score(None) is None


def test_top_average_uses_best_players():
    players = [player(40), player(80), player(60)]
    assert top_average(players, 2) == 70
    assert top_average([], 2) == 50


def test_elite_weighted_squad_strength_rewards_top_end():
    flat = [player(60) for _ in range(11)]
    elite = [player(90), player(85), player(80)] + [player(50) for _ in range(8)]
    assert elite_weighted_squad_strength(elite) > elite_weighted_squad_strength(flat)


def test_squad_component_rejects_unknown_method():
    assert squad_component([player(60)], "current") == 60
    try:
        squad_component([player(60)], "unknown")
    except ValueError as exc:
        assert "unknown squad method" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_team_strength_variant_blends_rank_and_squad():
    players = [player(60) for _ in range(11)]
    variant = {"rank_weight": 0.75, "squad_method": "current"}
    strength, confidence = team_strength_variant(1, players, variant)
    assert confidence == "estimated"
    assert strength > 60
    no_rank_strength, _ = team_strength_variant(None, players, variant)
    assert no_rank_strength == 60


def test_best_variant_prefers_watchlist_reduction_then_small_overall_shift():
    rows = [
        {
            "variant_id": "a",
            "comparison": {
                "evaluation": {"watchlist_implausible_reduction": 1},
                "overall": {"average_favorite_win_pct_delta": 2.0},
            },
        },
        {
            "variant_id": "b",
            "comparison": {
                "evaluation": {"watchlist_implausible_reduction": 2},
                "overall": {"average_favorite_win_pct_delta": 5.0},
            },
        },
    ]
    assert best_variant(rows)["variant_id"] == "b"
