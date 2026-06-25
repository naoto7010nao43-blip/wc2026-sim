"""Build read-only data change proposal reports from external verification candidates.

This script never mutates seed/rating/tactical data. It turns URL-backed,
field-mappable candidates from the external data verification pipeline into
four separate proposal reports for later Codex review:

  - external_current_field_change_proposals_2026-06-24.json
  - external_rating_change_proposals_2026-06-24.json
  - external_tactical_change_proposals_2026-06-24.json
  - external_roster_change_proposals_2026-06-24.json

Each row carries the current seed value (where it can be resolved), the raw
claim text in place of a fabricated "proposed value" (this script does not
invent specific replacement numbers/names), source URLs/tiers, a governance
confidence label, and short Japanese impact/safety notes. Tier C evidence and
candidates with no resolvable source URL are excluded entirely; they remain
review-only material in the decision queue.

Usage:
  ./venv/Scripts/python.exe scripts/build_external_data_change_proposals.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_external_data_verification_report import (
    FUTURE_ONLY_CATEGORIES,
    RECOGNIZED_CATEGORIES,
    as_list,
    candidate_text,
    load_json,
    validate_candidate,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports"
SEED_DIR = BACKEND_DIR / "data" / "seed"

TACTICAL_FIELDS = {"press_intensity", "possession_style", "defensive_line_height", "default_formation"}
CURRENT_FIELDS = {"manager_name", "fifa_rank", "team_strength_rating", "club_name"}
RATING_FIELDS = {"player_rating"}
ROSTER_FIELDS = {"seed_roster", "availability_status", "starting_probability"}

REPORT_FOR_FIELD: dict[str, str] = {}
for _f in TACTICAL_FIELDS:
    REPORT_FOR_FIELD[_f] = "tactical"
for _f in CURRENT_FIELDS:
    REPORT_FOR_FIELD[_f] = "current_field"
for _f in RATING_FIELDS:
    REPORT_FOR_FIELD[_f] = "rating"
for _f in ROSTER_FIELDS:
    REPORT_FOR_FIELD[_f] = "roster"

PLAYER_LEVEL_FIELDS = {"club_name", "player_rating", "availability_status", "starting_probability", "seed_roster"}

OUT_FILENAMES = {
    "current_field": "external_current_field_change_proposals_2026-06-24.json",
    "rating": "external_rating_change_proposals_2026-06-24.json",
    "tactical": "external_tactical_change_proposals_2026-06-24.json",
    "roster": "external_roster_change_proposals_2026-06-24.json",
}

IMPACT_JA = {
    "manager_name": "チーム運用上の監督名表示と戦術推論の前提に影響します。",
    "fifa_rank": "FIFAランクに依存する国力評価・予測補正に影響します。",
    "team_strength_rating": "team_strength_ratingはseedの直接フィールドではなく算出値である可能性が高く、反映方法はCodexが判断する必要があります。",
    "club_name": "選手の所属クラブ表示に影響しますが、能力値そのものは変更しません。",
    "default_formation": "既定フォーメーション表示とシミュレーションの初期配置に影響します。",
    "press_intensity": "戦術プロファイル(プレッシング強度)に影響し、試合シミュレーションに反映されます。",
    "possession_style": "戦術プロファイル(ポゼッション傾向)に影響し、試合シミュレーションに反映されます。",
    "defensive_line_height": "戦術プロファイル(最終ラインの高さ)に影響し、試合シミュレーションに反映されます。",
    "player_rating": "選手の能力値(overall)に影響し、シミュレーション上の強さに直接反映されます。小幅かつ慎重な範囲設定が必要です。",
    "availability_status": "出場可否の扱いに影響し、先発確率や采配シミュレーションに反映されます。",
    "starting_probability": "先発確率の推定に影響します。",
    "seed_roster": "シードの選手登録(追加/除外/差し替え)に影響する可能性があります。",
}

RATIONALE_JA_HIGH = "出典の信頼度が高く(TierS/A、confidence={conf})、Codexのレビュー後に反映候補として検討可能です。"
RATIONALE_JA_MED = "報道ベースの情報(TierB)のため、TierS/Aで補強されるまでは'external/estimated'扱いに留め、確定事実としては反映しないでください。"
RATIONALE_JA_ROSTER_BLOCKED = "ロスター変更はTierSまたはFIFA/協会の出典が必要です。現状の出典ではこの基準を満たさないため、提案のみに留めてください。"


def latest_report(pattern: str, reports_dir: Path = REPORTS_DIR) -> Path | None:
    matches = sorted(reports_dir.glob(pattern))
    return matches[-1] if matches else None


def load_seed_json(name: str) -> Any:
    path = SEED_DIR / name
    if not path.exists():
        return []
    return load_json(path)


def index_by(rows: list[dict], key: str) -> dict[str, dict]:
    return {row[key]: row for row in rows if isinstance(row, dict) and row.get(key)}


NAME_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ'\-]+")


def match_player(claim: str, team_players: list[dict]) -> dict | None:
    """Heuristic, non-authoritative name match against a team's seed roster.

    Used only to populate a proposal report's currentValue for human review;
    never used to apply a change automatically.
    """
    best = None
    best_len = 0
    for player in team_players:
        name = player.get("name") or ""
        if not name:
            continue
        if name.lower() in claim.lower() and len(name) > best_len:
            best, best_len = player, len(name)
    if best:
        return best
    for player in team_players:
        name = player.get("name") or ""
        tokens = NAME_TOKEN_RE.findall(name)
        if not tokens:
            continue
        last = tokens[-1]
        if len(last) >= 4 and re.search(rf"\b{re.escape(last)}\b", claim, re.IGNORECASE) and len(last) > best_len:
            best, best_len = player, len(last)
    return best


def recommended_confidence_label(maps_to: str, source_tier: str | None) -> str:
    if maps_to == "player_rating":
        return "estimated"
    if maps_to == "club_name":
        return "external"
    if maps_to == "team_strength_rating":
        return "estimated"
    if maps_to in {"manager_name", "fifa_rank"}:
        return "official" if source_tier == "S" else "external"
    if maps_to == "seed_roster":
        return "external" if source_tier == "S" else "estimated"
    if source_tier in {"S", "A"}:
        return "external"
    return "estimated"


def safety_rationale_ja(maps_to: str, source_tier: str | None, confidence_value: str | None) -> str:
    if maps_to == "seed_roster" and source_tier != "S":
        return RATIONALE_JA_ROSTER_BLOCKED
    if source_tier in {"S", "A"}:
        return RATIONALE_JA_HIGH.format(conf=confidence_value or "unknown")
    return RATIONALE_JA_MED


def current_value_for_team_field(maps_to: str, team: dict) -> Any:
    if maps_to == "manager_name":
        return (team.get("tactical_profile") or {}).get("manager_name")
    if maps_to == "fifa_rank":
        return team.get("fifa_rank")
    if maps_to == "default_formation":
        return team.get("default_formation")
    if maps_to in {"press_intensity", "possession_style", "defensive_line_height"}:
        return (team.get("tactical_profile") or {}).get(maps_to)
    if maps_to == "team_strength_rating":
        return None
    return None


def build_proposals(
    candidate_report: dict,
    teams_seed: list[dict],
    players_seed: list[dict],
    official_seed: list[dict],
    ratings_seed: list[dict],
    generated_at: str | None = None,
) -> dict[str, dict]:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()

    teams_by_id = index_by(teams_seed, "id")
    players_by_team: dict[str, list[dict]] = defaultdict(list)
    for player in players_seed:
        if isinstance(player, dict) and player.get("team_id"):
            players_by_team[player["team_id"]].append(player)
    official_by_id = index_by(official_seed, "playerId")
    ratings_by_id = index_by(ratings_seed, "playerId")

    rows_by_report: dict[str, list[dict]] = defaultdict(list)
    excluded_tier_c = 0
    excluded_no_url = 0
    excluded_unmapped = 0

    for team in candidate_report.get("teams") or []:
        team_id = str(team.get("teamId") or "")
        team_name = team.get("teamName")
        team_seed = teams_by_id.get(team_id, {})
        team_players = players_by_team.get(team_id, [])

        for category in RECOGNIZED_CATEGORIES:
            if category in FUTURE_ONLY_CATEGORIES:
                continue
            for index, candidate in enumerate(team.get(category) or []):
                errors, warnings, score = validate_candidate(category, candidate, team_id, index)
                if errors:
                    continue
                maps_to = score.get("mapsTo")
                if not maps_to or maps_to not in REPORT_FOR_FIELD:
                    excluded_unmapped += 1
                    continue
                source_tier = score.get("sourceTier")
                if source_tier == "C":
                    excluded_tier_c += 1
                    continue

                sources = [row for row in as_list(candidate.get("sources")) if isinstance(row, dict)]
                url_sources = [
                    {
                        "name": row.get("name"),
                        "url": row.get("url"),
                        "tier": row.get("tier"),
                        "observedDate": row.get("observedDate"),
                    }
                    for row in sources
                    if isinstance(row.get("url"), str) and row["url"].startswith(("http://", "https://"))
                ]
                if not url_sources:
                    excluded_no_url += 1
                    continue

                claim = candidate_text(candidate)
                report_key = REPORT_FOR_FIELD[maps_to]
                confidence_value = score.get("confidence")

                player_id = None
                player_name = None
                player_match_confidence = "team_level"
                current_value: Any = None

                if maps_to in PLAYER_LEVEL_FIELDS:
                    matched = match_player(claim, team_players)
                    if matched:
                        player_id = matched.get("id")
                        player_name = matched.get("name")
                        player_match_confidence = "matched"
                        if maps_to == "club_name":
                            official = official_by_id.get(player_id)
                            current_value = official.get("clubName") if official else None
                        elif maps_to == "player_rating":
                            rating = ratings_by_id.get(player_id)
                            current_value = rating.get("overall") if rating else None
                        elif maps_to == "availability_status":
                            rating = ratings_by_id.get(player_id)
                            current_value = rating.get("availability") if rating else None
                        elif maps_to == "starting_probability":
                            rating = ratings_by_id.get(player_id)
                            current_value = rating.get("startingProbability") if rating else None
                        elif maps_to == "seed_roster":
                            current_value = "present_in_seed_roster"
                    else:
                        player_match_confidence = "unmatched"
                        if maps_to == "seed_roster":
                            current_value = "not_found_in_seed_roster"
                else:
                    current_value = current_value_for_team_field(maps_to, team_seed)

                row = {
                    "teamId": team_id,
                    "teamName": team_name,
                    "category": category,
                    "mapsTo": maps_to,
                    "playerId": player_id,
                    "playerName": player_name,
                    "playerMatchConfidence": player_match_confidence,
                    "currentValue": current_value,
                    "claimText": claim,
                    "proposedValueNote": "CodexがclaimTextを確認し、反映する具体的な値を確定してください。本レポートは値を自動生成しません。",
                    "sourceTier": source_tier,
                    "confidence": confidence_value,
                    "qualityScore": score.get("qualityScore"),
                    "impactBand": score.get("impactBand"),
                    "useTier": score.get("useTier"),
                    "sources": url_sources,
                    "recommendedConfidenceLabel": recommended_confidence_label(maps_to, source_tier),
                    "expectedSimulatorImpactJa": IMPACT_JA.get(maps_to, ""),
                    "safetyRationaleJa": safety_rationale_ja(maps_to, source_tier, confidence_value),
                    "readyForCodexReview": (
                        score.get("useTier") == "ready_for_codex_review"
                        and (maps_to != "seed_roster" or source_tier == "S")
                    ),
                }
                rows_by_report[report_key].append(row)

    reports: dict[str, dict] = {}
    for report_key, filename in OUT_FILENAMES.items():
        rows = rows_by_report.get(report_key, [])
        rows.sort(key=lambda r: (-int(r["readyForCodexReview"]), -(r["qualityScore"] or 0), r["teamId"]))
        ready_count = sum(1 for r in rows if r["readyForCodexReview"])
        reports[report_key] = {
            "generatedAt": generated_at,
            "note": (
                "外部データ検証候補から、出典URL付きでフィールドに対応付けられた候補のみを抜き出した"
                "変更提案レポートです。seed/能力値/戦術値/ロスターへの直接反映は一切行っていません。"
                "Codexのレビューを経て、別の反映spec/スクリプトで初めて適用してください。"
            ),
            "proposalKind": report_key,
            "candidateCount": len(rows),
            "readyForCodexReviewCount": ready_count,
            "proposalOnlyCount": len(rows) - ready_count,
            "excludedTierCCount": excluded_tier_c,
            "excludedNoResolvableUrlCount": excluded_no_url,
            "excludedUnmappedFieldCount": excluded_unmapped,
            "proposals": rows,
        }
    return reports


def main() -> int:
    candidates_path = latest_report("external_data_verification_candidates_*.json")
    if candidates_path is None:
        raise SystemExit("external data verification candidate report is missing")

    candidate_report = load_json(candidates_path)
    teams_seed = load_seed_json("teams.json")
    players_seed = load_seed_json("players.json")
    official_seed = load_seed_json("players2026_official.json")
    ratings_seed = load_seed_json("playerRatings2026_estimated.json")

    reports = build_proposals(candidate_report, teams_seed, players_seed, official_seed, ratings_seed)

    for report_key, filename in OUT_FILENAMES.items():
        out_path = REPORTS_DIR / filename
        out_path.write_text(json.dumps(reports[report_key], indent=2, ensure_ascii=False), encoding="utf-8")
        report = reports[report_key]
        print(
            f"Wrote {out_path} "
            f"(candidates={report['candidateCount']} ready={report['readyForCodexReviewCount']} "
            f"proposalOnly={report['proposalOnlyCount']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
