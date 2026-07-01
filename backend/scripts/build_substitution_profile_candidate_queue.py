"""Build a read-only queue for manager substitution-profile candidates.

Spec 018 added a neutral-preserving substitution profile mechanism to the
engine, but no team has source-backed non-neutral values yet. This report
turns the external substitution research candidates into a review queue so a
later Codex-reviewed change can populate profile values deliberately.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports"

SOURCE_TIER_SCORE = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
CONFIDENCE_SCORE = {"high": 3, "medium": 2, "low": 1}

SIGNAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "first_sub_minute_bias": (
        "first substitution",
        "first change",
        "halftime",
        "half-time",
        "57th",
        "58'",
        "58th",
        "60th",
        "61st",
        "62nd",
        "87th",
        "late",
        "early",
        "delayed",
    ),
    "trailing_aggression": (
        "behind",
        "chasing",
        "attacking",
        "equalizer",
        "scored",
        "goal",
        "super-sub",
        "fresh attackers",
    ),
    "leading_defensive_bias": (
        "leading",
        "protect",
        "defensive",
        "solidity",
        "close out",
        "closing",
    ),
    "like_for_like_preference": (
        "like-for-like",
        "shape",
        "formation",
        "same position",
        "position",
    ),
    "bench_trust": (
        "bench",
        "substitute",
        "substitutes",
        "all 5",
        "five substitution",
        "depth",
        "super-sub",
        "fresh",
    ),
    "late_penalty_prep_bias": (
        "penalty",
        "penalties",
        "shootout",
        "extra-time",
        "extra time",
    ),
}


def _latest_report(reports_dir: Path, pattern: str) -> dict[str, Any] | None:
    matches = sorted(reports_dir.glob(pattern))
    if not matches:
        return None
    return json.loads(matches[-1].read_text(encoding="utf-8"))


def _source_tier_score(candidate: dict[str, Any]) -> int:
    return SOURCE_TIER_SCORE.get(str(candidate.get("sourceTier", "")).upper(), 0)


def _confidence_score(candidate: dict[str, Any]) -> int:
    return CONFIDENCE_SCORE.get(str(candidate.get("confidence", "")).lower(), 0)


def infer_profile_signals(summary: str) -> list[str]:
    haystack = summary.lower()
    signals = [
        signal
        for signal, keywords in SIGNAL_KEYWORDS.items()
        if any(keyword.lower() in haystack for keyword in keywords)
    ]
    return signals or ["manual_substitution_profile_review"]


def readiness_band(readiness_score: float, warnings: list[str], signals: list[str]) -> str:
    if warnings:
        return "hold_for_source_review"
    if readiness_score >= 8 and len(signals) >= 2:
        return "profile_review_ready"
    if readiness_score >= 6:
        return "needs_more_match_evidence"
    return "low_confidence_context"


def build_team_rows(decision_queue: dict[str, Any]) -> list[dict[str, Any]]:
    future_queue = [
        row
        for row in decision_queue.get("futureEngineQueue", [])
        if row.get("category") == "substitutionTendencyCandidates" or row.get("mapsTo") == "substitution_tendency"
    ]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in future_queue:
        grouped[row.get("teamId", "UNKNOWN")].append(row)

    teams: list[dict[str, Any]] = []
    for team_id, rows in grouped.items():
        signals = sorted({signal for row in rows for signal in infer_profile_signals(row.get("summary", ""))})
        warnings = sorted({warning for row in rows for warning in row.get("warnings", [])})
        source_score = max((_source_tier_score(row) for row in rows), default=0)
        confidence_score = max((_confidence_score(row) for row in rows), default=0)
        quality_score = max((float(row.get("qualityScore", 0)) for row in rows), default=0)
        readiness_score = round(source_score + confidence_score + min(quality_score, 5), 1)
        band = readiness_band(readiness_score, warnings, signals)

        teams.append(
            {
                "teamId": team_id,
                "teamName": rows[0].get("teamName"),
                "candidateCount": len(rows),
                "strongestSourceTier": rows[0].get("sourceTier"),
                "confidenceBand": rows[0].get("confidence"),
                "readinessScore": readiness_score,
                "readinessBand": band,
                "suggestedProfileSignals": signals,
                "evidenceSummaries": [row.get("summary", "") for row in rows],
                "warnings": warnings,
                "recommendedHandlingJa": (
                    "出典付き候補として、交代プロファイル値を作る前のCodexレビュー対象にできます。"
                    if band == "profile_review_ready"
                    else "まだ直接反映せず、追加の試合別根拠または出典確認を待つ候補として保留します。"
                ),
            }
        )

    return sorted(
        teams,
        key=lambda row: (
            row["readinessBand"] != "profile_review_ready",
            -row["readinessScore"],
            row["teamId"],
        ),
    )


def build_report(reports_dir: Path = REPORTS_DIR) -> dict[str, Any]:
    decision_queue = _latest_report(reports_dir, "external_data_decision_queue_*.json")
    generated_at = datetime.now(timezone.utc).isoformat()
    if decision_queue is None:
        return {
            "generatedAt": generated_at,
            "sourceReports": [],
            "note": "外部調査の判断キューがまだ生成されていないため、交代プロファイル候補は表示できません。",
            "candidateCount": 0,
            "teamCount": 0,
            "readyTeamCount": 0,
            "holdTeamCount": 0,
            "signalCounts": {},
            "teams": [],
            "recommendationsJa": ["先に外部調査候補と判断キューを生成してください。"],
        }

    teams = build_team_rows(decision_queue)
    signal_counts = Counter(signal for team in teams for signal in team["suggestedProfileSignals"])
    ready_count = sum(1 for team in teams if team["readinessBand"] == "profile_review_ready")
    hold_count = sum(1 for team in teams if team["readinessBand"] in {"hold_for_source_review", "low_confidence_context"})

    return {
        "generatedAt": generated_at,
        "sourceReports": [
            {
                "name": "external_data_decision_queue",
                "generatedAt": decision_queue.get("generatedAt"),
            }
        ],
        "note": (
            "交代傾向の外部調査候補を、既存の交代プロファイル機構に将来反映するための読み取り専用キューです。"
            "ここではseed、能力値、試合ロジック、予測式を変更せず、反映候補の優先度だけを整理します。"
        ),
        "candidateCount": sum(team["candidateCount"] for team in teams),
        "teamCount": len(teams),
        "readyTeamCount": ready_count,
        "holdTeamCount": hold_count,
        "signalCounts": dict(sorted(signal_counts.items())),
        "teams": teams,
        "recommendationsJa": [
            "profile_review_readyのチームから、交代タイミング・スコア状況・控え信頼度を別々にレビューしてください。",
            "1つの試合記事だけで数値化せず、複数試合または公式記録で同じ傾向が見える場合だけ非中立値を検討してください。",
            "反映時は試合結果分布とイベント説得力のbefore/afterを必ず比較し、勝率だけが不自然に動く変更は戻してください。",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()

    report = build_report()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"substitution_profile_candidate_queue_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        "candidateCount={candidateCount} teamCount={teamCount} readyTeamCount={readyTeamCount}".format(
            **report
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
