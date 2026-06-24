"""Build a read-only decision queue from external verification candidates.

This report turns a validated external research file into Codex-facing review
queues. It does not apply seed, rating, manager, tactical, or formula changes.
The goal is to preserve weak/sparse signal while preventing sourced-but-risky
claims from being treated as automatic data changes.

Usage:
  ./venv/Scripts/python.exe scripts/build_external_data_decision_queue.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_external_data_verification_report import (
    EXISTING_FIELD_CATEGORIES,
    FUTURE_ONLY_CATEGORIES,
    RECOGNIZED_CATEGORIES,
    candidate_text,
    load_json,
    validate_candidate,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports"


def latest_report(pattern: str, reports_dir: Path = REPORTS_DIR) -> Path | None:
    matches = sorted(reports_dir.glob(pattern))
    return matches[-1] if matches else None


def source_report_ref(path: Path | None, name: str) -> dict:
    if path is None:
        return {"name": name, "path": None}
    return {"name": name, "path": str(path.relative_to(BACKEND_DIR))}


def handling_ja(row: dict) -> str:
    if row["bucket"] == "current_field_review":
        return "既存フィールドに対応します。出典を再確認したうえで、別specでseed/能力値変更候補にできます。"
    if row["bucket"] == "warning_hold":
        return "構造上は有用ですが警告があります。反映候補にする前に追加確認してください。"
    if row["bucket"] == "future_engine":
        return "現エンジンに直接の反映先がありません。将来の選手交代・監督傾向仕様の候補として保留します。"
    if row["bucket"] == "provisional_context":
        return "判断材料として残しますが、単独ではseed/能力値変更に使いません。"
    return "情報量が薄いため、追跡用に残しつつ直接の変更判断には使いません。"


def queue_bucket(category: str, score: dict, warnings: list[str], errors: list[str]) -> str:
    if errors or warnings:
        return "warning_hold"
    if category in FUTURE_ONLY_CATEGORIES or score.get("useTier") == "future_engine_candidate":
        return "future_engine"
    if (
        score.get("useTier") == "ready_for_codex_review"
        and score.get("impactBand") in {"high", "medium"}
        and score.get("mapsTo") in EXISTING_FIELD_CATEGORIES.get(category, set())
    ):
        return "current_field_review"
    if score.get("useTier") in {"provisional_context", "review_question"}:
        return "provisional_context"
    return "insufficient_detail"


def build_decision_queue(candidate_report: dict, validation_report: dict, generated_at: str | None = None) -> dict:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    queued: list[dict] = []

    for team in candidate_report.get("teams") or []:
        team_id = str(team.get("teamId") or "")
        team_name = team.get("teamName")
        for category in RECOGNIZED_CATEGORIES:
            for index, candidate in enumerate(team.get(category) or []):
                errors, warnings, score = validate_candidate(category, candidate, team_id, index)
                bucket = queue_bucket(category, score, warnings, errors)
                row = {
                    "teamId": team_id,
                    "teamName": team_name,
                    "category": category,
                    "index": index,
                    "bucket": bucket,
                    "impactBand": score.get("impactBand", "low"),
                    "useTier": score.get("useTier", "insufficient_detail"),
                    "qualityScore": score.get("qualityScore", 0),
                    "sourceTier": score.get("sourceTier"),
                    "confidence": score.get("confidence"),
                    "mapsTo": score.get("mapsTo"),
                    "candidateCategory": score.get("candidateCategory"),
                    "summary": candidate_text(candidate)[:260],
                    "warnings": warnings,
                    "errors": errors,
                    "recommendedHandlingJa": "",
                }
                row["recommendedHandlingJa"] = handling_ja(row)
                queued.append(row)

    bucket_counts = Counter(row["bucket"] for row in queued)
    category_counts = Counter(row["category"] for row in queued)
    impact_counts = Counter(row["impactBand"] for row in queued)
    use_tier_counts = Counter(row["useTier"] for row in queued)
    by_team: dict[str, list[dict]] = defaultdict(list)
    for row in queued:
        by_team[row["teamId"]].append(row)

    team_rows = []
    for team_id, rows in by_team.items():
        buckets = Counter(row["bucket"] for row in rows)
        review_score = sum(
            row["qualityScore"]
            for row in rows
            if row["bucket"] in {"current_field_review", "warning_hold"} and row["impactBand"] in {"high", "medium"}
        )
        team_rows.append({
            "teamId": team_id,
            "teamName": rows[0].get("teamName"),
            "candidateCount": len(rows),
            "bucketCounts": dict(sorted(buckets.items())),
            "currentFieldReviewCount": buckets.get("current_field_review", 0),
            "warningHoldCount": buckets.get("warning_hold", 0),
            "futureEngineCount": buckets.get("future_engine", 0),
            "reviewScore": review_score,
        })
    team_rows.sort(key=lambda row: (-row["reviewScore"], row["teamId"]))

    sorted_rows = sorted(
        queued,
        key=lambda row: (
            {"current_field_review": 0, "warning_hold": 1, "future_engine": 2, "provisional_context": 3}.get(row["bucket"], 4),
            -row["qualityScore"],
            row["teamId"],
            row["category"],
        ),
    )

    return {
        "generatedAt": generated_at,
        "sourceReports": [],
        "note": (
            "外部調査候補を反映前の判断キューに分けた読み取り専用レポートです。"
            "候補を捨てず、現行フィールド・警告保留・暫定文脈・将来エンジン候補に分離します。"
        ),
        "validInput": bool(validation_report.get("valid")),
        "candidateCount": len(queued),
        "bucketCounts": dict(sorted(bucket_counts.items())),
        "categoryCounts": dict(sorted(category_counts.items())),
        "impactCounts": dict(sorted(impact_counts.items())),
        "useTierCounts": dict(sorted(use_tier_counts.items())),
        "currentFieldReviewCount": bucket_counts.get("current_field_review", 0),
        "warningHoldCount": bucket_counts.get("warning_hold", 0),
        "futureEngineCount": bucket_counts.get("future_engine", 0),
        "provisionalContextCount": bucket_counts.get("provisional_context", 0),
        "teamCount": len(by_team),
        "teams": team_rows,
        "currentFieldReviewQueue": [row for row in sorted_rows if row["bucket"] == "current_field_review"],
        "warningHoldQueue": [row for row in sorted_rows if row["bucket"] == "warning_hold"],
        "futureEngineQueue": [row for row in sorted_rows if row["bucket"] == "future_engine"],
        "provisionalContextQueue": [row for row in sorted_rows if row["bucket"] == "provisional_context"],
    }


def main() -> int:
    candidates_path = latest_report("external_data_verification_candidates_*.json")
    validation_path = latest_report("external_data_verification_validation_*.json")
    if candidates_path is None or validation_path is None:
        raise SystemExit("external data verification candidate/validation report is missing")

    report = build_decision_queue(load_json(candidates_path), load_json(validation_path))
    report["sourceReports"] = [
        source_report_ref(candidates_path, "external_data_verification_candidates"),
        source_report_ref(validation_path, "external_data_verification_validation"),
    ]
    out_path = REPORTS_DIR / "external_data_decision_queue_2026-06-24.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        "currentFieldReview={current} warningHold={warning} futureEngine={future} provisionalContext={provisional}".format(
            current=report["currentFieldReviewCount"],
            warning=report["warningHoldCount"],
            future=report["futureEngineCount"],
            provisional=report["provisionalContextCount"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
