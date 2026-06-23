import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_rating_review_workbench import (
    build_candidate_row,
    build_report,
    build_review_summary_ja,
    build_team_row,
    compute_player_signals,
    compute_review_score,
    percentile_ranks,
    percentile_ranks_by_position_group,
    review_band,
    suggested_codex_action,
    weak_position_groups,
)


def _player(
    player_id,
    position,
    overall,
    *,
    starting_probability=50,
    caps=20,
    market_value_eur=5_000_000,
    low_confidence_attributes=None,
    data_confidence="estimated",
):
    return {
        "player_id": player_id,
        "name": player_id,
        "name_ja": None,
        "primary_position": position,
        "age": 25,
        "club_name": "Some FC",
        "caps": caps,
        "national_team_goals": 0,
        "market_value_eur": market_value_eur,
        "source_citations": [],
        "qualitative_adjustments": {},
        "current_overall": overall,
        "position_overall": overall,
        "starting_probability": starting_probability,
        "uncertainty": 0.2,
        "data_confidence": data_confidence,
        "source_breakdown": {},
        "low_confidence_attributes": low_confidence_attributes or [],
    }


def test_percentile_ranks_handles_few_or_missing_values():
    assert percentile_ranks({"A": 10}) == {"A": None}
    result = percentile_ranks({"A": 10, "B": 20, "C": None})
    assert result["A"] == 0.0
    assert result["B"] == 100.0
    assert result["C"] is None


def test_percentile_ranks_by_position_group_isolates_groups():
    # A goalkeeper with the lowest absolute overall in the dataset should
    # still rank at the TOP of the GK group, not bottom of a mixed pool --
    # this is the regression for the structural bug where comparing GK
    # overall against outfield overall on one shared scale flagged nearly
    # every goalkeeper as "underrated" purely from a baseline gap, not a
    # real per-player signal.
    players = [
        _player("GK_BEST", "GK", 50),
        _player("GK_WORST", "GK", 40),
        _player("FW_BEST", "ST", 90),
        _player("FW_WORST", "ST", 80),
    ]
    pct = percentile_ranks_by_position_group(players, "current_overall")
    assert pct["GK_BEST"] == 100.0
    assert pct["GK_WORST"] == 0.0
    assert pct["FW_BEST"] == 100.0
    assert pct["FW_WORST"] == 0.0


def test_weak_position_groups_only_uses_thin_depth_flags():
    # Must NOT fall back to "lowest average overall among the four groups" --
    # that heuristic always selects GK in the real dataset because GK overall
    # is computed on a structurally lower baseline for every team, not
    # because that team's GK depth is actually thin.
    assert weak_position_groups([]) == set()
    assert weak_position_groups(["thin_defensive_depth"]) == {"DF"}
    assert weak_position_groups(["thin_attacking_depth"]) == {"FW"}
    assert weak_position_groups(["thin_defensive_depth", "thin_attacking_depth"]) == {"DF", "FW"}


def test_compute_review_score_team_flag_alone_stays_in_low_band():
    signals = compute_player_signals(
        _player("X", "CM", 60),
        team_rank_underperformance=True,
        is_weak_position_group=False,
        value_percentile=None,
        caps_percentile=None,
        overall_percentile=None,
        team_median_overall=None,
        shallow_roster=False,
        is_top_contributor=False,
    )
    score = compute_review_score(signals)
    assert review_band(score) != "high"
    assert review_band(score) == "low"


def test_review_band_thresholds():
    assert review_band(30.0) == "high"
    assert review_band(29.9) == "medium"
    assert review_band(15.0) == "medium"
    assert review_band(14.9) == "low"


def test_suggested_codex_action_downgrade_only():
    signals = compute_player_signals(
        _player("X", "CM", 80),
        team_rank_underperformance=False,
        is_weak_position_group=False,
        value_percentile=10.0,
        caps_percentile=10.0,
        overall_percentile=90.0,
        team_median_overall=None,
        shallow_roster=False,
        is_top_contributor=False,
    )
    assert suggested_codex_action(signals) == "inspect_for_possible_downgrade"


def test_suggested_codex_action_upgrade():
    signals = compute_player_signals(
        _player("X", "CM", 40),
        team_rank_underperformance=False,
        is_weak_position_group=False,
        value_percentile=90.0,
        caps_percentile=90.0,
        overall_percentile=10.0,
        team_median_overall=None,
        shallow_roster=False,
        is_top_contributor=False,
    )
    assert suggested_codex_action(signals) == "inspect_for_possible_upgrade"


def test_suggested_codex_action_verify_roster_role_first():
    signals = compute_player_signals(
        _player("X", "CM", 60),
        team_rank_underperformance=False,
        is_weak_position_group=False,
        value_percentile=None,
        caps_percentile=None,
        overall_percentile=None,
        team_median_overall=None,
        shallow_roster=True,
        is_top_contributor=True,
    )
    assert suggested_codex_action(signals) == "verify_roster_role_first"


