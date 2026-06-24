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
SEED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "seed"


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


def get_release_readiness_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    report = _latest_report(reports_dir, "release_readiness_*.json")
    if report is None:
        return {
            "generatedAt": None,
            "note": "本番反映可否レポートがまだ生成されていません。",
            "readyForManualPush": False,
            "blockers": ["release readiness report is missing"],
            "currentTask": None,
            "gitStatusShort": [],
            "modelVersions": None,
            "rank75Benchmark": None,
            "requiredReports": [],
            "requiredCommands": [],
        }
    return {
        **report,
        "note": (
            "本番反映に必要なローカル診断レポートの要約です。"
            "この表示は読み取り専用で、テスト実行やpushは行いません。"
        ),
    }


def get_external_data_verification_summary(reports_dir: Path = REPORTS_DIR, seed_dir: Path = SEED_DIR) -> dict:
    validation = _latest_report(reports_dir, "external_data_verification_validation_*.json")
    candidates = _latest_report(reports_dir, "external_data_verification_candidates_*.json")
    decision_queue = _latest_report(reports_dir, "external_data_decision_queue_*.json")
    source_traceability = _latest_report(reports_dir, "external_source_traceability_audit_*.json")
    total_team_count = 48
    teams_path = seed_dir / "teams.json"
    if teams_path.exists():
        total_team_count = len(json.loads(teams_path.read_text(encoding="utf-8")))

    if validation is None:
        return {
            "generatedAt": None,
            "note": "外部データ検証レポートがまだ生成されていません。",
            "valid": False,
            "errorCount": 0,
            "warningCount": 0,
            "candidateCount": 0,
            "coveredTeamCount": 0,
            "totalTeamCount": total_team_count,
            "remainingTeamCount": total_team_count,
            "scope": None,
            "categoryCounts": {},
            "impactCounts": {},
            "useTierCounts": {},
            "teamSignalBandCounts": {},
            "sparseTeamIds": [],
            "topTeamPriorities": [],
            "teamSignalProfiles": [],
            "decisionQueue": None,
            "sourceTraceability": None,
            "warnings": [],
            "errors": [],
        }

    scope = (candidates or {}).get("scope") or {}
    covered = scope.get("coveredTeams") or []
    remaining = scope.get("remainingUnresearchedTeams") or []
    decision_queue_summary = None
    if decision_queue is not None:
        decision_queue_summary = {
            "generatedAt": decision_queue.get("generatedAt"),
            "currentFieldReviewCount": decision_queue.get("currentFieldReviewCount", 0),
            "warningHoldCount": decision_queue.get("warningHoldCount", 0),
            "futureEngineCount": decision_queue.get("futureEngineCount", 0),
            "provisionalContextCount": decision_queue.get("provisionalContextCount", 0),
            "bucketCounts": decision_queue.get("bucketCounts", {}),
            "topTeams": (decision_queue.get("teams") or [])[:8],
        }
    source_traceability_summary = None
    if source_traceability is not None:
        source_traceability_summary = {
            "generatedAt": source_traceability.get("generatedAt"),
            "severity": source_traceability.get("severity", "unknown"),
            "candidateCount": source_traceability.get("candidateCount", 0),
            "sourceReferenceCount": source_traceability.get("sourceReferenceCount", 0),
            "missingUrlSourceCount": source_traceability.get("missingUrlSourceCount", 0),
            "candidateMissingResolvableUrlCount": source_traceability.get("candidateMissingResolvableUrlCount", 0),
            "missingObservedDateSourceCount": source_traceability.get("missingObservedDateSourceCount", 0),
            "recommendationsJa": source_traceability.get("recommendationsJa", []),
        }
    return {
        "generatedAt": (candidates or {}).get("generatedAt"),
        "note": (
            "外部調査候補をCodexレビュー前に整理した読み取り専用サマリーです。"
            "候補は直接seedや能力値へ反映せず、信頼度と用途別に保留します。"
        ),
        "valid": validation.get("valid", False),
        "errorCount": validation.get("errorCount", 0),
        "warningCount": validation.get("warningCount", 0),
        "candidateCount": validation.get("candidateCount", 0),
        "coveredTeamCount": validation.get("coveredTeamCount", len(covered)),
        "totalTeamCount": total_team_count,
        "remainingTeamCount": len(remaining) if remaining else max(0, total_team_count - len(covered)),
        "scope": {
            "coveredTeams": covered,
            "remainingUnresearchedTeams": remaining,
        },
        "categoryCounts": validation.get("categoryCounts", {}),
        "impactCounts": validation.get("impactCounts", {}),
        "useTierCounts": validation.get("useTierCounts", {}),
        "teamSignalBandCounts": validation.get("teamSignalBandCounts", {}),
        "sparseTeamIds": validation.get("sparseTeamIds", []),
        "topTeamPriorities": validation.get("topTeamPriorities", []),
        "teamSignalProfiles": validation.get("teamSignalProfiles", []),
        "decisionQueue": decision_queue_summary,
        "sourceTraceability": source_traceability_summary,
        "warnings": validation.get("warnings", []),
        "errors": validation.get("errors", []),
    }


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
    comparison = _latest_report(reports_dir, "prediction_benchmark_comparison_rank75_order_neutral_*.json")
    comparison_report_name = "prediction_benchmark_comparison_rank75_order_neutral"
    if comparison is None:
        comparison = _latest_report(reports_dir, "prediction_benchmark_comparison_rank75_*.json")
        comparison_report_name = "prediction_benchmark_comparison_rank75"
    if comparison is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "modelVersionBefore": None,
            "modelVersionAfter": None,
            "status": None,
            "benchmarkMethod": None,
            "overall": None,
            "watchlist": None,
            "bestSandboxVariantId": None,
            "note": "モデルキャリブレーションの比較レポートがまだ生成されていません。",
            "recommendations_ja": [],
        }

    after_report = _latest_report(reports_dir, "prediction_benchmark_rank75_order_neutral_*.json")
    after_report_name = "prediction_benchmark_rank75_order_neutral"
    if after_report is None:
        after_report = _latest_report(reports_dir, "prediction_benchmark_rank75_*.json")
        after_report_name = "prediction_benchmark_rank75"
    sandbox = _latest_report(reports_dir, "aggregation_calibration_sandbox_*.json")
    evaluation = comparison.get("evaluation") or {}
    benchmark_method = comparison.get("benchmarkMethod")

    source_reports = [
        {"name": comparison_report_name, "generatedAt": comparison.get("generatedAt") or comparison.get("afterGeneratedAt")},
    ]
    if after_report:
        source_reports.append({"name": after_report_name, "generatedAt": after_report.get("generatedAt")})
    if sandbox:
        source_reports.append({"name": "aggregation_calibration_sandbox", "generatedAt": sandbox.get("generatedAt")})

    return {
        "generatedAt": comparison.get("generatedAt") or comparison.get("afterGeneratedAt"),
        "sourceReports": source_reports,
        "modelVersionBefore": comparison.get("modelVersionBefore"),
        "modelVersionAfter": comparison.get("modelVersionAfter"),
        "status": evaluation.get("status"),
        "benchmarkMethod": benchmark_method,
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


def get_simulation_stability_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    report = _latest_report(reports_dir, "simulation_stability_audit_*.json")
    if report is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "modelVersion": None,
            "note": "モンテカルロ安定性監査のレポートがまだ生成されていません。",
            "scope": None,
            "samples": [],
            "comparisons": [],
            "summary": None,
        }
    return report


def get_substitution_model_gap_summary(reports_dir: Path = REPORTS_DIR) -> dict:
    report = _latest_report(reports_dir, "substitution_model_gap_audit_*.json")
    if report is None:
        return {
            "generatedAt": None,
            "sourceReports": [],
            "note": "選手交代モデルのギャップ監査レポートがまだ生成されていません。",
            "engineCapabilities": None,
            "gapCount": 0,
            "gaps": [],
            "recommendationsJa": [],
            "summary": None,
        }
    return report


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
