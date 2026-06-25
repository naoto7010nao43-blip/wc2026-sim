import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.apply_external_factual_updates import (
    apply_updates,
    apply_updates_v2,
    regenerate_legacy_players_json,
    regenerate_legacy_teams_json,
    update_metadata_freshness,
)


def test_apply_updates_changes_matching_field():
    teams = [{"id": "URU", "fifa_rank": 14}, {"id": "ARG", "fifa_rank": 1}]
    updates = [{"teamId": "URU", "field": "fifa_rank", "oldValue": 14, "newValue": 16}]

    applied, skipped = apply_updates(teams, updates)

    assert len(applied) == 1
    assert len(skipped) == 0
    by_id = {team["id"]: team for team in teams}
    assert by_id["URU"]["fifa_rank"] == 16
    assert by_id["ARG"]["fifa_rank"] == 1


def test_apply_updates_skips_when_live_value_no_longer_matches_recorded_old_value():
    teams = [{"id": "URU", "fifa_rank": 99}]
    updates = [{"teamId": "URU", "field": "fifa_rank", "oldValue": 14, "newValue": 16}]

    applied, skipped = apply_updates(teams, updates)

    assert applied == []
    assert len(skipped) == 1
    assert skipped[0]["skipReason"] == "seed_value_changed_since_candidate"
    assert skipped[0]["liveValue"] == 99
    by_id = {team["id"]: team for team in teams}
    assert by_id["URU"]["fifa_rank"] == 99


def test_apply_updates_skips_unknown_team():
    teams = [{"id": "URU", "fifa_rank": 14}]
    updates = [{"teamId": "ZZZ", "field": "fifa_rank", "oldValue": 14, "newValue": 16}]

    applied, skipped = apply_updates(teams, updates)

    assert applied == []
    assert skipped[0]["skipReason"] == "team_not_found"


def test_apply_updates_is_idempotent_on_second_run():
    teams = [{"id": "URU", "fifa_rank": 14}]
    updates = [{"teamId": "URU", "field": "fifa_rank", "oldValue": 14, "newValue": 16}]

    applied_once, _ = apply_updates(teams, updates)
    assert len(applied_once) == 1

    applied_twice, skipped_twice = apply_updates(teams, updates)
    assert applied_twice == []
    assert skipped_twice[0]["skipReason"] == "seed_value_changed_since_candidate"
    assert skipped_twice[0]["liveValue"] == 16


def test_apply_updates_v2_mirrors_the_field_with_translated_name():
    teams_v2 = [{"teamId": "URU", "fifaRank": 14}, {"teamId": "ARG", "fifaRank": 1}]
    updates = [{"teamId": "URU", "field": "fifa_rank", "oldValue": 14, "newValue": 16}]

    applied, skipped = apply_updates_v2(teams_v2, updates)

    assert len(applied) == 1
    assert skipped == []
    by_id = {team["teamId"]: team for team in teams_v2}
    assert by_id["URU"]["fifaRank"] == 16
    assert by_id["ARG"]["fifaRank"] == 1


def test_apply_updates_v2_skips_when_live_value_no_longer_matches():
    teams_v2 = [{"teamId": "URU", "fifaRank": 99}]
    updates = [{"teamId": "URU", "field": "fifa_rank", "oldValue": 14, "newValue": 16}]

    applied, skipped = apply_updates_v2(teams_v2, updates)

    assert applied == []
    assert skipped[0]["skipReason"] == "v2_seed_value_changed_since_candidate"
    assert skipped[0]["liveValue"] == 99


def test_apply_updates_v2_ignores_fields_with_no_v2_equivalent():
    teams_v2 = [{"teamId": "URU", "fifaRank": 14}]
    updates = [{"teamId": "URU", "field": "manager_name", "oldValue": "Old", "newValue": "New"}]

    applied, skipped = apply_updates_v2(teams_v2, updates)

    assert applied == []
    assert skipped == []


def test_regenerate_legacy_teams_json_translates_field_names():
    teams_v2 = [{
        "teamId": "URU",
        "teamCode": "URU",
        "name": "Uruguay",
        "confederation": "CONMEBOL",
        "fifaRank": 16,
        "defaultFormation": "4-3-3",
        "groupId": "H",
        "tacticalProfile": {"manager_name": "Marcelo Bielsa", "press_intensity": 70},
        "dataConfidence": "official",
        "lastUpdated": "2026-06",
    }]

    legacy = regenerate_legacy_teams_json(teams_v2)

    assert legacy == [{
        "id": "URU",
        "name": "Uruguay",
        "confederation": "CONMEBOL",
        "fifa_rank": 16,
        "default_formation": "4-3-3",
        "group_id": "H",
        "tactical_profile": {"manager_name": "Marcelo Bielsa", "press_intensity": 70},
    }]


def test_regenerate_legacy_teams_json_preserves_fields_with_no_v2_equivalent():
    teams_v2 = [{
        "teamId": "MEX", "name": "Mexico", "confederation": "CONCACAF",
        "fifaRank": 12, "defaultFormation": "4-3-3", "groupId": "A",
        "tacticalProfile": {"manager_name": "Javier Aguirre"},
    }]
    existing_teams = [{
        "id": "MEX", "name": "Mexico", "confederation": "CONCACAF",
        "fifa_rank": 12, "default_formation": "4-3-3", "group_id": "A",
        "tactical_profile": {"manager_name": "Javier Aguirre"},
        "_tactical_profile_basis": "Aguirre favors a pragmatic, structured 4-3-3...",
    }]

    legacy = regenerate_legacy_teams_json(teams_v2, existing_teams)

    assert legacy[0]["_tactical_profile_basis"] == "Aguirre favors a pragmatic, structured 4-3-3..."


