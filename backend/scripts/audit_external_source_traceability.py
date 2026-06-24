"""Audit citation traceability for external data verification candidates.

The external verification candidate report can preserve useful football signal
without being ready for seed/rating changes. This audit checks whether each
candidate has source references that can be re-opened by Codex later. It does
not validate the truth of the claims and does not mutate data.

Usage:
  ./venv/Scripts/python.exe scripts/audit_external_source_traceability.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_external_data_verification_report import RECOGNIZED_CATEGORIES, as_list, candidate_text, source_tier

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports"


def latest_report(pattern: str, reports_dir: Path = REPORTS_DIR) -> Path | None:
    matches = sorted(reports_dir.glob(pattern))
    return matches[-1] if matches else None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def source_has_url(source: dict) -> bool:
    url = source.get("url")
    return isinstance(url, str) and url.startswith(("http://", "https://"))


def audit_traceability(candidate_report: dict, generated_at: str | None = None) -> dict:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    candidate_count = 0
    source_count = 0
    missing_url_source_count = 0
    missing_date_source_count = 0
    candidates_missing_resolvable_url = []
    tier_counts: Counter[str] = Counter()
    source_name_counts: Counter[str] = Counter()
    missing_url_by_team: defaultdict[str, int] = defaultdict(int)
    missing_url_by_category: defaultdict[str, int] = defaultdict(int)

    for team in candidate_report.get("teams") or []:
        team_id = str(team.get("teamId") or "")
        for category in RECOGNIZED_CATEGORIES:
            for index, candidate in enumerate(team.get(category) or []):
                candidate_count += 1
                sources = [row for row in as_list(candidate.get("sources")) if isinstance(row, dict)]
                has_resolvable_url = any(source_has_url(source) for source in sources)
                if not has_resolvable_url:
                    candidates_missing_resolvable_url.append({
                        "teamId": team_id,
                        "category": category,
                        "index": index,
                        "sourceTier": source_tier(candidate),
                        "summary": candidate_text(candidate)[:220],
                    })
                    missing_url_by_team[team_id] += 1
                    missing_url_by_category[category] += 1
                for source in sources:
                    source_count += 1
                    name = source.get("name") if isinstance(source.get("name"), str) else "missing"
                    source_name_counts[name] += 1
                    tier_counts[source.get("tier") or "missing"] += 1
                    if not source_has_url(source):
                        missing_url_source_count += 1
                    if not source.get("observedDate"):
                        missing_date_source_count += 1

    severity = "pass"
    if candidates_missing_resolvable_url:
        severity = "review_required"
    if candidate_count and len(candidates_missing_resolvable_url) == candidate_count:
        severity = "blocking_for_data_changes"

    return {
        "generatedAt": generated_at,
        "note": (
            "外部調査候補の出典をあとから再確認できるかを見る読み取り専用監査です。"
            "URLが無い候補は捨てずに残しますが、seed・能力値・戦術値へ反映する前にURL付き出典で再確認します。"
        ),
        "severity": severity,
        "candidateCount": candidate_count,
        "sourceReferenceCount": source_count,
        "missingUrlSourceCount": missing_url_source_count,
        "candidateMissingResolvableUrlCount": len(candidates_missing_resolvable_url),
        "missingObservedDateSourceCount": missing_date_source_count,
        "tierCounts": dict(sorted(tier_counts.items())),
        "missingUrlByTeam": dict(sorted(missing_url_by_team.items())),
        "missingUrlByCategory": dict(sorted(missing_url_by_category.items())),
        "topSourceNames": [
            {"name": name, "count": count}
            for name, count in source_name_counts.most_common(20)
        ],
        "candidatesMissingResolvableUrl": candidates_missing_resolvable_url[:40],
        "recommendationsJa": [
            "現行フィールド候補73件は、反映specを書く前にURL付き出典へ差し替える。",
            "URLが無い候補も、調査の方向性としては保持する。削除ではなく再確認キューとして扱う。",
            "選手交代候補は現エンジンに直接入れず、将来仕様の要求データとして保留する。",
        ],
    }


def main() -> int:
    candidates_path = latest_report("external_data_verification_candidates_*.json")
    if candidates_path is None:
        raise SystemExit("external data verification candidate report is missing")
    report = audit_traceability(load_json(candidates_path))
    out_path = REPORTS_DIR / "external_source_traceability_audit_2026-06-24.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        "severity={severity} candidateMissingResolvableUrl={missing}/{total}".format(
            severity=report["severity"],
            missing=report["candidateMissingResolvableUrlCount"],
            total=report["candidateCount"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
