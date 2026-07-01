import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_tactical_basis_candidate_review import build_report, extract_urls, recommended_status


def test_extract_urls_strips_sentence_punctuation():
    text = "Sources: https://example.com/a, https://example.com/b."
    assert extract_urls(text) == ["https://example.com/a", "https://example.com/b"]


def test_recommended_status_splits_missing_and_blocked_sources():
    assert recommended_status(0, None, None) == "needs_sources"
    assert recommended_status(2, None, None) == "ready_for_human_review"
    assert recommended_status(2, 2, 0) == "ready_for_human_review"
    assert recommended_status(2, 1, 1) == "blocked_source_review"


def test_build_report_keeps_plain_basis_as_review_candidate_not_verified_seed():
    teams = [
        {"id": "AAA", "name": "Alpha", "_tactical_profile_basis": "Pressing note https://example.com/a"},
        {"id": "BBB", "name": "Beta", "_tactical_profile_basis": "No source note"},
        {"id": "CCC", "name": "Gamma"},
    ]
    report = build_report(teams, check_urls=False)
    assert report["candidateTeamCount"] == 2
    assert report["urlCount"] == 1
    assert report["urlLessCandidateCount"] == 1
    assert report["statusCounts"] == {"ready_for_human_review": 1, "needs_sources": 1}
    rows = {row["team_id"]: row for row in report["teams"]}
    assert rows["AAA"]["recommended_status"] == "ready_for_human_review"
    assert rows["BBB"]["recommended_status"] == "needs_sources"
    assert rows["CCC"]["candidate_present"] is False
