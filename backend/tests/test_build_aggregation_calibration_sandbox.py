import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_aggregation_calibration_sandbox as sandbox

from build_aggregation_calibration_sandbox import (
    best_variant,
    build_variant_matchup_row,
    elite_weighted_squad_strength,
    rank_score,
    squad_component,
    team_strength_variant,
    top_average,
)
from build_prediction_benchmark_baseline import BENCHMARK_ORDERING_METHOD


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


def test_build_variant_matchup_row_uses_dual_order_average(monkeypatch):
    def fake_lambdas_from_ratings(home_attack, *args):
        if home_attack == 70:
            return 2.0, 1.0
        return 1.1, 1.8

    def fake_matchup_probabilities(lambda_home, lambda_away):
        if (lambda_home, lambda_away) == (2.0, 1.0):
            return 60.0, 20.0, 20.0, [{"home_goals": 2, "away_goals": 1, "probability_pct": 12.3}]
        return 30.0, 25.0, 45.0, [{"home_goals": 1, "away_goals": 2, "probability_pct": 10.0}]

    monkeypatch.setattr(sandbox, "lambdas_from_ratings", fake_lambdas_from_ratings)
    monkeypatch.setattr(sandbox, "matchup_probabilities", fake_matchup_probabilities)

    row = build_variant_matchup_row(
        {"id": "FAV", "fifa_rank": 1},
        {"id": "DOG", "fifa_rank": 11},
        {
            "FAV": {"attack": 70, "defense": 60, "strength": 80, "data_confidence": "estimated"},
            "DOG": {"attack": 50, "defense": 55, "strength": 60, "data_confidence": "estimated"},
        },
    )

    assert row["benchmark_ordering_method"] == BENCHMARK_ORDERING_METHOD
    assert row["favorite_win_pct"] == 52.5
    assert row["home_win_pct"] == 52.5
    assert row["away_win_pct"] == 25.0
    assert row["draw_pct"] == 22.5
    assert row["favorite_home_win_pct"] == 60.0
    assert row["favorite_away_win_pct"] == 45.0
    assert row["home_expected_goals"] == 1.9
    assert row["away_expected_goals"] == 1.05
