import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_substitution_model_gap_audit import build_engine_capabilities, build_gap_rows, build_report


def test_engine_capabilities_reflect_substitution_profile_prototype():
    capabilities = build_engine_capabilities()

    assert capabilities["hasSubstitutionEvents"] is True
    # Spec 018 Phase 5 added the substitution_profile mechanism -- these are
    # now True at the engine level, even though no team has real data yet.
    assert capabilities["hasManagerSpecificSubstitutionParameters"] is True
    assert capabilities["hasScoreStateSubstitutionBias"] is True
    assert capabilities["hasPositionSpecificSubstitutionPreferences"] is True
    assert capabilities["anyTeamUsesNonNeutralProfile"] is False
    assert capabilities["neutralSubstitutionProfileFields"]
    assert capabilities["maxSubs"] == 3
    assert capabilities["subWindow"] == {"startMinute": 55, "endMinute": 88}
    assert capabilities["selectionRule"] == "most_fatigued_matching_position_best_overall_bench"


def test_gap_rows_keep_future_fields_separate_from_current_seed_values():
    rows = build_gap_rows()

    assert len(rows) >= 4
    assert {row["gapId"] for row in rows} >= {
        "manager_specific_timing",
        "score_state_intent",
        "role_and_position_preference",
        "bench_trust_and_depth",
    }
    for row in rows:
        assert row["futureFieldCandidates"]
        assert "seed" not in row["recommendedNextAction"].lower()


def test_report_is_read_only_and_has_japanese_user_copy():
    report = build_report()

    assert report["gapCount"] == len(report["gaps"])
    assert report["summary"]["safeCurrentAction"] == "read_only_candidate_collection"
    assert report["summary"]["currentModelHasManagerSpecificSubstitutions"] is False
    assert report["summary"]["substitutionProfileMechanismImplemented"] is True
    assert "交代" in report["note"]
    assert any("before/after" in line for line in report["recommendationsJa"])
