import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_team_data_review_plan import (
    build_report,
    build_review_reasons,
    build_team_row,
    compute_priority_band,
    compute_priority_score,
    latest_report,
    recommended_next_action,
)


def test_priority_score_weights_rank_underperformance_highest():
    underperforming = compute_priority_score(
        rank_underperformance_flags=3, high_confidence_add_count=0, other_add_count=0,
        ambiguous_pair_count=0, likely_stale_seed_player_count=0,
    )
    roster_noise_only = compute_priority_score(
        rank_underperformance_flags=0, high_confidence_add_count=20, other_add_count=30,
        ambiguous_pair_count=0, likely_stale_seed_player_count=0,
    )
    assert underperforming > roster_noise_only


def test_priority_band_thresholds():
    assert compute_priority_band(0.0) == "low"
    assert compute_priority_band(5.0) == "medium"
    assert compute_priority_band(20.0) == "high"


def test_roster_noise_alone_does_not_reach_high_band():
    # A team's official roster always has more players than this project's
    # intentionally shallow seed roster -- that structural gap must not
    # alone push a team into "high" priority.
    score = compute_priority_score(
        rank_underperformance_flags=0, high_confidence_add_count=15, other_add_count=20,
        ambiguous_pair_count=0, likely_stale_seed_player_count=0,
    )
    assert compute_priority_band(score) != "high"


def test_build_review_reasons_lists_each_active_signal():
    reasons = build_review_reasons(
        rank_underperformance_flags=3, ambiguous_pair_count=2, likely_stale_seed_player_count=1, high_confidence_add_count=4,
    )
    assert any("FIFAランク比" in r for r in reasons)
    assert any("名寄せ候補" in r for r in reasons)
    assert any("古いシード選手" in r for r in reasons)
    assert any("追加候補" in r for r in reasons)


def test_build_review_reasons_falls_back_when_nothing_flagged():
    assert build_review_reasons(0, 0, 0, 0) == ["特筆すべき指摘なし"]


def test_recommended_next_action_priority_order():
    assert recommended_next_action(3, 2, 1, 4, 5) == "スカッド能力値レビュー"
    assert recommended_next_action(0, 2, 1, 4, 5) == "名寄せ候補レビュー"
    assert recommended_next_action(0, 0, 1, 4, 5) == "ロスター候補レビュー"
    assert recommended_next_action(0, 0, 0, 0, 0) == "低優先度"


def test_build_team_row_pulls_audit_and_roster_signals():
    team = {"id": "CRO", "name": "Croatia", "fifa_rank": 10}
    audit_report = {
        "ratings": {"attack": {"highest": [], "lowest": [{"team_id": "CRO", "attack": 50.0}]}},
        "frequentRankUnderperformers": [{"team_id": "CRO", "implausible_matchup_count": 9}],
    }
    roster_report = {
        "teamReports": [{
            "team_code": "CRO", "seed_roster_size": 14,
            "high_confidence_add_candidates": [1, 2], "other_add_candidates": [1],
            "ambiguous_pairs": [], "likely_stale_seed_players": [1],
        }],
    }
    row = build_team_row(team, audit_report, roster_report)
    assert row["rank_underperformance_flags"] == 9
    assert row["attack_rating"] == 50.0
    assert row["seed_roster_size"] == 14
    assert row["high_confidence_add_candidate_count"] == 2
    assert row["likely_stale_seed_player_count"] == 1
    assert row["priority_band"] == "high"
    assert row["recommended_next_action"] == "スカッド能力値レビュー"


def test_build_team_row_handles_team_absent_from_both_reports():
    team = {"id": "ZZZ", "name": "Nowhere", "fifa_rank": 99}
    row = build_team_row(team, None, None)
    assert row["rank_underperformance_flags"] == 0
    assert row["priority_score"] == 0.0
    assert row["priority_band"] == "low"
    assert row["seed_roster_size"] is None


def test_build_report_sorts_descending_by_priority_score():
    teams = [
        {"id": "LOW", "name": "Low", "fifa_rank": 1},
        {"id": "HIGH", "name": "High", "fifa_rank": 2},
    ]
    audit_report = {"ratings": {}, "frequentRankUnderperformers": [{"team_id": "HIGH", "implausible_matchup_count": 5}]}
    report = build_report(teams, audit_report, None)
    assert [r["team_id"] for r in report["teams"]] == ["HIGH", "LOW"]
    assert report["teamCount"] == 2
    assert "generatedAt" in report
    assert "note" in report


def test_latest_report_returns_none_when_no_files_match(tmp_path, monkeypatch):
    import build_team_data_review_plan as module
    monkeypatch.setattr(module, "REPORTS_DIR", tmp_path)
    assert latest_report("nonexistent_*.json") is None


def test_latest_report_picks_lexicographically_latest_file(tmp_path, monkeypatch):
    import build_team_data_review_plan as module
    monkeypatch.setattr(module, "REPORTS_DIR", tmp_path)
    (tmp_path / "sample_2026-06-01.json").write_text(json.dumps({"generatedAt": "old"}), encoding="utf-8")
    (tmp_path / "sample_2026-06-23.json").write_text(json.dumps({"generatedAt": "new"}), encoding="utf-8")
    result = latest_report("sample_*.json")
    assert result["generatedAt"] == "new"
