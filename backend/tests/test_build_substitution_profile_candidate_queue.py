import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_substitution_profile_candidate_queue import build_report, infer_profile_signals


def test_infers_profile_signals_without_creating_numeric_values():
    signals = infer_profile_signals(
        "Moriyasu used all 5 substitution slots, with a super-sub scoring a late equalizer."
    )

    assert "bench_trust" in signals
    assert "trailing_aggression" in signals
    assert all(not signal.endswith("_value") for signal in signals)


def test_report_groups_future_engine_substitution_candidates():
    report = build_report()

    assert report["candidateCount"] == 37
    assert report["teamCount"] > 0
    assert report["readyTeamCount"] > 0
    assert report["signalCounts"]
    assert "交代傾向" in report["note"]
    assert any("before/after" in line for line in report["recommendationsJa"])


def test_team_rows_stay_read_only_and_keep_evidence_text():
    report = build_report()
    row = next(team for team in report["teams"] if team["teamId"] == "JPN")

    assert row["candidateCount"] >= 1
    assert row["readinessBand"] in {
        "profile_review_ready",
        "needs_more_match_evidence",
        "hold_for_source_review",
        "low_confidence_context",
    }
    assert row["suggestedProfileSignals"]
    assert row["evidenceSummaries"]
    assert "seed" not in row["recommendedHandlingJa"].lower()
