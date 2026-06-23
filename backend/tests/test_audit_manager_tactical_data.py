import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_manager_tactical_data import (
    build_report,
    build_team_row,
    compute_review_score,
    duplicate_profile_lookup,
    normalize_name,
    priority_band,
)


def test_normalize_name_case_and_spacing():
    assert normalize_name("  Carlo   Ancelotti. ") == "carlo ancelotti"


def test_duplicate_profile_lookup_flags_shared_tactical_values():
    teams = [
        {"id": "AAA", "tactical_profile": {"press_intensity": 60, "possession_style": 50, "defensive_line_height": 40}},
        {"id": "BBB", "tactical_profile": {"press_intensity": 60, "possession_style": 50, "defensive_line_height": 40}},
        {"id": "CCC", "tactical_profile": {"press_intensity": 70, "possession_style": 50, "defensive_line_height": 40}},
    ]
    lookup = duplicate_profile_lookup(teams)
    assert lookup["AAA"] == ["AAA", "BBB"]
    assert lookup["BBB"] == ["AAA", "BBB"]
    assert "CCC" not in lookup


def test_review_score_prioritizes_name_mismatch_and_top_team_without_basis():
    score = compute_review_score(
        manager_name_mismatch=True,
        missing_manager_rating=False,
        missing_tactical_basis=True,
        duplicate_profile_team_count=2,
        top_twenty_fifa_rank=True,
        team_review_band="high",
    )
    assert score == 59.0
    assert priority_band(score) == "high"


def test_build_team_row_compares_seed_and_official_manager_names():
    team = {
        "id": "AAA",
        "name": "Alpha",
        "fifa_rank": 5,
        "default_formation": "4-3-3",
        "tactical_profile": {
            "manager_name": "Seed Coach",
            "press_intensity": 60,
            "possession_style": 50,
            "defensive_line_height": 40,
        },
    }
    row = build_team_row(
        team=team,
        official_team={"teamId": "AAA", "tacticalProfile": {"manager_name": "Official Coach"}},
        official_manager={"teamCode": "AAA", "name": "Official Coach"},
        manager_rating={"teamCode": "AAA", "dataConfidence": "estimated"},
        duplicate_profiles={"AAA": ["AAA", "BBB"]},
        team_review_rows={"AAA": {"priority_band": "medium"}},
    )
    assert row["manager_name_mismatch"] is True
    assert row["manager_rating_confidence"] == "estimated"
    assert row["has_tactical_basis"] is False
    assert row["review_band"] == "high"
    assert "監督名" in row["review_reasons"][0]


def test_build_report_sorts_by_review_score_and_counts_bands():
    teams = [
        {
            "id": "LOW",
            "name": "Low",
            "fifa_rank": 80,
            "default_formation": "4-4-2",
            "_tactical_profile_basis": "manual note",
            "tactical_profile": {
                "manager_name": "Same Coach",
                "press_intensity": 40,
                "possession_style": 40,
                "defensive_line_height": 40,
            },
        },
        {
            "id": "HIGH",
            "name": "High",
            "fifa_rank": 3,
            "default_formation": "4-3-3",
            "tactical_profile": {
                "manager_name": "Seed Coach",
                "press_intensity": 60,
                "possession_style": 60,
                "defensive_line_height": 60,
            },
        },
    ]
    official_teams = [
        {"teamId": "LOW", "tacticalProfile": {"manager_name": "Same Coach"}},
        {"teamId": "HIGH", "tacticalProfile": {"manager_name": "Official Coach"}},
    ]
    official_managers = [
        {"teamCode": "LOW", "name": "Same Coach"},
        {"teamCode": "HIGH", "name": "Official Coach"},
    ]
    manager_ratings = [
        {"teamCode": "LOW", "dataConfidence": "estimated"},
        {"teamCode": "HIGH", "dataConfidence": "estimated"},
    ]
    report = build_report(
        teams=teams,
        official_teams=official_teams,
        official_managers=official_managers,
        manager_ratings=manager_ratings,
        team_review_report={"generatedAt": "now", "teams": [{"team_id": "HIGH", "priority_band": "high"}]},
    )
    assert [row["team_id"] for row in report["teams"]] == ["HIGH", "LOW"]
    assert report["bandCounts"]["high"] == 1
    assert report["bandCounts"]["low"] == 1
    assert report["teamCount"] == 2
