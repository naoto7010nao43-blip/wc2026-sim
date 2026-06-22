import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.apply_fifa_squad_field_updates import apply_updates, write_outputs


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _seed_dir(tmp_path: Path) -> Path:
    seed = tmp_path / "seed"
    seed.mkdir()
    _write_json(seed / "players2026_official.json", [
        {
            "playerId": "BRA_ALISSON",
            "teamCode": "BRA",
            "dateOfBirth": None,
            "heightCm": None,
            "clubName": None,
            "caps": None,
            "nationalTeamGoals": None,
        },
        {
            "playerId": "BRA_EXISTING",
            "teamCode": "BRA",
            "dateOfBirth": "01/01/2000",
            "heightCm": 180,
            "clubName": "Existing FC",
            "caps": 1,
            "nationalTeamGoals": 0,
        },
    ])
    _write_json(seed / "metadata.json", {
        "lastUpdated": "old",
        "sources": [
            {"name": "FIFA Official Squad feed", "tier": "S", "lastChecked": None, "status": "not_yet_integrated"},
        ],
    })
    return seed


def _proposal_path(tmp_path: Path) -> Path:
    proposal = tmp_path / "proposal.json"
    _write_json(proposal, {
        "generatedAt": "2026-06-22T17:44:43+00:00",
        "matchedPlayerFieldUpdates": [
            {
                "playerId": "BRA_ALISSON",
                "proposedUpdates": {
                    "dateOfBirth": "02/10/1992",
                    "heightCm": 193,
                    "clubName": "Liverpool FC (ENG)",
                    "caps": 80,
                    "nationalTeamGoals": 0,
                },
            },
            {
                "playerId": "BRA_EXISTING",
                "proposedUpdates": {
                    "clubName": "Different FC",
                    "caps": 99,
                },
            },
            {
                "playerId": "MISSING_PLAYER",
                "proposedUpdates": {"caps": 1},
            },
        ],
    })
    return proposal


def test_apply_updates_fills_null_fields_without_adding_or_removing_players(tmp_path):
    seed = _seed_dir(tmp_path)
    reports = tmp_path / "reports"
    proposal = _proposal_path(tmp_path)

    report, players, metadata = apply_updates(
        proposal_path=proposal,
        seed_dir=seed,
        reports_dir=reports,
        now="2026-06-23T00:00:00+00:00",
    )

    assert [p["playerId"] for p in players] == ["BRA_ALISSON", "BRA_EXISTING"]
    alisson = players[0]
    assert alisson["dateOfBirth"] == "02/10/1992"
    assert alisson["heightCm"] == 193
    assert alisson["clubName"] == "Liverpool FC (ENG)"
    assert alisson["caps"] == 80
    assert alisson["nationalTeamGoals"] == 0
    assert report["noPlayersAddedOrRemoved"] is True
    assert report["fieldsAppliedByFieldName"] == {
        "caps": 1,
        "clubName": 1,
        "dateOfBirth": 1,
        "heightCm": 1,
        "nationalTeamGoals": 1,
    }
    assert metadata["sources"][0]["status"] == "active"
    assert metadata["sources"][0]["lastChecked"] == "2026-06-22T17:44:43+00:00"


def test_apply_updates_skips_non_null_conflicts_and_missing_players(tmp_path):
    seed = _seed_dir(tmp_path)
    proposal = _proposal_path(tmp_path)

    report, players, _metadata = apply_updates(
        proposal_path=proposal,
        seed_dir=seed,
        reports_dir=tmp_path / "reports",
        now="2026-06-23T00:00:00+00:00",
    )

    existing = players[1]
    assert existing["clubName"] == "Existing FC"
    assert existing["caps"] == 1
    assert {c["field"] for c in report["skippedConflicts"]} == {"clubName", "caps"}
    assert report["missingPlayerIds"] == ["MISSING_PLAYER"]


def test_write_outputs_persists_seed_metadata_and_report(tmp_path):
    seed = _seed_dir(tmp_path)
    reports = tmp_path / "reports"
    proposal = _proposal_path(tmp_path)
    report, players, metadata = apply_updates(proposal, seed, reports, now="2026-06-23T00:00:00+00:00")

    report_path = write_outputs(report, players, metadata, seed_dir=seed, reports_dir=reports)

    saved_players = json.loads((seed / "players2026_official.json").read_text(encoding="utf-8"))
    saved_metadata = json.loads((seed / "metadata.json").read_text(encoding="utf-8"))
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved_players[0]["caps"] == 80
    assert saved_metadata["sources"][0]["status"] == "active"
    assert saved_report["totalFieldsApplied"] == 5


def test_apply_updates_cleans_existing_pdf_ligature_artifacts(tmp_path):
    seed = _seed_dir(tmp_path)
    players_path = seed / "players2026_official.json"
    players = json.loads(players_path.read_text(encoding="utf-8"))
    players[1]["clubName"] = "SL Ben\x00ca (POR)"
    _write_json(players_path, players)

    proposal = tmp_path / "proposal.json"
    _write_json(proposal, {
        "generatedAt": "2026-06-22T17:44:43+00:00",
        "matchedPlayerFieldUpdates": [],
    })

    report, players, _metadata = apply_updates(
        proposal_path=proposal,
        seed_dir=seed,
        reports_dir=tmp_path / "reports",
        now="2026-06-23T00:00:00+00:00",
    )

    assert players[1]["clubName"] == "SL Benfica (POR)"
    assert report["cleanedExistingFields"] == [{
        "playerId": "BRA_EXISTING",
        "field": "clubName",
        "original": "SL Ben\\u0000ca (POR)",
        "cleaned": "SL Benfica (POR)",
    }]
