import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_squad_rating_gap_review import (
    build_diagnostic_flags,
    build_position_groups,
    build_rating_distribution,
    build_report,
    build_review_summary,
    build_team_row,
    build_trust_profile,
    median,
    position_group_for,
    recommended_next_action,
)


def _player(name, position, overall, starting_probability=70.0, data_confidence="estimated", uncertainty=5.0, low_conf=None):
    return {
        "player_id": f"X_{name}",
        "name": name,
        "primary_position": position,
        "overall": overall,
        "starting_probability": starting_probability,
        "data_confidence": data_confidence,
        "uncertainty": uncertainty,
        "low_confidence_attributes": low_conf or [],
    }


def test_median_handles_empty_and_normal_lists():
    assert median([]) is None
    assert median([10, 20, 30]) == 20
    assert median([10, 20]) == 15.0


def test_position_group_for_maps_known_and_unknown_positions():
    assert position_group_for("GK") == "GK"
    assert position_group_for("CB") == "DF"
    assert position_group_for("CM") == "MF"
    assert position_group_for("ST") == "FW"
    assert position_group_for("UNKNOWN") == "MF"


def test_build_position_groups_computes_averages_and_top_player():
    players = [_player("A", "CB", 60), _player("B", "CB", 70), _player("C", "ST", 80)]
    groups = build_position_groups(players)
    assert groups["DF"]["count"] == 2
    assert groups["DF"]["avg_overall"] == 65.0
    assert groups["DF"]["top_player"] == {"name": "B", "overall": 70}
    assert groups["FW"]["count"] == 1
    assert groups["GK"]["count"] == 0
    assert groups["GK"]["top_player"] is None


def test_build_rating_distribution_counts_thresholds():
    players = [_player("A", "GK", 55), _player("B", "CB", 72), _player("C", "ST", 80)]
    dist = build_rating_distribution(players)
    assert dist["min_overall"] == 55
    assert dist["max_overall"] == 80
    assert dist["median_overall"] == 72
    assert dist["count_overall_gte_75"] == 1
    assert dist["count_overall_gte_70"] == 2
    assert dist["count_overall_lt_60"] == 1
    assert dist["top_5_players"][0]["name"] == "C"


def test_build_trust_profile_counts_confidence_and_coverage():
    players = [
        _player("A", "GK", 55, data_confidence="official", low_conf=["passing"]),
        _player("B", "CB", 60, data_confidence="estimated", low_conf=["passing", "tackling"]),
    ]
    official_lookup = {"X_A": {"clubName": "Foo FC", "caps": None, "nationalTeamGoals": 0, "heightCm": 180, "dateOfBirth": None}}
    profile = build_trust_profile(players, official_lookup)
    assert profile["data_confidence_counts"] == {"official": 1, "estimated": 1}
    assert profile["low_confidence_attribute_count"] == 3
    assert profile["official_profile_coverage"]["club"] == 1
    assert profile["official_profile_coverage"]["caps"] == 0
    assert profile["official_profile_coverage"]["goals"] == 1
    assert profile["official_profile_coverage"]["dateOfBirth"] == 0


def test_diagnostic_flags_shallow_roster_and_thin_depth():
    players = [_player("A", "GK", 55), _player("B", "ST", 60)]
    trust_profile = {"official_profile_coverage": {"club": 0, "caps": 0, "goals": 0, "height": 0, "dateOfBirth": 0}, "low_confidence_attribute_count": 0}
    flags = build_diagnostic_flags(seed_roster_size=12, position_groups=build_position_groups(players), trust_profile=trust_profile, roster_recon={})
    assert "shallow_seed_roster" in flags
    assert "thin_defensive_depth" in flags
    assert "low_official_profile_coverage" in flags


def test_diagnostic_flags_uniform_baseline_low_confidence_count_does_not_flag():
    # Every player in the real dataset carries exactly 10 "low confidence"
    # attributes -- a uniform pipeline-wide baseline, not per-team
    # variance. A team sitting exactly at that baseline must NOT be
    # flagged, or every single team in the dataset would be flagged.
    players = [_player(f"P{i}", "CB", 65) for i in range(14)]
    trust_profile = {
        "official_profile_coverage": {"club": 14, "caps": 14, "goals": 14, "height": 14, "dateOfBirth": 14},
        "low_confidence_attribute_count": 14 * 10,
    }
    flags = build_diagnostic_flags(
        seed_roster_size=14, position_groups=build_position_groups(players), trust_profile=trust_profile, roster_recon={},
    )
    assert "many_low_confidence_attributes" not in flags


