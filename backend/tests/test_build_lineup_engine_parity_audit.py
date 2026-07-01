import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_lineup_engine_parity_audit import audit_team, build_report  # noqa: E402


def player(pid, pos, prob=80, secondary=None, overall=70, stamina_max=90):
    return {
        "id": pid,
        "name": pid,
        "primary_position": pos,
        "secondary_positions": secondary or [],
        "overall": overall,
        "attributes": {"startingProbability": prob},
        "stamina_max": stamina_max,
    }


def full_roster():
    return [
        player("GK1", "GK", prob=85, overall=70),
        player("GK2", "GK", prob=10, overall=78),
        player("LB", "LB"),
        player("CB1", "CB"),
        player("CB2", "CB"),
        player("RB", "RB"),
        player("CM1", "CM"),
        player("CM2", "CM"),
        player("CM3", "CM"),
        player("LW", "LW"),
        player("ST", "ST"),
        player("RW", "RW"),
    ]


def test_audit_team_reports_display_and_engine_parity():
    row = audit_team({"teamId": "TST", "name": "Test", "defaultFormation": "4-3-3"}, full_roster())

    assert row["parityOk"] is True
    assert row["mismatchCount"] == 0
    assert row["displayedStarterCount"] == 11
    assert row["simulatedStarterCount"] == 11
    assert row["displayedPlayerIds"] == row["simulatedPlayerIds"]
    assert row["displayedPlayerIds"][0] == "GK1"


def test_audit_team_handles_null_stamina_from_seed_data():
    roster = full_roster()
    roster[0]["stamina_max"] = None

    row = audit_team({"teamId": "TST", "name": "Test", "defaultFormation": "4-3-3"}, roster)

    assert row["parityOk"] is True
    assert row["displayedPlayerIds"][0] == "GK1"


def test_build_report_current_seed_has_full_parity():
    report = build_report()

    assert report["teamCount"] == 48
    assert report["checkedTeamCount"] == 48
    assert report["mismatchTeamCount"] == 0
    assert report["mismatchSlotCount"] == 0
    assert report["incompleteDisplayedLineupTeamCount"] == 0
    assert report["incompleteSimulatedLineupTeamCount"] == 0
    assert report["fullParityTeamCount"] == 48
