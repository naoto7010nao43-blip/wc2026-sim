"""Build a read-only review report for tactical-basis candidate notes.

The report intentionally does not accept `_tactical_profile_basis` as verified
seed evidence. Free-text notes are converted into a review queue so they can be
checked, structured, and only then used by manager/tactical diagnostics.

Usage:
  ./venv/Scripts/python.exe scripts/build_tactical_basis_candidate_review.py
  ./venv/Scripts/python.exe scripts/build_tactical_basis_candidate_review.py --check-urls
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
URL_RE = re.compile(r"https?://[^\s)]+")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def extract_urls(text: str) -> list[str]:
    return [url.rstrip(".,") for url in URL_RE.findall(text)]


def check_url(url: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                return {"url": url, "status": response.status, "method": method, "error": None}
        except Exception as exc:  # noqa: BLE001 - this is a best-effort audit, not app logic
            last_error = f"{type(exc).__name__}: {str(exc)[:160]}"
    return {"url": url, "status": None, "method": None, "error": last_error}


def recommended_status(url_count: int, reachable_url_count: int | None, blocked_or_failed_url_count: int | None) -> str:
    if url_count == 0:
        return "needs_sources"
    if reachable_url_count is None:
        return "ready_for_human_review"
    if reachable_url_count > 0 and blocked_or_failed_url_count == 0:
        return "ready_for_human_review"
    return "blocked_source_review"


def build_report(teams: list[dict], *, check_urls: bool = False) -> dict:
    all_urls = sorted({url for team in teams for url in extract_urls(str(team.get("_tactical_profile_basis") or ""))})
    url_results: dict[str, dict] = {}
    if check_urls and all_urls:
        with ThreadPoolExecutor(max_workers=10) as executor:
            for result in executor.map(check_url, all_urls):
                url_results[result["url"]] = result

    rows = []
    for team in teams:
        candidate_text = str(team.get("_tactical_profile_basis") or "")
        urls = extract_urls(candidate_text)
        reachable = None
        failed = None
        if check_urls:
            reachable = sum(1 for url in urls if (url_results.get(url) or {}).get("status") == 200)
            failed = len(urls) - reachable
        status = recommended_status(len(urls), reachable, failed)
        rows.append(
            {
                "team_id": team["id"],
                "team_name": team.get("name"),
                "candidate_present": bool(candidate_text),
                "url_count": len(urls),
                "reachable_url_count": reachable,
                "blocked_or_failed_url_count": failed,
                "url_less_candidate": bool(candidate_text) and len(urls) == 0,
                "recommended_status": status,
                "urls": urls,
                "notes_ja": _notes(status, bool(candidate_text), len(urls), reachable, failed),
            }
        )

    status_counts: dict[str, int] = {}
    for row in rows:
        if not row["candidate_present"]:
            continue
        status_counts[row["recommended_status"]] = status_counts.get(row["recommended_status"], 0) + 1

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "note": "戦術根拠の自由文候補を、seedへ直接反映せずレビューキューへ変換する読み取り専用レポートです。数値戦術・予測式・seedデータは変更しません。",
        "urlCheckPerformed": check_urls,
        "teamCount": len(rows),
        "candidateTeamCount": sum(1 for row in rows if row["candidate_present"]),
        "urlCount": sum(row["url_count"] for row in rows),
        "urlLessCandidateCount": sum(1 for row in rows if row["url_less_candidate"]),
        "statusCounts": status_counts,
        "urlResults": [url_results[url] for url in sorted(url_results)],
        "teams": rows,
        "recommendationsJa": [
            "URLなし候補はseed反映せず、外部調査キューへ戻す。",
            "自由文の存在だけでmanager/tactical auditの根拠あり判定を通さない。",
            "採用する場合はtactical_profile_sourcesのような構造化フィールドへ移し、verified=trueを明示する。",
        ],
    }


def _notes(status: str, candidate_present: bool, url_count: int, reachable: int | None, failed: int | None) -> str:
    if not candidate_present:
        return "候補文がありません。"
    if status == "needs_sources":
        return "候補文はありますがURLがないため、根拠としては未採用です。"
    if status == "blocked_source_review":
        return f"URL {url_count}件のうち到達不能または未確認が{failed}件あります。本文確認まで保留します。"
    if reachable is None:
        return f"URL {url_count}件を含む候補です。本文確認と構造化を待ちます。"
    return f"URL {reachable}件が到達可能です。本文が戦術値を支持するか確認してから構造化します。"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-urls", action="store_true")
    args = parser.parse_args()
    teams = load_json(SEED_DIR / "teams.json")
    report = build_report(teams, check_urls=args.check_urls)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"tactical_basis_candidate_review_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        "Candidates: "
        f"{report['candidateTeamCount']} teams, {report['urlCount']} urls, "
        f"{report['urlLessCandidateCount']} url-less candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
