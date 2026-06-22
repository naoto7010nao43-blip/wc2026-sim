import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from migrate_to_player_data_v2 import _migrate_career_stats, _migrate_manager, _migrate_player, _migrate_team

NOW = "2026-06-22T00:00:00+00:00"


def test_migrate_team_carries_over_known_fields():
    team = {"id": "BRA", "name": "Brazil", "confederation": "CONMEBOL", "fifa_rank": 3,
             "default_formation": "4-2-3-1", "group_id": "A", "tactical_profile": {"manager_name": "Test Coach"}}
    out = _migrate_team(team, NOW)
    assert out["teamId"] == "BRA"
    assert out["fifaRank"] == 3
    assert out["dataConfidence"] == "official"


def test_migrate_team_without_fifa_rank_is_marked_missing():
    team = {"id": "XYZ", "name": "Nowhere", "confederation": "UEFA", "fifa_rank": None,
             "default_formation": "4-4-2", "group_id": None, "tactical_profile": None}
    out = _migrate_team(team, NOW)
    assert out["dataConfidence"] == "missing"


def test_migrate_manager_extracts_name_from_tactical_profile():
    team = {"id": "BRA", "tactical_profile": {"manager_name": "Test Coach"}}
    out = _migrate_manager(team, NOW)
    assert out["managerId"] == "mgr_bra"
    assert out["teamCode"] == "BRA"
    assert out["name"] == "Test Coach"
    assert out["dataConfidence"] == "external"


def test_migrate_manager_without_name_is_marked_missing_not_fabricated():
    team = {"id": "XYZ", "tactical_profile": None}
    out = _migrate_manager(team, NOW)
    assert out["name"] is None
    assert out["dataConfidence"] == "missing"


def test_migrate_career_stats_renames_keys_to_camel_case():
    stats = {"appearances": 30, "minutes_played": 2500, "tackles_per90": 1.0}
    out = _migrate_career_stats(stats)
    assert out == {"appearances": 30, "minutesPlayed": 2500, "tacklesPer90": 1.0}


def test_migrate_career_stats_handles_none():
    assert _migrate_career_stats(None) is None


def test_migrate_player_leaves_unknown_fields_as_null_not_fabricated():
    player = {"id": "p1", "team_id": "BRA", "name": "Test Player", "age": 26,
              "primary_position": "ST", "secondary_positions": [], "market_value_eur": 1_000_000,
              "career_stats": {"appearances": 10}, "qualitative_adjustments": {}, "source_citations": []}
    out = _migrate_player(player, NOW)
    for unknown_field in ("clubName", "clubCountry", "leagueName", "caps", "nationalTeamGoals", "heightCm", "weightKg", "dateOfBirth", "shirtNumber"):
        assert out[unknown_field] is None
    assert out["playerId"] == "p1"
    assert out["marketValueEur"] == 1_000_000