def test_suggested_codex_action_monitor_only_when_no_signal():
    signals = compute_player_signals(
        _player("X", "CM", 60),
        team_rank_underperformance=False,
        is_weak_position_group=False,
        value_percentile=None,
        caps_percentile=None,
        overall_percentile=None,
        team_median_overall=None,
        shallow_roster=False,
        is_top_contributor=False,
    )
    assert suggested_codex_action(signals) == "monitor_only"


def test_build_review_summary_ja_falls_back_when_no_flags():
    assert build_review_summary_ja([]) == ["現時点で能力値レビューを要する明確な指摘はありません。"]


def test_build_review_summary_ja_caps_at_three_lines():
    flags = ["team_rank_underperformance", "weak_position_group", "many_low_confidence_attributes", "shallow_roster_top_contributor"]
    assert len(build_review_summary_ja(flags)) <= 3


def test_build_candidate_row_shape():
    player = _player("BRA_X", "ST", 70, caps=60, market_value_eur=40_000_000)
    signals = compute_player_signals(
        player,
        team_rank_underperformance=True,
        is_weak_position_group=False,
        value_percentile=95.0,
        caps_percentile=10.0,
        overall_percentile=20.0,
        team_median_overall=75.0,
        shallow_roster=False,
        is_top_contributor=False,
    )
    row = build_candidate_row(player, signals)
    for field in (
        "player_id", "name", "name_ja", "primary_position", "age", "club_name", "caps",
        "national_team_goals", "market_value_eur", "source_citations", "current_overall",
        "position_overall", "starting_probability", "uncertainty", "data_confidence",
        "source_breakdown", "low_confidence_attributes", "qualitative_adjustments",
        "review_score", "review_band", "review_flags", "review_summary_ja", "suggested_codex_action",
    ):
        assert field in row


def test_build_team_row_excludes_players_with_no_signal():
    squad_gap_row = {
        "team_id": "CRO", "team_name": "Croatia", "fifa_rank": 10, "priority_score": 141.0,
        "rank_underperformance_flags": 0, "recommended_next_action": "monitor_only",
        "diagnostic_flags": [],
        "position_groups": {
            "GK": {"count": 1, "avg_overall": 50, "top_player": None},
            "DF": {"count": 1, "avg_overall": 60, "top_player": None},
            "MF": {"count": 1, "avg_overall": 60, "top_player": None},
            "FW": {"count": 1, "avg_overall": 60, "top_player": None},
        },
    }
    players = [_player("QUIET", "CM", 60, starting_probability=10, caps=20, market_value_eur=5_000_000)]
    row = build_team_row(squad_gap_row, players, {}, {}, {})
    assert row["rating_review_candidates"] == []


def test_build_team_row_includes_players_with_a_real_signal():
    squad_gap_row = {
        "team_id": "CRO", "team_name": "Croatia", "fifa_rank": 10, "priority_score": 141.0,
        "rank_underperformance_flags": 9, "recommended_next_action": "rating_data_review",
        "diagnostic_flags": [],
        "position_groups": {
            "GK": {"count": 0, "avg_overall": None, "top_player": None},
            "DF": {"count": 0, "avg_overall": None, "top_player": None},
            "MF": {"count": 1, "avg_overall": 60, "top_player": None},
            "FW": {"count": 0, "avg_overall": None, "top_player": None},
        },
    }
    players = [_player("UNDERRATED", "CM", 60)]
    overall_percentiles = {"UNDERRATED": 60.0}
    row = build_team_row(squad_gap_row, players, {}, {}, overall_percentiles)
    assert len(row["rating_review_candidates"]) == 1
    candidate = row["rating_review_candidates"][0]
    assert candidate["player_id"] == "UNDERRATED"
    assert "team_rank_underperformance" in candidate["review_flags"]


def test_build_report_respects_limit_and_includes_source_reports():
    squad_gap_report = {
        "generatedAt": "2026-06-23T00:00:00Z",
        "teams": [
            {"team_id": "CRO", "team_name": "Croatia", "fifa_rank": 10, "priority_score": 141.0, "rank_underperformance_flags": 9, "recommended_next_action": "rating_data_review", "diagnostic_flags": [], "position_groups": {}},
            {"team_id": "NED", "team_name": "Netherlands", "fifa_rank": 7, "priority_score": 129.5, "rank_underperformance_flags": 8, "recommended_next_action": "rating_data_review", "diagnostic_flags": [], "position_groups": {}},
            {"team_id": "ZZZ", "team_name": "Nowhere", "fifa_rank": 99, "priority_score": 0.0, "rank_underperformance_flags": 0, "recommended_next_action": "monitor_only", "diagnostic_flags": [], "position_groups": {}},
        ],
    }
    report = build_report(squad_gap_report, None, None, {}, limit=2)
    assert len(report["teams"]) == 2
    assert [t["team_id"] for t in report["teams"]] == ["CRO", "NED"]
    assert report["sourceReports"][0]["name"] == "squad_rating_gap_review"
    assert "generatedAt" in report
    assert "note" in report
    assert report["teamCount"] == 2
