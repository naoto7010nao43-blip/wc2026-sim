"""Build a read-only source provenance audit for rating-review candidates.

The rating workbench and decision audit identify possible player-rating review
targets. This script audits the source text behind those candidates so future
data-changing specs do not accidentally treat game ratings, secondary sites, or
future-looking claims as strong evidence.

Read-only: does not mutate seed data, ratings, formulas, or prediction
behavior.

Usage: ./venv/Scripts/python.exe scripts/build_source_provenance_audit.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports"
PLAYERS_PATH = BACKEND_DIR / "data" / "seed" / "players.json"

RISK_RULES = {
    "EA FC": {
        "severity": "high",
        "reason_ja": "ゲーム内評価は実データではなく、能力値変更の直接根拠にできません。",
    },
    "FC26": {
        "severity": "high",
        "reason_ja": "ゲーム内評価は実データではなく、能力値変更の直接根拠にできません。",
    },
    "Fotmob": {
        "severity": "medium",
        "reason_ja": "二次的なスタッツ参照のため、公式成績または別ソースで確認が必要です。",
    },
    "hat trick": {
        "severity": "high",
        "reason_ja": "単発イベントの記述は能力値更新の根拠として過大評価しやすく、事実確認が必要です。",
    },
    "WC2026": {
        "severity": "medium",
        "reason_ja": "大会関連の将来・直近記述は、公式発表日と文脈を確認してから使う必要があります。",
    },
    "World Cup 2026": {
        "severity": "medium",
        "reason_ja": "大会関連の将来・直近記述は、公式発表日と文脈を確認してから使う必要があります。",
    },
    "Wikipedia": {
        "severity": "medium",
        "reason_ja": "Wikipediaは入口情報としては使えますが、能力値変更には一次情報での確認が必要です。",
    },
}

SEVERITY_WEIGHT = {"low": 1, "medium": 3, "high": 5}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report(pattern: str) -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(pattern))
    if not matches:
        return None
    return load_json(matches[-1])


def source_risk_flags(citations: list[str]) -> list[dict]:
    joined = " | ".join(citations)
    flags = []
    seen = set()
    for marker, rule in RISK_RULES.items():
        if marker.casefold() in joined.casefold() and marker not in seen:
            flags.append({
                "marker": marker,
                "severity": rule["severity"],
                "reason_ja": rule["reason_ja"],
            })
            seen.add(marker)
    return flags


def risk_score(flags: list[dict]) -> int:
    return sum(SEVERITY_WEIGHT.get(flag["severity"], 1) for flag in flags)


def flatten_decision_candidates(decision_report: dict | None) -> list[dict]:
    rows = []
    if not decision_report:
        return rows
    buckets = (
        "candidate_for_later_proposal",
        "source_review_first",
        "do_not_use_for_upgrade_proposal",
        "monitor_only",
    )
    for team in decision_report.get("teams", []):
        for bucket in buckets:
            for candidate in team.get(bucket, []):
                row = dict(candidate)
                row["team_id"] = team["team_id"]
                row["team_name"] = team["team_name"]
                row["decision_bucket"] = bucket
                rows.append(row)
    return rows


def player_source_index(players: list[dict]) -> dict[str, dict]:
    return {
        player["id"]: {
            "team_id": player.get("team_id"),
            "player_id": player["id"],
            "name": player.get("name"),
            "source_citations": player.get("source_citations") or [],
        }
        for player in players
    }


def build_seed_source_summary(players: list[dict]) -> dict:
    marker_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    risky_players = []
    for player in players:
        citations = player.get("source_citations") or []
        flags = source_risk_flags(citations)
        if not flags:
            continue
        for flag in flags:
            marker_counts[flag["marker"]] += 1
            severity_counts[flag["severity"]] += 1
        risky_players.append({
            "team_id": player.get("team_id"),
            "player_id": player.get("id"),
            "name": player.get("name"),
            "risk_score": risk_score(flags),
            "risk_flags": flags,
            "source_citations": citations,
        })
    risky_players.sort(key=lambda row: (-row["risk_score"], row["team_id"] or "", row["name"] or ""))
    return {
        "seed_player_count": len(players),
        "players_with_source_risk": len(risky_players),
        "marker_counts": dict(sorted(marker_counts.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
        "top_risky_seed_players": risky_players[:20],
    }


def build_team_rows(decision_candidates: list[dict], source_index: dict[str, dict]) -> list[dict]:
    by_team: dict[str, list[dict]] = defaultdict(list)
    team_names: dict[str, str] = {}
    for candidate in decision_candidates:
        player_source = source_index.get(candidate["player_id"], {})
        citations = player_source.get("source_citations") or []
        flags = source_risk_flags(citations)
        row = {
            "player_id": candidate["player_id"],
            "name": candidate["name"],
            "primary_position": candidate.get("primary_position"),
            "current_overall": candidate.get("current_overall"),
            "decision_bucket": candidate.get("decision_bucket"),
            "suggested_codex_action": candidate.get("suggested_codex_action"),
            "risk_score": risk_score(flags),
            "risk_flags": flags,
            "source_citations": citations,
        }
        team_id = candidate["team_id"]
        team_names[team_id] = candidate.get("team_name") or team_id
        by_team[team_id].append(row)

    teams = []
    for team_id, rows in by_team.items():
        rows.sort(key=lambda row: (-row["risk_score"], row["decision_bucket"], row["name"]))
        bucket_counts = Counter(row["decision_bucket"] for row in rows)
        risky_rows = [row for row in rows if row["risk_score"] > 0]
        clear_later = [
            row for row in rows
            if row["decision_bucket"] == "candidate_for_later_proposal" and row["risk_score"] == 0
        ]
        teams.append({
            "team_id": team_id,
            "team_name": team_names[team_id],
            "candidate_count": len(rows),
            "source_risk_candidate_count": len(risky_rows),
            "decision_bucket_counts": dict(sorted(bucket_counts.items())),
            "clear_later_proposal_candidates": clear_later,
            "source_review_candidates": risky_rows,
        })
    teams.sort(key=lambda row: (-row["source_risk_candidate_count"], row["team_id"]))
    return teams


def build_report(
    players: list[dict] | None = None,
    decision_report: dict | None = None,
) -> dict:
    players = players if players is not None else load_json(PLAYERS_PATH)
    decision_report = decision_report if decision_report is not None else latest_report("rating_decision_audit_*.json")
    decision_candidates = flatten_decision_candidates(decision_report)
    source_index = player_source_index(players)
    seed_summary = build_seed_source_summary(players)
    teams = build_team_rows(decision_candidates, source_index)

    proposal_clear = sum(len(team["clear_later_proposal_candidates"]) for team in teams)
    source_review = sum(len(team["source_review_candidates"]) for team in teams)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "note": (
            "能力値レビュー候補の出典リスクを確認する読み取り専用監査です。"
            "ゲーム内評価、二次情報、未来・直近大会記述を直接の能力値変更根拠にしないためのゲートです。"
        ),
        "sourceReports": [
            {"name": "rating_decision_audit", "generatedAt": (decision_report or {}).get("generatedAt")},
        ],
        "seedSourceSummary": seed_summary,
        "decisionCandidateCount": len(decision_candidates),
        "clearLaterProposalCandidateCount": proposal_clear,
        "sourceReviewCandidateCount": source_review,
        "teamCount": len(teams),
        "teams": teams,
        "recommendations_ja": [
            "能力値を変更する前に、source_review_candidatesは一次情報または複数ソースで確認する。",
            "candidate_for_later_proposalでも、数値変更は別途ベンチマーク比較を通過するまで適用しない。",
            "EA FC/FC26系の記述は補助メモに留め、能力値差分の直接根拠から除外する。",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()

    report = build_report()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"source_provenance_audit_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(
        "Seed risk: "
        f"{report['seedSourceSummary']['players_with_source_risk']}/"
        f"{report['seedSourceSummary']['seed_player_count']} players"
    )
    print(
        "Decision candidates: "
        f"{report['decisionCandidateCount']} total, "
        f"{report['clearLaterProposalCandidateCount']} clear later-proposal candidates, "
        f"{report['sourceReviewCandidateCount']} source-review candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
