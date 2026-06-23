import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_team_rating_component_audit import (
    build_team_row,
    component_flags,
    position_counts,
    rank_score,
    top_n_average,
)


def player(**overrides):
    row = {
        "id": "P1",
        "name": "One",
        "primary_position": "CM",
        "overall": 60,
        "attributes": {
            "finishing": 55,
            "shotPower": 55,
            "chanceCreation": 55,
            "ballCarrying": 55,
            "crossing": 55,
            "setPiece": 55,
            "tackling": 55,
            "interception": 55,
            "aerialDefense": 55,
            "strength": 55,
            "goalkeeperReflexes": 55,
            "goalkeeperHandling": 55,
            "goalkeeperDistribution": 55,
        },
        "stamina_max": 60,
    }
    row.update(overrides)
    return row


def test_rank_score_is_monotonic_for_better_rank():
    assert rank_score(1) > rank_score(10)
    assert rank_score(None) is None


def test_top_n_average_uses_best_players_only():
    players = [player(id="P1", overall=40), player(id="P2", overall=80), player(id="P3", overall=70)]
    assert top_n_average(players, 2) == 75.0
    assert top_n_average([], 2) is None


def test_position_counts_groups_positions():
    counts = position_counts([
        player(primary_position="GK"),
        player(primary_position="CB"),
        player(primary_position="CDM"),
        player(primary_position="ST"),
    ])
    assert counts == {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1}


def test_component_flags_detects_rank_squad_gap_and_thin_depth():
    row = {
        "fifa_rank": 8,
        "rank_score": 80,
        "squad_strength": 55,
        "top_11_avg_overall": 54,
        "count_overall_gte_70": 1,
        "position_counts": {"GK": 1, "DEF": 3, "MID": 5, "FWD": 2},
        "attack": 49,
        "defense": 48,
    }
    flags = set(component_flags(row))
    assert "rank_signal_far_above_squad_strength" in flags
    assert "best_xi_overall_low_for_top_ranked_team" in flags
    assert "few_elite_seed_players_for_top_15_team" in flags
    assert "thin_defensive_seed_depth" in flags
    assert "thin_attacking_seed_depth" in flags


def test_build_team_row_has_stable_shape_and_flags():
    team = {"id": "AAA", "name": "Alpha", "fifa_rank": 5}
    players = [player(id=f"P{i}", overall=55 + i, primary_position="CM") for i in range(11)]
    row = build_team_row(team, players, watchlist=True)
    assert row["team_id"] == "AAA"
    assert row["watchlist"] is True
    assert row["player_count"] == 11
    assert row["rank_score"] is not None
    assert row["top_players"][0]["overall"] == 65
    assert isinstance(row["diagnostic_flags"], list)
