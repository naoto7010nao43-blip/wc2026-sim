import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_source_provenance_audit import (
    build_report,
    build_seed_source_summary,
    flatten_decision_candidates,
    source_risk_flags,
)


def player(**overrides):
    row = {
        "id": "AAA_ONE",
        "team_id": "AAA",
        "name": "Player One",
        "source_citations": ["Transfermarkt profile"],
    }
    row.update(overrides)
    return row


def decision_candidate(**overrides):
    row = {
        "player_id": "AAA_ONE",
        "name": "Player One",
        "primary_position": "CM",
        "current_overall": 55,
        "suggested_codex_action": "inspect_for_possible_upgrade",
    }
    row.update(overrides)
    return row


def decision_report():
    return {
        "generatedAt": "decision",
        "teams": [{
            "team_id": "AAA",
            "team_name": "Alpha",
            "candidate_for_later_proposal": [decision_candidate(player_id="AAA_ONE")],
            "source_review_first": [decision_candidate(player_id="AAA_TWO", name="Player Two")],
            "do_not_use_for_upgrade_proposal": [],
            "monitor_only": [],
        }],
    }


def test_source_risk_flags_detects_game_rating_and_secondary_sources():
    flags = source_risk_flags(["EA FC26 signal", "Fotmob profile"])
    markers = {flag["marker"] for flag in flags}
    assert {"EA FC", "FC26", "Fotmob"} <= markers
    assert any(flag["severity"] == "high" for flag in flags)


def test_build_seed_source_summary_counts_only_players_with_risk():
    summary = build_seed_source_summary([
        player(id="AAA_ONE"),
        player(id="AAA_TWO", source_citations=["WC2026 squad note"]),
    ])
    assert summary["seed_player_count"] == 2
    assert summary["players_with_source_risk"] == 1
    assert summary["marker_counts"]["WC2026"] == 1


def test_flatten_decision_candidates_preserves_bucket_and_team():
    rows = flatten_decision_candidates(decision_report())
    assert len(rows) == 2
    assert rows[0]["team_id"] == "AAA"
    assert rows[0]["decision_bucket"] == "candidate_for_later_proposal"
    assert rows[1]["decision_bucket"] == "source_review_first"


def test_build_report_separates_clear_and_source_review_candidates():
    report = build_report(
        players=[
            player(id="AAA_ONE", source_citations=["Transfermarkt profile"]),
            player(id="AAA_TWO", source_citations=["EA FC 26 rating used as signal"]),
        ],
        decision_report=decision_report(),
    )
    assert report["decisionCandidateCount"] == 2
    assert report["clearLaterProposalCandidateCount"] == 1
    assert report["sourceReviewCandidateCount"] == 1
    team = report["teams"][0]
    assert team["clear_later_proposal_candidates"][0]["player_id"] == "AAA_ONE"
    assert team["source_review_candidates"][0]["player_id"] == "AAA_TWO"


def test_build_report_includes_japanese_recommendations():
    report = build_report(players=[player()], decision_report=decision_report())
    assert report["recommendations_ja"]
    assert "能力値" in report["recommendations_ja"][0]
