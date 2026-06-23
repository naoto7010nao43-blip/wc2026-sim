import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_matchup_driver_audit import (
    contribution_breakdown,
    driver_summary,
    primary_negative_driver,
    select_watchlist_rows,
)


def test_contribution_breakdown_uses_model_weights():
    features = SimpleNamespace(
        attack_diff=10.0,
        defense_diff=-5.0,
        strength_diff=2.0,
        tactical_modifier=-0.5,
    )
    contributions = contribution_breakdown(features)
    assert contributions["attack"] == 0.22
    assert contributions["defense"] == -0.11
    assert contributions["strength"] == 0.024
    assert contributions["tactical"] == -0.05
    assert contributions["home_order"] == 0.05


def test_primary_negative_driver_returns_largest_drag():
    contributions = {"attack": 0.1, "defense": -0.2, "strength": -0.05, "tactical": 0.0, "home_order": 0.05}
    assert primary_negative_driver(contributions) == "defense"
    assert primary_negative_driver({"attack": 0.1, "home_order": 0.05}) == "none"


def test_driver_summary_averages_contributions_and_counts_drivers():
    rows = [
        {
            "log_goal_contributions": {
                "attack": 0.1,
                "defense": -0.2,
                "strength": 0.0,
                "tactical": -0.1,
                "home_order": 0.05,
            },
            "primary_negative_driver": "defense",
        },
        {
            "log_goal_contributions": {
                "attack": 0.3,
                "defense": -0.1,
                "strength": -0.2,
                "tactical": 0.0,
                "home_order": 0.05,
            },
            "primary_negative_driver": "strength",
        },
    ]
    summary = driver_summary(rows)
    assert summary["matchup_count"] == 2
    assert summary["average_contributions"]["attack"] == 0.2
    assert summary["average_contributions"]["home_order"] == 0.05
    assert summary["primary_negative_driver_counts"] == {"defense": 1, "strength": 1}


def test_driver_summary_handles_empty_rows():
    summary = driver_summary([])
    assert summary["matchup_count"] == 0
    assert summary["average_contributions"]["attack"] is None
    assert summary["primary_negative_driver_counts"] == {}


def test_select_watchlist_rows_prefers_implausible_lowest_win_rows():
    rows = [
        {"favorite_team_id": "CRO", "favorite_win_pct": 45.0, "implausible_favorite": False},
        {"favorite_team_id": "CRO", "favorite_win_pct": 30.0, "implausible_favorite": True},
        {"favorite_team_id": "CRO", "favorite_win_pct": 35.0, "implausible_favorite": True},
        {"favorite_team_id": "NED", "favorite_win_pct": 20.0, "implausible_favorite": True},
    ]
    selected = select_watchlist_rows(rows, "CRO", limit=1)
    assert selected == [{"favorite_team_id": "CRO", "favorite_win_pct": 30.0, "implausible_favorite": True}]


def test_select_watchlist_rows_falls_back_when_no_implausible_rows():
    rows = [
        {"favorite_team_id": "CRO", "favorite_win_pct": 45.0, "implausible_favorite": False},
        {"favorite_team_id": "CRO", "favorite_win_pct": 40.0, "implausible_favorite": False},
    ]
    selected = select_watchlist_rows(rows, "CRO", limit=1)
    assert selected[0]["favorite_win_pct"] == 40.0