def test_regenerate_legacy_teams_json_reflects_an_applied_v2_update():
    teams_v2 = [{
        "teamId": "URU", "name": "Uruguay", "confederation": "CONMEBOL",
        "fifaRank": 14, "defaultFormation": "4-3-3", "groupId": "H", "tacticalProfile": {},
    }]
    apply_updates_v2(teams_v2, [{"teamId": "URU", "field": "fifa_rank", "oldValue": 14, "newValue": 16}])

    legacy = regenerate_legacy_teams_json(teams_v2)

    assert legacy[0]["fifa_rank"] == 16


def test_regenerate_legacy_players_json_translates_field_and_career_stat_names():
    players_v2 = [{
        "playerId": "URU_VALVERDE",
        "teamId": "URU",
        "teamCode": "URU",
        "name": "Federico Valverde",
        "nameJa": "フェデリコ・バルベルデ",
        "age": 27,
        "primaryPosition": "CM",
        "secondaryPositions": ["RM"],
        "careerStats": {
            "appearances": 70, "goals": 12, "assists": 9,
            "minutesPlayed": 5800, "keyPassesPer90": 1.4,
            "successfulDribblesPer90": 1.1, "tacklesPer90": 1.8,
            "interceptionsPer90": 1.0, "aerialDuelsWonPct": 52.0,
            "passCompletionPct": 86.0,
        },
        "marketValueEur": 130000000,
        "qualitativeAdjustments": {"leadership": 0.2},
        "sourceCitations": ["https://example.com/valverde"],
        "staminaMax": 95,
        "clubName": "Real Madrid CF",  # v2-only field, must not leak into legacy
        "dataConfidence": "official",
    }]

    legacy = regenerate_legacy_players_json(players_v2)

    assert legacy == [{
        "id": "URU_VALVERDE",
        "team_id": "URU",
        "name": "Federico Valverde",
        "age": 27,
        "primary_position": "CM",
        "secondary_positions": ["RM"],
        "career_stats": {
            "appearances": 70, "goals": 12, "assists": 9,
            "minutes_played": 5800, "key_passes_per90": 1.4,
            "successful_dribbles_per90": 1.1, "tackles_per90": 1.8,
            "interceptions_per90": 1.0, "aerial_duels_won_pct": 52.0,
            "pass_completion_pct": 86.0,
        },
        "market_value_eur": 130000000,
        "qualitative_adjustments": {"leadership": 0.2},
        "source_citations": ["https://example.com/valverde"],
        "stamina_max": 95,
        "name_ja": "フェデリコ・バルベルデ",
    }]


def test_regenerate_legacy_players_json_keeps_goalkeeper_only_stats_last():
    players_v2 = [{
        "playerId": "BRA_ALISSON", "teamId": "BRA", "name": "Alisson Becker",
        "nameJa": "アリソン", "age": 33, "primaryPosition": "GK",
        "secondaryPositions": [],
        "careerStats": {
            "appearances": 78, "goals": 0, "assists": 1, "minutesPlayed": 6950,
            "keyPassesPer90": 0.1, "successfulDribblesPer90": 0.0,
            "tacklesPer90": 0.0, "interceptionsPer90": 0.1,
            "aerialDuelsWonPct": 55.0, "passCompletionPct": 84.0,
            "savePct": 68.5, "goalsConcededPer90": 0.9,
        },
        "marketValueEur": 30000000, "qualitativeAdjustments": {},
        "sourceCitations": [], "staminaMax": 100,
    }]

    legacy = regenerate_legacy_players_json(players_v2)

    assert list(legacy[0]["career_stats"].keys())[-2:] == ["save_pct", "goals_conceded_per90"]
    assert legacy[0]["career_stats"]["save_pct"] == 68.5


def test_regenerate_legacy_players_json_preserves_fields_with_no_v2_equivalent():
    players_v2 = [{
        "playerId": "JPN_MITOMA", "teamId": "JPN", "name": "Kaoru Mitoma",
        "nameJa": "三笘薫", "age": 28, "primaryPosition": "LW",
        "secondaryPositions": [], "careerStats": {"appearances": 40},
        "marketValueEur": 50000000, "qualitativeAdjustments": {},
        "sourceCitations": [], "staminaMax": 90,
    }]
    existing_players = [{
        "id": "JPN_MITOMA", "team_id": "JPN", "name": "Kaoru Mitoma",
        "_legacy_only_note": "carried over verbatim",
    }]

    legacy = regenerate_legacy_players_json(players_v2, existing_players)

    assert legacy[0]["_legacy_only_note"] == "carried over verbatim"


def test_update_metadata_freshness_updates_fifa_rank_source_and_top_level_timestamp():
    metadata = {
        "lastUpdated": "old",
        "sources": [
            {"name": "FIFA World Ranking (fifa_rank field)", "tier": "S", "lastChecked": "old", "status": "active"},
            {"name": "Other source", "tier": "A", "lastChecked": "old", "status": "active"},
        ],
    }

    update_metadata_freshness(metadata, "2026-06-25T00:00:00+00:00")

    assert metadata["lastUpdated"] == "2026-06-25T00:00:00+00:00"
    by_name = {source["name"]: source for source in metadata["sources"]}
    assert by_name["FIFA World Ranking (fifa_rank field)"]["lastChecked"] == "2026-06-25T00:00:00+00:00"
    assert by_name["Other source"]["lastChecked"] == "old"
