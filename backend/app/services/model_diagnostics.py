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


def get_rating_decision_audit_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    report = _latest_report(reports_dir, "rating_decision_audit_*.json")
    if report is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "note": "能力値レビュー判断監査のレポートがまだ生成されていません。",
            "teamCount": 0,
            "bucketCounts": {},
            "teams": [],
        }
    return report


def get_model_calibration_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    comparison = _latest_report(reports_dir, "prediction_benchmark_comparison_rank75_*.json")
    if comparison is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "modelVersionBefore": None,
            "modelVersionAfter": None,
            "status": None,
            "overall": None,
            "watchlist": None,
            "bestSandboxVariantId": None,
            "note": "モデルキャリブレーションの比較レポートがまだ生成されていません。",
            "recommendations_ja": [],
        }

    after_report = _latest_report(reports_dir, "prediction_benchmark_rank75_*.json")
    sandbox = _latest_report(reports_dir, "aggregation_calibration_sandbox_*.json")
    evaluation = comparison.get("evaluation") or {}

    source_reports = [
        {"name": "prediction_benchmark_comparison_rank75", "generatedAt": comparison.get("afterGeneratedAt")},
    ]
    if after_report:
        source_reports.append({"name": "prediction_benchmark_rank75", "generatedAt": after_report.get("generatedAt")})
    if sandbox:
        source_reports.append({"name": "aggregation_calibration_sandbox", "generatedAt": sandbox.get("generatedAt")})

    return {
        "generatedAt": comparison.get("afterGeneratedAt"),
        "sourceReports": source_reports,
        "modelVersionBefore": comparison.get("modelVersionBefore"),
        "modelVersionAfter": comparison.get("modelVersionAfter"),
        "status": evaluation.get("status"),
        "overall": comparison.get("overall"),
        "watchlist": {
            "watchlist_implausible_reduction": evaluation.get("watchlist_implausible_reduction"),
            "teams": comparison.get("watchlistTeams") or [],
        },
        "bestSandboxVariantId": (sandbox or {}).get("bestVariantId"),
        "note": (
            "FIFAランクとローカル能力値(チーム強さ)の混合比率を調整したモデル"
            f"({comparison.get('modelVersionAfter')})の検証結果です。"
            "能力値データが圧縮されている注目チームで、ランク差に対して説明しにくい本命判定の件数が"
            "ベンチマーク上で減少しました。これは検証上の改善であり、試合予測そのものの正しさを保証するものではありません。"
        ),
        "recommendations_ja": [
            "この改善はベンチマーク上の結果であり、実際の試合結果の正しさを保証するものではありません。",
            "さらなるフォーミュラ調整も、before/afterのベンチマーク比較を必須としてください。",
        ],
    }


def get_source_provenance_audit_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    report = _latest_report(reports_dir, "source_provenance_audit_*.json")
    if report is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "note": "能力値レビュー候補の出典監査レポートがまだ生成されていません。",
            "seedSourceSummary": {
                "seed_player_count": 0,
                "players_with_source_risk": 0,
                "marker_counts": {},
                "severity_counts": {},
                "top_risky_seed_players": [],
            },
            "decisionCandidateCount": 0,
            "clearLaterProposalCandidateCount": 0,
            "sourceReviewCandidateCount": 0,
            "teamCount": 0,
            "teams": [],
            "recommendations_ja": [
                "能力値を変更する前に、候補の出典監査レポートを生成してください。",
            ],
        }
    return report
