"""Read-only model diagnostics summary: serves the latest
team_data_review_plan_*.json report (Spec 011) produced by
scripts/build_team_data_review_plan.py. Never computes or mutates
anything itself -- if the report is missing, returns a calm empty state
rather than failing.
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
