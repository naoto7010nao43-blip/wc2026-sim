"""Build a read-only local release readiness report.

This script summarizes whether the repository is ready for a manual production
push according to docs/codex/PRODUCTION_RELEASE_CHECKLIST.md. It does not run
the expensive test suite; it records structural release blockers such as an
active Ready spec, dirty git status, missing diagnostics reports, and the
latest model benchmark comparison state.

Read-only: does not mutate seed data, ratings, formulas, or prediction
behavior.

Usage:
  ./venv/Scripts/python.exe scripts/build_release_readiness_report.py
  ./venv/Scripts/python.exe scripts/build_release_readiness_report.py --check-only
  ./venv/Scripts/python.exe scripts/build_release_readiness_report.py --check-only --fail-on-blockers
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from check_data_freshness import check_freshness

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
REPORTS_DIR = BACKEND_DIR / "reports"
SEED_DIR = BACKEND_DIR / "data" / "seed"
CURRENT_TASK_PATH = REPO_ROOT / "docs" / "specs" / "CURRENT_TASK.md"

REQUIRED_REPORT_PATTERNS = (
    "prediction_benchmark_baseline_*.json",
    "prediction_benchmark_v1_order_neutral_*.json",
    "prediction_benchmark_rank75_*.json",
    "prediction_benchmark_rank75_order_neutral_*.json",
    "prediction_benchmark_comparison_rank75_*.json",
    "prediction_benchmark_comparison_rank75_order_neutral_*.json",
    "simulation_accuracy_audit_*.json",
    "team_data_review_plan_*.json",
    "squad_rating_gap_review_*.json",
    "rating_review_workbench_*.json",
    "rating_decision_audit_*.json",
    "source_provenance_audit_*.json",
    "simulation_stability_audit_*.json",
    "substitution_model_gap_audit_*.json",
    "external_data_verification_candidates_*.json",
    "external_data_verification_validation_*.json",
    "external_data_decision_queue_*.json",
    "external_source_traceability_audit_*.json",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report(pattern: str, reports_dir: Path = REPORTS_DIR) -> Path | None:
    matches = sorted(reports_dir.glob(pattern))
    return matches[-1] if matches else None


def git_status_short(repo_root: Path = REPO_ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def current_task_state(text: str) -> dict:
    active_ready = "## Active Claude Code Task" in text and "Ready:" in text
    awaiting = "None. Awaiting the next Codex-authored Ready spec" in text
    completed_spec = None
    for sentence in text.replace("\n", " ").split("."):
        sentence = sentence.strip()
        if sentence.startswith("Spec ") and " is complete" in sentence:
            completed_spec = sentence
            break
    return {
        "hasActiveReadyTask": active_ready,
        "awaitingNextSpec": awaiting,
        "latestCompletedSpecText": completed_spec,
    }


def required_report_status(reports_dir: Path = REPORTS_DIR) -> list[dict]:
    rows = []
    for pattern in REQUIRED_REPORT_PATTERNS:
        path = latest_report(pattern, reports_dir)
        rows.append({
            "pattern": pattern,
            "present": path is not None,
            "path": None if path is None else display_path(path),
        })
    return rows


def benchmark_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    comparison_path = latest_report("prediction_benchmark_comparison_rank75_order_neutral_*.json", reports_dir)
    if comparison_path is None:
        comparison_path = latest_report("prediction_benchmark_comparison_rank75_*.json", reports_dir)
    if comparison_path is None:
        return {
            "present": False,
            "status": "missing",
            "benchmarkMethod": None,
            "watchlistImplausibleReduction": None,
            "overallImplausibleFavoriteCountDelta": None,
            "averageFavoriteWinPctDelta": None,
        }
    comparison = load_json(comparison_path)
    evaluation = comparison.get("evaluation") or {}
    overall = comparison.get("overall") or {}
    return {
        "present": True,
        "path": display_path(comparison_path),
        "status": evaluation.get("status"),
        "benchmarkMethod": comparison.get("benchmarkMethod"),
        "watchlistImplausibleReduction": evaluation.get("watchlist_implausible_reduction"),
        "overallImplausibleFavoriteCountDelta": overall.get("implausible_favorite_count_delta"),
        "averageFavoriteWinPctDelta": overall.get("average_favorite_win_pct_delta"),
    }


def model_version_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    rank75_path = latest_report("prediction_benchmark_rank75_order_neutral_*.json", reports_dir)
    if rank75_path is None:
        rank75_path = latest_report("prediction_benchmark_rank75_*.json", reports_dir)
    baseline_path = latest_report("prediction_benchmark_v1_order_neutral_*.json", reports_dir)
    if baseline_path is None:
        baseline_path = latest_report("prediction_benchmark_baseline_*.json", reports_dir)
    return {
        "baselineModelVersion": None if baseline_path is None else load_json(baseline_path).get("modelVersion"),
        "currentModelVersion": None if rank75_path is None else load_json(rank75_path).get("modelVersion"),
    }


def release_blockers(
    *,
    current_task: dict,
    git_status: list[str],
    reports: list[dict],
    benchmark: dict,
) -> list[str]:
    blockers = []
    if current_task["hasActiveReadyTask"]:
        blockers.append("CURRENT_TASK.md still lists an active Ready task.")
    if git_status:
        blockers.append("git status is not clean.")
    missing = [row["pattern"] for row in reports if not row["present"]]
    if missing:
        blockers.append("required report files are missing: " + ", ".join(missing))
    if benchmark.get("status") != "pass":
        blockers.append("rank75 benchmark comparison is not passing.")
    return blockers


def freshness_warning_label(message: str) -> str:
    if message.startswith("FIFA Official Squad feed: stale"):
        return "公式スカッドfeedの最終確認が鮮度ポリシーを超過しています。公開は可能ですが、能力値・戦術値の追加反映前に再確認してください。"
    if message.startswith("Existing project seed data"):
        return "既存seedデータ（経歴・市場価値・出典）の最終確認が鮮度ポリシーを超過しています。公開は可能ですが、精度改善作業では最新ソースを優先してください。"
    if message.startswith("metadata.lastUpdated"):
        return "seedメタデータの最終更新日が鮮度ポリシーを超過しています。"
    return f"データ鮮度注意: {message}"


def non_blocking_warnings(seed_dir: Path = SEED_DIR) -> list[str]:
    metadata_path = seed_dir / "metadata.json"
    if not metadata_path.exists():
        return ["metadata.jsonが見つからないため、データ鮮度を確認できません。"]
    metadata = load_json(metadata_path)
    return [
        freshness_warning_label(finding["message"])
        for finding in check_freshness(metadata)
        if finding.get("level") in {"critical", "warning"}
    ]


def build_report(
    *,
    current_task_text: str | None = None,
    git_status: list[str] | None = None,
    reports_dir: Path = REPORTS_DIR,
    seed_dir: Path = SEED_DIR,
) -> dict:
    current_task_text = current_task_text if current_task_text is not None else CURRENT_TASK_PATH.read_text(encoding="utf-8")
    git_status = git_status if git_status is not None else git_status_short()
    task = current_task_state(current_task_text)
    reports = required_report_status(reports_dir)
    benchmark = benchmark_summary(reports_dir)
    model_versions = model_version_summary(reports_dir)
    warnings = non_blocking_warnings(seed_dir)
    blockers = release_blockers(
        current_task=task,
        git_status=git_status,
        reports=reports,
        benchmark=benchmark,
    )
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Manual production release readiness snapshot. This report is read-only and does not run tests; "
            "use scripts/pre_release_check.ps1 for the executable verification gate."
        ),
        "readyForManualPush": not blockers,
        "blockers": blockers,
        "nonBlockingWarnings": warnings,
        "currentTask": task,
        "gitStatusShort": git_status,
        "modelVersions": model_versions,
        "rank75Benchmark": benchmark,
        "requiredReports": reports,
        "requiredCommands": [
            ".\\scripts\\pre_release_check.ps1",
            ".\\scripts\\post_deploy_smoke.ps1 -FrontendBaseUrl \"https://wc2026-sim-ten.vercel.app\" -BackendBaseUrl \"<production-backend-url>\"",
            ".\\scripts\\post_deploy_content_smoke.ps1 -FrontendBaseUrl \"https://wc2026-sim-ten.vercel.app\" -BackendBaseUrl \"<production-backend-url>\"",
            ".\\scripts\\post_deploy_browser_smoke.ps1 -FrontendBaseUrl \"https://wc2026-sim-ten.vercel.app\" -BackendBaseUrl \"<production-backend-url>\"",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Print the release readiness result without writing backend/reports.",
    )
    parser.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help="Exit with status 1 when release blockers are present.",
    )
    args = parser.parse_args()

    report = build_report()
    if not args.check_only:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = REPORTS_DIR / f"release_readiness_{date_str}.json"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {out_path}")

    print(f"readyForManualPush={report['readyForManualPush']}")
    for blocker in report["blockers"]:
        print(f"  - {blocker}")
    return 1 if args.fail_on_blockers and report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
