import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_rating_probe_sensitivity import (
    apply_probe_changes,
    clean_later_candidates,
    clamp_rating,
    relevant_attribute_fields,
)


def test_clamp_rating_adds_probe_delta_and_caps_at_99():
    assert clamp_rating(50) == 52
    assert clamp_rating(98) == 99


def test_relevant_attribute_fields_uses_driver_and_position():
    assert "tackling" in relevant_attribute_fields("CB", "defense")
    assert "finishing" in relevant_attribute_fields("ST", "attack")
    assert "decisionMaking" in relevant_attribute_fields("CM", "defense")
    assert "goalkeeperReflexes" in relevant_attribute_fields("GK", "defense")


def test_clean_later_candidates_reads_only_later_bucket():
    decision = {
        "teams": [{
            "team_id": "AAA",
            "team_name": "Alpha",
            "dominant_negative_driver": "attack",
            "candidate_for_later_proposal": [{"player_id": "P1", "name": "One"}],
            "source_review_first": [{"player_id": "P2", "name": "Two"}],
        }],
    }
    rows = clean_later_candidates(decision)
    assert len(rows) == 1
    assert rows[0]["player_id"] == "P1"
    assert rows[0]["team_id"] == "AAA"
    assert rows[0]["dominant_negative_driver"] == "attack"


def test_apply_probe_changes_mutates_copy_only_and_records_fields():
    ratings = [{
        "playerId": "P1",
        "overall": 50,
        "positionOverall": 51,
        "attack": 52,
        "finishing": 53,
        "shotPower": 54,
        "chanceCreation": 55,
        "ballCarrying": 56,
        "crossing": 57,
    }]
    candidates = [{
        "player_id": "P1",
        "team_id": "AAA",
        "name": "One",
        "primary_position": "ST",
        "dominant_negative_driver": "attack",
    }]
    modified, applied = apply_probe_changes(ratings, candidates)
    assert ratings[0]["overall"] == 50
    assert modified[0]["overall"] == 52
    assert modified[0]["finishing"] == 55
    assert applied[0]["player_id"] == "P1"
    changed_fields = {row["field"] for row in applied[0]["field_changes"]}
    assert {"overall", "positionOverall", "finishing"} <= changed_fields


def test_apply_probe_changes_skips_missing_player():
    modified, applied = apply_probe_changes(
        [{"playerId": "P1", "overall": 50}],
        [{"player_id": "P2", "team_id": "AAA", "name": "Two", "primary_position": "CM"}],
    )
    assert modified == [{"playerId": "P1", "overall": 50}]
    assert applied == []
