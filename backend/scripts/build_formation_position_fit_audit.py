"""Build a read-only formation / position-fit audit report.

The simulator now uses the same starting-XI selector as the displayed likely
lineup. That makes `defaultFormation` accuracy more important: a poor
formation can force sourced starters into unnatural slots. This script audits
that risk without changing seed data or prediction behavior.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.engine.formations import FORMATIONS
from app.engine.lineup_selection import select_starting_assignments

SEED_DIR = ROOT / "data" / "seed"
REPORTS_DIR = ROOT / "reports"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_rosters(seed_dir: Path = SEED_DIR) -> dict[str, list[dict]]:
    players = load_json(seed_dir / "players.json")
    ratings = {row["playerId"]: row for row in load_json(seed_dir / "playerRatings2026_estimated.json")}
    by_team: dict[str, list[dict]] = defaultdict(list)
    for player in players:
        rating = ratings.get(player["id"], {})
        by_team[player["team_id"]].append({
            "id": player["id"],
            "name": player["name"],
            "name_ja": player.get("name_ja"),
            "primary_position": player["primary_position"],
            "secondary_positions": player.get("secondary_positions") or [],
            "overall": rating.get("overall", player.get("overall", 50)),
            "attributes": {"startingProbability": rating.get("startingProbability")},
            "stamina_max": player.get("stamina_max") or 90,
        })
    return by_team


def position_fits_slot(player: dict, slot_position: str) -> bool:
    primary = player.get("primary_position")
    if primary == slot_position or slot_position in (player.get("secondary_positions") or []):
        return True
    # The single holding slot in e.g. a 4-3-3 is labelled CDM but is a natural
    # home for a central midfielder, so a CM filling a CDM slot is genuine
    # positional fit, not an out-of-position placement worth flagging. (The
    # reverse -- a specialist CDM/CAM pushed into a CM slot, or a winger into a
    # flat wide-mid role -- is still surfaced for review.)
    if slot_position == "CDM" and primary == "CM":
        return True
    return False


def severity_band(score: float) -> str:
    if score >= 12:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def recommended_action(out_of_position_count: int, low_probability_count: int) -> str:
    if out_of_position_count >= 3:
        return "formation_or_roster_review"
    if out_of_position_count > 0:
        return "monitor_position_flex"
    if low_probability_count > 0:
        return "roster_depth_review"
    return "no_action"


def recommended_action_ja(action: str) -> str:
    labels = {
        "formation_or_roster_review": "フォーメーションまたは不足ポジションを出典付きで再確認してください。",
        "monitor_position_flex": "隣接ポジション起用の範囲として監視し、断定的な変更は避けてください。",
        "roster_depth_review": "低い先発確率の選手が先発するため、該当ポジションのロスター深度を確認してください。",
        "no_action": "現時点で大きなフォーメーション適合リスクは検出されていません。",
    }
    return labels[action]


def audit_team(team: dict, roster: list[dict]) -> dict:
    team_id = team["teamId"]
    formation_name = team["defaultFormation"]
    assignments = select_starting_assignments(roster, formation_name)
    out_of_position = []
    low_probability = []
    for index, slot in enumerate(FORMATIONS[formation_name].slots):
        player = assignments.get(index)
        if player is None:
            out_of_position.append({
                "slotPosition": slot.position,
                "playerId": None,
                "name": None,
                "primaryPosition": None,
                "secondaryPositions": [],
                "startingProbability": None,
                "overall": None,
                "reasonJa": "このスロットに割り当て可能な選手が不足しています。",
            })
            continue
        starting_probability = (player.get("attributes") or {}).get("startingProbability")
        if not position_fits_slot(player, slot.position):
            out_of_position.append({
                "slotPosition": slot.position,
                "playerId": player["id"],
                "name": player["name"],
                "primaryPosition": player["primary_position"],
                "secondaryPositions": player.get("secondary_positions") or [],
                "startingProbability": starting_probability,
                "overall": player.get("overall"),
                "reasonJa": "選手の主ポジション・副ポジションが割り当てスロットと一致していません。",
            })
        if starting_probability is None or starting_probability < 40:
            low_probability.append({
                "slotPosition": slot.position,
                "playerId": player["id"],
                "name": player["name"],
                "primaryPosition": player["primary_position"],
                "startingProbability": starting_probability,
                "overall": player.get("overall"),
                "reasonJa": "先発確率が低い選手がフォーメーション上の先発枠に入っています。",
            })

    score = len(out_of_position) * 3 + len(low_probability)
    action = recommended_action(len(out_of_position), len(low_probability))
    return {
        "teamId": team_id,
        "teamName": team.get("name"),
        "defaultFormation": formation_name,
        "rosterSize": len(roster),
        "starterCount": len(assignments),
        "outOfPositionCount": len(out_of_position),
        "lowProbabilityStarterCount": len(low_probability),
        "severityScore": score,
        "severityBand": severity_band(score),
        "outOfPositionAssignments": out_of_position,
        "lowProbabilityStarters": low_probability,
        "recommendedAction": action,
        "recommendedActionJa": recommended_action_ja(action),
    }


def build_report(seed_dir: Path = SEED_DIR) -> dict:
    teams = load_json(seed_dir / "teams2026_official.json")
    by_team = build_rosters(seed_dir)
    rows = [audit_team(team, by_team.get(team["teamId"], [])) for team in teams]
    rows.sort(key=lambda row: (-row["severityScore"], row["teamId"]))
    band_counts = Counter(row["severityBand"] for row in rows)
    return {
        "generatedAt": datetime.now(UTC).isoformat(),
        "sourceReports": [
            {"name": "teams2026_official", "generatedAt": None},
            {"name": "players", "generatedAt": None},
            {"name": "playerRatings2026_estimated", "generatedAt": None},
        ],
        "note": (
            "表示用の予想スタメンとシミュレーターの先発XIが同じになったため、"
            "defaultFormationが選手を不自然なスロットへ押し込んでいないかを読み取り専用で監査します。"
            "このレポートはseedデータや予測式を変更しません。"
        ),
        "teamCount": len(rows),
        "flaggedTeamCount": sum(1 for row in rows if row["severityScore"] > 0),
        "highSeverityTeamCount": band_counts["high"],
        "mediumSeverityTeamCount": band_counts["medium"],
        "lowSeverityTeamCount": band_counts["low"],
        "outOfPositionAssignmentCount": sum(row["outOfPositionCount"] for row in rows),
        "lowProbabilityStarterCount": sum(row["lowProbabilityStarterCount"] for row in rows),
        "teams": rows,
        "recommendationsJa": [
            "複数の選手が不自然なスロットに入るチームは、フォーメーション変更か不足ポジション補強のどちらが妥当かを出典付きで確認してください。",
            "隣接ポジションの単発起用は戦術上の柔軟性である可能性があるため、自動変更せずレビュー対象として扱ってください。",
            "低い先発確率の選手が先発枠に入る場合は、能力値変更より先にロスター深度と実スタメン情報を確認してください。",
        ],
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    stamp = datetime.now(UTC).date().isoformat()
    out = REPORTS_DIR / f"formation_position_fit_audit_{stamp}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(
        "flaggedTeamCount="
        f"{report['flaggedTeamCount']} outOfPositionAssignmentCount={report['outOfPositionAssignmentCount']}"
    )


if __name__ == "__main__":
    main()
