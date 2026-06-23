import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_rating_decision_audit import (
    build_report,
    classify_candidate,
    dominant_driver,
    position_matches_driver,
    source_risk_flags,
)


def candidate(**overrides):
    row = {
        "player_id": "P1",
        "name": "Player One",
        "primary_position": "CB",
        "current_overall": 60,
        "review_score": 20,
        "review_band": "medium",
        "suggested_codex_action": "inspect_for_possible_upgrade",
        "review_flags": ["team_rank_underperformance", "caps_outpace_rating"],
        "source_citations": ["Transfermarkt profile"],
    }
    row.update(overrides)
    return row


def test_dominant_driver_uses_highest_count():
    summary = {"primary_negative_driver_counts": {"attack": 2, "defense": 5}}
    assert dominant_driver(summary) == "defense"
    assert dominant_driver(None) == "unknown"


def test_position_matches_driver_for_attack_and_defense():
    assert position_matches_driver("ST", "attack") is True
    assert position_matches_driver("CB", "attack") is False
    assert position_matches_driver("CB", "defense") is True
    assert position_matches_driver("CM", "defense") is True


def test_source_risk_flags_detects_soft_sources():
    flags = source_risk_flags(["EA FC26 rising-star rating used as minor signal", "Transfermarkt"])
    assert "EA FC" in flags
    assert "FC26" in flags


def test_classify_candidate_accepts_aligned_upgrade_without_source_risk():
    result = classify_candidate(candidate(primary_position="CB"), "defense")
    assert result["decision_bucket"] == "candidate_for_later_proposal"
    assert result["driver_alignment"] is True


def test_classify_candidate_routes_source_risk_first():
    result = classify_candidate(candidate(source_citations=["Fotmob 2026"]), "defense")
    assert result["decision_bucket"] == "source_review_first"
    assert result["source_risk_flags"] == ["Fotmob"]


def test_classify_candidate_blocks_counterproductive_downgrade():
    result = classify_candidate(
        candidate(suggested_codex_action="inspect_for_possible_downgrade"),
        "defense",
    )
    assert result["decision_bucket"] == "do_not_use_for_upgrade_proposal"
    assert result["counterproductive_for_team_underperformance"] is True


def test_build_report_counts_decision_buckets():
    workbench = {
        "generatedAt": "workbench",
        "teams": [{
            "team_id": "CRO",
            "team_name": "Croatia",
            "rank_underperformance_flags": 9,
            "rating_review_candidates": [
                candidate(player_id="P1", primary_position="CB"),
                candidate(player_id="P2", suggested_codex_action="inspect_for_possible_downgrade"),
            ],
        }],
    }
    driver = {
        "generatedAt": "driver",
        "watchlistTeams": [{
            "team_id": "CRO",
            "summary": {"primary_negative_driver_counts": {"defense": 5}},
        }],
    }
    report = build_report(workbench, driver)
    assert report["teamCount"] == 1
    assert report["bucketCounts"]["candidate_for_later_proposal"] == 1
    assert report["bucketCounts"]["do_not_use_for_upgrade_proposal"] == 1
