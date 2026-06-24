import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_external_data_decision_queue import build_decision_queue


def source(tier="A"):
    return {"name": "Federation report", "tier": tier, "observedDate": "2026-06-24"}


def candidate(**overrides):
    row = {
        "claim": "Manager has repeatedly used a 4-2-3-1 base shape in competitive fixtures this cycle.",
        "sources": [source("A"), source("B")],
        "confidence": "medium",
        "mapsTo": "default_formation",
        "candidateCategory": "tactical-profile candidate",
    }
    row.update(overrides)
    return row


def report():
    return {
        "generatedAt": "2026-06-24T00:00:00+09:00",
        "scope": {"coveredTeams": ["BRA"], "remainingUnresearchedTeams": []},
        "teams": [
            {
                "teamId": "BRA",
                "teamName": "Brazil",
                "managerStatus": [],
                "formationCandidates": [candidate()],
                "tacticalProfileCandidates": [
                    candidate(
                        claim="A Tier B tactical article claims a high press, but this should not be treated as verified high confidence.",
                        sources=[source("B")],
                        confidence="high",
                        mapsTo="press_intensity",
                    )
                ],
                "keyPlayerStatusCandidates": [],
                "nationalStrengthContext": [],
                "substitutionTendencyCandidates": [
                    candidate(
                        claim="The manager tends to make the first attacking substitution before the hour when chasing.",
                        mapsTo="substitution_tendency",
                        candidateCategory="future-engine candidate",
                    )
                ],
            }
        ],
    }


def test_decision_queue_separates_current_fields_warning_holds_and_future_engine():
    result = build_decision_queue(report(), {"valid": True}, generated_at="2026-06-24T00:00:00+00:00")

    assert result["validInput"] is True
    assert result["candidateCount"] == 3
    assert result["currentFieldReviewCount"] == 1
    assert result["warningHoldCount"] == 1
    assert result["futureEngineCount"] == 1
    assert result["currentFieldReviewQueue"][0]["mapsTo"] == "default_formation"
    assert result["warningHoldQueue"][0]["mapsTo"] == "press_intensity"
    assert result["futureEngineQueue"][0]["mapsTo"] == "substitution_tendency"


def test_decision_queue_preserves_team_level_counts_without_applying_data():
    result = build_decision_queue(report(), {"valid": True}, generated_at="2026-06-24T00:00:00+00:00")
    team = result["teams"][0]

    assert team["teamId"] == "BRA"
    assert team["candidateCount"] == 3
    assert team["bucketCounts"]["current_field_review"] == 1
    assert team["bucketCounts"]["warning_hold"] == 1
    assert team["bucketCounts"]["future_engine"] == 1
    assert "seed" not in result
