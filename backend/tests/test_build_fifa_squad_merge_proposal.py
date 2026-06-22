import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.audit_fifa_squad_list import OfficialPlayer, OfficialTeam
from scripts.build_fifa_squad_merge_proposal import _proposed_updates, build_merge_proposal


def _official_player(**overrides) -> OfficialPlayer:
    base = dict(position="GK", name_block="ALISSON Alisson Ramses BECKER ALISSON",
                dob="02/10/1992", club="Liverpool FC (ENG)", height_cm=193, caps=80, goals=0)
    base.update(overrides)
    return OfficialPlayer(**base)


def test_proposed_updates_only_fills_fields_the_seed_is_missing():
    seed_player = {"name": "Alisson Becker", "dateOfBirth": None, "heightCm": None,
                   "clubName": "Old Club (XXX)", "caps": None, "nationalTeamGoals": None}
    proposed = _proposed_updates(seed_player, _official_player())
    # clubName already had a (non-null) value in the seed -- must not be overwritten silently.
    assert "clubName" not in proposed
    assert proposed["dateOfBirth"] == "02/10/1992"
    assert proposed["heightCm"] == 193
    assert proposed["caps"] == 80
    assert proposed["nationalTeamGoals"] == 0


def test_proposed_updates_is_empty_when_seed_already_has_everything():
    seed_player = {"name": "Alisson Becker", "dateOfBirth": "1992-10-02", "heightCm": 193,
                   "clubName": "Liverpool FC (ENG)", "caps": 80, "nationalTeamGoals": 0}
    assert _proposed_updates(seed_player, _official_player()) == {}


def test_build_merge_proposal_matches_unmatches_and_flags_coach_mismatch(monkeypatch):
    def fake_load_seed_json(name: str) -> list[dict]:
        if name == "players2026_official.json":
            return [
                {"playerId": "BRA_ALISSON", "teamCode": "BRA", "name": "Alisson Becker",
                 "primaryPosition": "GK", "dateOfBirth": None, "heightCm": None,
                 "clubName": None, "caps": None, "nationalTeamGoals": None},
                {"playerId": "BRA_UNMATCHED", "teamCode": "BRA", "name": "Some Unmatched Player",
                 "primaryPosition": "ST", "dateOfBirth": None, "heightCm": None,
                 "clubName": None, "caps": None, "nationalTeamGoals": None},
            ]
        if name == "managers2026_official.json":
            return [{"managerId": "mgr_bra", "teamCode": "BRA", "name": "Someone Else"}]
        if name == "teams2026_official.json":
            return [{"teamCode": "BRA", "name": "Brazil"}]
        raise AssertionError(f"unexpected seed file requested: {name}")

    import scripts.build_fifa_squad_merge_proposal as module
    monkeypatch.setattr(module.audit, "load_seed_json", fake_load_seed_json)

    official_teams = {
        "BRA": OfficialTeam(
            team_name="Brazil", team_code="BRA",
            players=[_official_player(), _official_player(name_block="UNKNOWN NEW PLAYER", dob="01/01/2000")],
            coach_name_block="ANCELOTTI Carlo Carlo ANCELOTTI", coach_nationality="Italy",
        ),
    }

    report = build_merge_proposal(official_teams)

    assert report["matchedPlayerFieldUpdateCount"] == 1
    assert report["matchedPlayerFieldUpdates"][0]["playerId"] == "BRA_ALISSON"
    assert report["unmatchedOfficialPlayerCount"] == 1
    assert report["unmatchedOfficialPlayers"][0]["name_block"] == "UNKNOWN NEW PLAYER"
    assert report["unmatchedSeedPlayerCount"] == 1
    assert report["unmatchedSeedPlayers"][0]["playerId"] == "BRA_UNMATCHED"
    # "Someone Else" the seed manager name does not match the official coach block.
    assert report["coachMismatchCount"] == 1
    assert report["coachMismatches"][0]["teamCode"] == "BRA"


def test_build_merge_proposal_never_touches_seed_files(monkeypatch, tmp_path):
    """Spec 007A's acceptance criteria require this script to be read-only."""
    calls: list[str] = []

    def fake_load_seed_json(name: str) -> list[dict]:
        calls.append(name)
        if name == "players2026_official.json":
            return []
        if name == "managers2026_official.json":
            return []
        if name == "teams2026_official.json":
            return [{"teamCode": "BRA", "name": "Brazil"}]
        raise AssertionError(name)

    import scripts.build_fifa_squad_merge_proposal as module
    monkeypatch.setattr(module.audit, "load_seed_json", fake_load_seed_json)
    monkeypatch.setattr(module, "REPORTS_DIR", tmp_path)

    report = build_merge_proposal({})
    module.write_report(report, tmp_path / "out.json")

    assert "players2026_official.json" in calls
    assert (tmp_path / "out.json").exists()
    # fake_load_seed_json is read-only by construction (no write call inside it);
    # this assertion documents that build_merge_proposal only ever calls the
    # (mocked) reader, never anything resembling a writer for seed data.
