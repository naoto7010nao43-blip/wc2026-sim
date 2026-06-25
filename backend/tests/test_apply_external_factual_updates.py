import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.apply_external_factual_updates import apply_updates, apply_updates_v2, update_metadata_freshness


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
