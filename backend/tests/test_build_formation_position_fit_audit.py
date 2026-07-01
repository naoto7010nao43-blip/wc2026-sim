import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_formation_position_fit_audit import (  # noqa: E402
    audit_team,
    position_fits_slot,
    recommended_action,
    severity_band,
)


def player(pid, pos, prob=80, secondary=None, overall=70):
    return {
        "id": pid,
        "name": pid,
        "primary_position": pos,
        "secondary_positions": secondary or [],
        "overall": overall,
        "attributes": {"startingProbability": prob},
        "stamina_max": 90,
    }


def test_position_fit_accepts_primary_or_secondary_slot():
    assert position_fits_slot(player("A", "RW"), "RW") is True
    assert position_fits_slot(player("B", "RW", secondary=["RM"]), "RM") is True
    assert position_fits_slot(player("C", "RW"), "CM") is False


def test_severity_band_thresholds():
    assert severity_band(12) == "high"
    assert severity_band(5) == "medium"
    assert severity_band(4) == "low"


def test_recommended_action_prioritizes_multi_slot_formation_review():
    assert recommended_action(out_of_position_count=3, low_probability_count=0) == "formation_or_roster_review"
    assert recommended_action(out_of_position_count=1, low_probability_count=0) == "monitor_position_flex"
    assert recommended_action(out_of_position_count=0, low_probability_count=1) == "roster_depth_review"
    assert recommended_action(out_of_position_count=0, low_probability_count=0) == "no_action"


def test_audit_team_flags_formation_that_forces_wingers_into_flat_midfield():
    roster = [
        player("GK", "GK"),
        player("CB1", "CB"),
        player("CB2", "CB"),
        player("LB", "LB"),
        player("RB", "RB"),
        player("LW", "LW", prob=90),
        player("RW", "RW", prob=88),
        player("CDM", "CDM", prob=86),
        player("CAM", "CAM", prob=84),
        player("ST1", "ST"),
        player("ST2", "ST"),
    ]
    row = audit_team({"teamId": "TST", "name": "Test", "defaultFormation": "4-4-2"}, roster)

    assert row["starterCount"] == 11
    assert row["outOfPositionCount"] >= 3
    assert row["severityBand"] == "high"
    assert row["recommendedAction"] == "formation_or_roster_review"


def test_audit_team_flags_low_probability_starter_when_roster_is_thin():
    roster = [
        player("GK", "GK"),
        player("CB1", "CB"),
        player("CB2", "CB"),
        player("LB", "LB"),
        player("RB", "RB"),
        player("CDM1", "CDM"),
        player("CM2", "CM"),
        player("CM3", "CM"),
        player("LW", "LW"),
        player("RW", "RW"),
        player("ST_LOW", "ST", prob=25),
    ]
    row = audit_team({"teamId": "TST", "name": "Test", "defaultFormation": "4-3-3"}, roster)

    assert row["outOfPositionCount"] == 0
    assert row["lowProbabilityStarterCount"] == 1
    assert row["recommendedAction"] == "roster_depth_review"
