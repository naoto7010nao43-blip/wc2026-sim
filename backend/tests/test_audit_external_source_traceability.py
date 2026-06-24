import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_external_source_traceability import audit_traceability


def candidate(url=None):
    source = {"name": "Federation report", "tier": "A", "observedDate": "2026-06-24"}
    if url:
        source["url"] = url
    return {
        "claim": "Manager uses a stable 4-2-3-1 shape in competitive fixtures.",
        "sources": [source],
        "confidence": "medium",
        "mapsTo": "default_formation",
        "candidateCategory": "tactical-profile candidate",
    }


def report(rows):
    return {
        "generatedAt": "2026-06-24T00:00:00+09:00",
        "scope": {"coveredTeams": ["BRA"], "remainingUnresearchedTeams": []},
        "teams": [
            {
                "teamId": "BRA",
                "teamName": "Brazil",
                "managerStatus": [],
                "formationCandidates": rows,
                "tacticalProfileCandidates": [],
                "keyPlayerStatusCandidates": [],
                "nationalStrengthContext": [],
                "substitutionTendencyCandidates": [],
            }
        ],
    }


def test_traceability_marks_all_missing_urls_as_blocking_for_data_changes():
    result = audit_traceability(report([candidate()]), generated_at="2026-06-24T00:00:00+00:00")

    assert result["severity"] == "blocking_for_data_changes"
    assert result["candidateCount"] == 1
    assert result["candidateMissingResolvableUrlCount"] == 1
    assert result["missingUrlSourceCount"] == 1
    assert result["missingUrlByTeam"]["BRA"] == 1
    assert result["missingUrlByCategory"]["formationCandidates"] == 1


def test_traceability_passes_when_candidates_have_resolvable_urls():
    result = audit_traceability(report([candidate("https://example.test/report")]), generated_at="2026-06-24T00:00:00+00:00")

    assert result["severity"] == "pass"
    assert result["candidateMissingResolvableUrlCount"] == 0
    assert result["missingUrlSourceCount"] == 0
