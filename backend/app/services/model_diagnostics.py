"""Read-only model diagnostics summary: serves the latest
team_data_review_plan_*.json (Spec 011), squad_rating_gap_review_*.json
(Spec 012), manager_tactical_data_audit_*.json (Spec 013), and
rating_review_workbench_*.json (Spec 014) reports produced by their
respective build scripts. Never computes or mutates anything itself -- if a
report is missing, returns a calm empty state rather than failing.
"""

from __future__ import annotations

import json
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"


def _latest_report(reports_dir: Path, pattern: str) -> dict | None:
    if not reports_dir.exists():
        return None
    matches = sorted(reports_dir.glob(pattern))
    if not matches:
        return None
    return json.loads(matches[-1].read_text(encoding="utf-8"))


def get_team_review_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    report = _latest_report(reports_dir, "team_data_review_plan_*.json")
    if report is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "note": "チームデータレビューのレポートがまだ生成されていません。",
            "teamCount": 0,
            "teams": [],
        }
    return report


def get_squad_gap_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    report = _latest_report(reports_dir, "squad_rating_gap_review_*.json")
    if report is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "note": "スカッド評価ギャップのレポートがまだ生成されていません。",
            "teams": [],
        }
    return report


def get_manager_tactical_trust_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    report = _latest_report(reports_dir, "manager_tactical_data_audit_*.json")
    if report is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "note": "監督・戦術データの信頼性監査レポートがまだ生成されていません。",
            "teamCount": 0,
            "bandCounts": {"high": 0, "medium": 0, "low": 0},
            "teams": [],
        }
    return report


def get_rating_review_workbench_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    report = _latest_report(reports_dir, "rating_review_workbench_*.json")
    if report is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "note": "能力値レビュー作業台のレポートがまだ生成されていません。",
            "teamCount": 0,
            "teams": [],
        }
    return report
