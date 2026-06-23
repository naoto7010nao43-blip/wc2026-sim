import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_external_data_verification_report import (
    candidate_quality_score,
    validate_candidate,
    validate_report,
)


def source(tier="A"):
    return {
        "name": "Federation match report",
        "url": "https://example.test/report",
        "tier": tier,
        "observedDate": "2026-06-24",
    }


def candidate(**overrides):
    row = {
        "claim": "Manager has repeatedly used a 4-2-3-1 base shape in competitive fixtures.",
        "sources": [source("A"), source("B")],
        "confidence": "medium",
        "mapsTo": "default_formation",
        "candidateCategory": "tactical-profile candidate",
    }
    row.update(overrides)
    return row


def report(**overrides):
    payload = {
        "generatedAt": "2026-06-24T00:00:00+09:00",
        "scope": {"coveredTeams": ["BRA"], "remainingUnresearchedTeams": []},
        "teams": [
            {
                "teamId": "BRA",
                "teamName": "Brazil",
                "managerStatus": [],
                "formationCandidates": [candidate()],
                "tacticalProfileCandidates": [],
                "keyPlayerStatusCandidates": [],
                "nationalStrengthContext": [],
                "substitutionTendencyCandidates": [],
                "recommendedCodexNextActions": [],
            }
        ],
        "crossTeamPatterns": [],
        "futureEngineFeatureCandidates": [],
    }
    payload.update(overrides)
    return payload


def test_validate_report_accepts_sourced_existing_field_candidate():
    result = validate_report(report(), known_team_ids={"BRA"})
    assert result["valid"] is True
    assert result["candidateCount"] == 1
    assert result["existingFieldCandidateCount"] == 1
    assert result["futureEngineCandidateCount"] == 0
    assert result["impactCounts"]["high"] == 1
    assert result["useTierCounts"]["ready_for_codex_review"] == 1
    assert result["topTeamPriorities"][0]["teamId"] == "BRA"
    assert result["teamSignalBandCounts"]["strong"] == 1
    assert result["teamSignalProfiles"][0]["signalBand"] == "strong"


def test_validate_report_rejects_unknown_team_id():
    payload = report(scope={"coveredTeams": ["XXX"]})
    payload["teams"][0]["teamId"] = "XXX"
    result = validate_report(payload, known_team_ids={"BRA"})
    assert result["valid"] is False
    assert any("not in backend/data/seed/teams.json" in error for error in result["errors"])


def test_validate_candidate_keeps_unsourced_claim_as_review_question():
    errors, warnings, score = validate_candidate(
        "formationCandidates",
        {"claim": "Short unsourced note", "mapsTo": "default_formation"},
        "BRA",
        0,
    )
    assert errors == []
    assert any("source tier" in warning for warning in warnings)
    assert any("confidence" in warning for warning in warnings)
    assert any("source reference" in warning for warning in warnings)
    assert score["impactBand"] == "low"
    assert score["useTier"] == "review_question"


def test_validate_report_preserves_sparse_team_signal_without_failing():
    payload = report(scope={"coveredTeams": ["BRA", "CAN"]})
    payload["teams"].append({
        "teamId": "CAN",
        "teamName": "Canada",
        "managerStatus": [],
        "formationCandidates": [
            {"claim": "Possible shape mentioned without enough evidence.", "mapsTo": "default_formation"}
        ],
        "tacticalProfileCandidates": [],
        "keyPlayerStatusCandidates": [],
        "nationalStrengthContext": [],
        "substitutionTendencyCandidates": [],
    })

    result = validate_report(payload, known_team_ids={"BRA", "CAN"})

    assert result["valid"] is True
    can_profile = next(row for row in result["teamSignalProfiles"] if row["teamId"] == "CAN")
    assert can_profile["signalBand"] == "sparse"
    assert can_profile["preservedReviewQuestionCount"] == 1
    assert "CAN" in result["sparseTeamIds"]
    assert any("sparse usable evidence" in warning for warning in result["warnings"])


def test_substitution_candidates_are_future_engine_candidates_not_current_fields():
    sub = candidate(
        claim="The manager often makes the first attacking change before the hour when chasing matches.",
        mapsTo="substitution_tendency",
        candidateCategory="future-engine candidate",
        confidence="medium",
    )
    errors, warnings, score = validate_candidate("substitutionTendencyCandidates", sub, "BRA", 0)
    assert errors == []
    assert warnings == []
    assert score["impactBand"] in {"medium", "low"}
    assert score["useTier"] == "future_engine_candidate"


def test_substitution_candidate_warns_when_mapped_to_nonexistent_current_field():
    sub = candidate(
        claim="The manager often makes the first attacking change before the hour when chasing matches.",
        mapsTo="manager_name",
        candidateCategory="tactical-profile candidate",
        confidence="medium",
    )
    errors, warnings, _ = validate_candidate("substitutionTendencyCandidates", sub, "BRA", 0)
    assert errors == []
    assert any("no engine field" in warning for warning in warnings)
    assert any("future-engine candidate" in warning for warning in warnings)


def test_tier_c_candidate_is_valid_but_warned_and_low_impact():
    weak = candidate(
        sources=[source("C")],
        sourceTier="C",
        confidence="low",
        mapsTo="player_rating",
        candidateCategory="rating-review candidate",
    )
    errors, warnings, score = validate_candidate("keyPlayerStatusCandidates", weak, "BRA", 0)
    assert errors == []
    assert any("Tier C" in warning for warning in warnings)
    assert score["impactBand"] == "low"


def test_quality_score_rewards_strong_sources_and_existing_field_mapping():
    strong = candidate(sources=[source("S"), source("A")], confidence="high", mapsTo="default_formation")
    weak = candidate(sources=[source("C")], confidence="low", mapsTo=None)
    assert candidate_quality_score("formationCandidates", strong) > candidate_quality_score("formationCandidates", weak)
