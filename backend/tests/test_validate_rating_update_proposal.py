import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_rating_update_proposal import validate_change, validate_proposal


def valid_change(**overrides):
    row = {
        "playerId": "CRO_GVARDIOL",
        "teamId": "CRO",
        "field": "defense",
        "currentValue": 70,
        "proposedValue": 74,
        "action": "upgrade",
        "sourceTier": "A",
        "confidence": "medium",
        "reason": "Local workbench and driver audit both point to a defensive review candidate.",
        "evidenceRefs": ["rating_review_workbench_2026-06-23.json"],
    }
    row.update(overrides)
    return row


def valid_proposal(**overrides):
    proposal = {
        "proposalVersion": "rating-proposal-v1",
        "generatedAt": "2026-06-23T00:00:00+00:00",
        "summary": "Small bounded rating review proposal for one team.",
        "changes": [valid_change()],
        "benchmarkComparison": {
            "status": "pass",
            "beforeReport": "prediction_benchmark_baseline_2026-06-23.json",
            "afterReport": "prediction_benchmark_after_2026-06-23.json",
            "watchlistImplausibleReduction": 2,
        },
    }
    proposal.update(overrides)
    return proposal


def test_validate_change_accepts_bounded_supported_change():
    assert validate_change(valid_change(), 0) == []


def test_validate_change_rejects_unknown_field():
    errors = validate_change(valid_change(field="marketValue"), 0)
    assert any("not an allowed rating field" in error for error in errors)


def test_validate_change_rejects_large_overall_delta():
    errors = validate_change(valid_change(field="overall", currentValue=60, proposedValue=70), 0)
    assert any("above max 5" in error for error in errors)


def test_validate_change_rejects_large_attribute_delta():
    errors = validate_change(valid_change(field="defense", currentValue=60, proposedValue=75), 0)
    assert any("above max 8" in error for error in errors)


def test_validate_change_requires_evidence_and_non_c_source_tier():
    errors = validate_change(valid_change(sourceTier="C", evidenceRefs=[]), 0)
    assert any("sourceTier" in error for error in errors)
    assert any("evidenceRefs" in error for error in errors)


def test_validate_proposal_accepts_valid_payload():
    report = validate_proposal(valid_proposal())
    assert report["valid"] is True
    assert report["errors"] == []


def test_validate_proposal_requires_passing_benchmark_comparison():
    proposal = valid_proposal(benchmarkComparison={"status": "review"})
    report = validate_proposal(proposal)
    assert report["valid"] is False
    assert any("benchmarkComparison.status" in error for error in report["errors"])


def test_validate_proposal_rejects_duplicate_player_field_change():
    proposal = valid_proposal(changes=[valid_change(), valid_change()])
    report = validate_proposal(proposal)
    assert report["valid"] is False
    assert any("duplicate change" in error for error in report["errors"])


def test_validate_proposal_warns_on_large_change_set():
    proposal = valid_proposal(changes=[valid_change(playerId=f"P{i}") for i in range(61)])
    report = validate_proposal(proposal)
    assert report["valid"] is True
    assert report["warningCount"] == 1
