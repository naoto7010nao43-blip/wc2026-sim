import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_release_readiness_report import (
    benchmark_summary,
    build_report,
    current_task_state,
    release_blockers,
    required_report_status,
)


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_current_task_state_detects_active_ready_task():
    state = current_task_state(
        """
## Active Claude Code Task

Ready:
- docs/specs/016-model-calibration-transparency.md
"""
    )
    assert state["hasActiveReadyTask"] is True
    assert state["awaitingNextSpec"] is False


def test_current_task_state_detects_awaiting_state():
    state = current_task_state(
        "None. Awaiting the next Codex-authored Ready spec. Spec 016 is complete."
    )
    assert state["hasActiveReadyTask"] is False
    assert state["awaitingNextSpec"] is True
    assert state["latestCompletedSpecText"] == "Spec 016 is complete"


def test_required_report_status_marks_missing_and_present(tmp_path):
    write_json(tmp_path / "prediction_benchmark_baseline_2026-06-23.json", {"modelVersion": "poisson-v1"})
    rows = required_report_status(tmp_path)
    baseline = next(row for row in rows if row["pattern"] == "prediction_benchmark_baseline_*.json")
    comparison = next(row for row in rows if row["pattern"] == "prediction_benchmark_comparison_rank75_*.json")
    assert baseline["present"] is True
    assert comparison["present"] is False


def test_benchmark_summary_reads_rank75_comparison(tmp_path):
    write_json(
        tmp_path / "prediction_benchmark_comparison_rank75_2026-06-23.json",
        {
            "evaluation": {"status": "pass", "watchlist_implausible_reduction": 5},
            "overall": {"implausible_favorite_count_delta": -6, "average_favorite_win_pct_delta": 0.7},
        },
    )
    summary = benchmark_summary(tmp_path)
    assert summary["present"] is True
    assert summary["status"] == "pass"
    assert summary["watchlistImplausibleReduction"] == 5


def test_release_blockers_include_active_task_dirty_status_missing_report_and_failed_benchmark():
    blockers = release_blockers(
        current_task={"hasActiveReadyTask": True},
        git_status=[" M file.py"],
        reports=[{"pattern": "missing.json", "present": False}],
        benchmark={"status": "review"},
    )
    assert len(blockers) == 4


def test_build_report_not_ready_when_task_active(tmp_path):
    write_json(
        tmp_path / "prediction_benchmark_comparison_rank75_2026-06-23.json",
        {
            "evaluation": {"status": "pass", "watchlist_implausible_reduction": 5},
            "overall": {"implausible_favorite_count_delta": -6, "average_favorite_win_pct_delta": 0.7},
        },
    )
    write_json(tmp_path / "prediction_benchmark_baseline_2026-06-23.json", {"modelVersion": "poisson-v1"})
    write_json(tmp_path / "prediction_benchmark_rank75_2026-06-23.json", {"modelVersion": "poisson-v2-rank75"})
    report = build_report(
        current_task_text="## Active Claude Code Task\n\nReady:\n- docs/specs/016.md",
        git_status=[],
        reports_dir=tmp_path,
    )
    assert report["readyForManualPush"] is False
    assert "CURRENT_TASK.md still lists an active Ready task." in report["blockers"]
    assert report["rank75Benchmark"]["status"] == "pass"