def test_diagnostic_flags_no_issues_for_deep_well_covered_roster():
    players = [_player(f"P{i}", pos, 65) for i, pos in enumerate(["GK", "CB", "CB", "LB", "RB", "CM", "CM", "ST", "ST", "RW", "LW"] * 2)]
    full_coverage = {"club": len(players), "caps": len(players), "goals": len(players), "height": len(players), "dateOfBirth": len(players)}
    trust_profile = {"official_profile_coverage": full_coverage, "low_confidence_attribute_count": 0}
    flags = build_diagnostic_flags(
        seed_roster_size=len(players), position_groups=build_position_groups(players), trust_profile=trust_profile, roster_recon={},
    )
    assert flags == []


def test_recommended_action_rank_underperformance_is_rating_data_review():
    # CRO/NED/POR-like: rank-underperformance flags present.
    action = recommended_next_action(rank_underperformance_flags=9, diagnostic_flags=[], roster_recon={})
    assert action == "rating_data_review"


def test_recommended_action_low_coverage_alone_is_also_rating_data_review():
    action = recommended_next_action(rank_underperformance_flags=0, diagnostic_flags=["low_official_profile_coverage"], roster_recon={})
    assert action == "rating_data_review"


def test_recommended_action_add_candidates_only_is_not_rating_data_review():
    # A team with only roster add-candidates and no rank-underperformance
    # signal must NOT be automatically treated as a rating-data issue.
    action = recommended_next_action(
        rank_underperformance_flags=0,
        diagnostic_flags=["shallow_seed_roster"],
        roster_recon={"high_confidence_add_candidate_count": 10, "other_add_candidate_count": 5, "ambiguous_pair_count": 0, "likely_stale_seed_player_count": 0},
    )
    assert action != "rating_data_review"
    assert action == "roster_reconciliation_review"


def test_recommended_action_ambiguous_pairs_routes_to_name_matching():
    action = recommended_next_action(0, [], {"ambiguous_pair_count": 3})
    assert action == "name_matching_review"


def test_recommended_action_nothing_flagged_is_monitor_only():
    assert recommended_next_action(0, [], {}) == "monitor_only"


def test_build_review_summary_falls_back_when_nothing_flagged():
    assert build_review_summary(0, [], {}, 16) == ["特筆すべき指摘はありません。継続的なモニタリングのみで十分です。"]


def test_build_review_summary_caps_at_four_bullets():
    flags = ["low_official_profile_coverage", "many_low_confidence_attributes", "shallow_seed_roster", "thin_defensive_depth", "thin_attacking_depth"]
    summary = build_review_summary(5, flags, {"likely_stale_seed_player_count": 2, "ambiguous_pair_count": 1}, 12)
    assert len(summary) <= 4


def test_build_team_row_full_shape():
    review_row = {"team_id": "CRO", "team_name": "Croatia", "fifa_rank": 10, "priority_score": 141.0, "rank_underperformance_flags": 9, "seed_roster_size": 14}
    players = [_player("A", "GK", 55), _player("B", "CB", 60)]
    row = build_team_row(review_row, players, {}, roster_row=None)
    assert row["team_id"] == "CRO"
    assert row["recommended_next_action"] == "rating_data_review"
    assert row["roster_reconciliation"]["ambiguous_pair_count"] == 0


def test_build_report_respects_limit_and_includes_source_reports():
    review_plan = {
        "generatedAt": "2026-06-23T00:00:00Z",
        "teams": [
            {"team_id": "CRO", "team_name": "Croatia", "fifa_rank": 10, "priority_score": 141.0, "rank_underperformance_flags": 9, "seed_roster_size": 14},
            {"team_id": "NED", "team_name": "Netherlands", "fifa_rank": 7, "priority_score": 129.5, "rank_underperformance_flags": 8, "seed_roster_size": 16},
            {"team_id": "ZZZ", "team_name": "Nowhere", "fifa_rank": 99, "priority_score": 0.0, "rank_underperformance_flags": 0, "seed_roster_size": 12},
        ],
    }
    report = build_report(review_plan, None, {}, {}, limit=2)
    assert len(report["teams"]) == 2
    assert [t["team_id"] for t in report["teams"]] == ["CRO", "NED"]
    assert report["sourceReports"][0]["name"] == "team_data_review_plan"
    assert "generatedAt" in report
    assert "note" in report
