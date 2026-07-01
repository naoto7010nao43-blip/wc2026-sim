"""Build a read-only displayed-XI vs simulated-XI parity audit report."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.engine.state import build_team_state
from app.rating_v2.lineup_builder import build_likely_lineup
from scripts.build_formation_position_fit_audit import build_rosters, load_json

SEED_DIR = ROOT / "data" / "seed"
REPORTS_DIR = ROOT / "reports"


def _lineup_mismatches(displayed: list[dict], simulated: list[dict]) -> list[dict]:
    max_len = max(len(displayed), len(simulated))
    mismatches = []
    for index in range(max_len):
        display_slot = displayed[index] if index < len(displayed) else None
        sim_slot = simulated[index] if index < len(simulated) else None
        display_player_id = display_slot.get("player_id") if display_slot else None
        sim_player_id = sim_slot.get("player_id") if sim_slot else None
        display_position = display_slot.get("slot_position") if display_slot else None
        sim_position = sim_slot.get("slot_position") if sim_slot else None
        if display_player_id != sim_player_id or display_position != sim_position:
            mismatches.append({
                "slotIndex": index,
                "displayedSlotPosition": display_position,
                "simulatedSlotPosition": sim_position,
                "displayedPlayerId": display_player_id,
                "simulatedPlayerId": sim_player_id,
                "displayedName": display_slot.get("name") if display_slot else None,
                "simulatedName": sim_slot.get("name") if sim_slot else None,
            })
    return mismatches


def audit_team(team: dict, roster: list[dict]) -> dict:
    team_id = team["teamId"]
    formation_name = team["defaultFormation"]
    displayed = build_likely_lineup(roster, formation_name)
    simulated_state = build_team_state(team_id, roster, formation_name, attacking_direction=1)
    simulated = [
        {
            "slot_position": player.slot_position,
            "player_id": player.player_id,
            "name": player.name,
        }
        for player in simulated_state.lineup
    ]
    mismatches = _lineup_mismatches(displayed, simulated)
    display_full = len(displayed) == 11
    sim_full = len(simulated) == 11
    return {
        "teamId": team_id,
        "teamName": team.get("name"),
        "defaultFormation": formation_name,
        "rosterSize": len(roster),
        "displayedStarterCount": len(displayed),
        "simulatedStarterCount": len(simulated),
        "parityOk": not mismatches and display_full and sim_full,
        "mismatchCount": len(mismatches),
        "mismatches": mismatches,
        "displayedPlayerIds": [slot["player_id"] for slot in displayed],
        "simulatedPlayerIds": [slot["player_id"] for slot in simulated],
        "reasonJa": (
            "表示される予想スタメンと、試合エンジンが実際に使う先発XIは一致しています。"
            if not mismatches
            else "表示用の予想スタメンとシミュレーション用の先発XIに差分があります。"
        ),
    }


def build_report(seed_dir: Path = SEED_DIR) -> dict:
    teams = load_json(seed_dir / "teams2026_official.json")
    by_team = build_rosters(seed_dir)
    rows = [audit_team(team, by_team.get(team["teamId"], [])) for team in teams]
    mismatch_rows = [row for row in rows if row["mismatchCount"] > 0]
    incomplete_display = [row for row in rows if row["displayedStarterCount"] != 11]
    incomplete_sim = [row for row in rows if row["simulatedStarterCount"] != 11]
    flagged_rows = [row for row in rows if not row["parityOk"]]
    return {
        "generatedAt": datetime.now(UTC).isoformat(),
        "sourceReports": [
            {"name": "teams2026_official", "generatedAt": None},
            {"name": "players", "generatedAt": None},
            {"name": "playerRatings2026_estimated", "generatedAt": None},
        ],
        "note": (
            "チームページの予想スタメンと、シミュレーターが実際に起用する先発XIを同じseedデータから再計算し、"
            "全48チームで一致しているか確認する読み取り専用監査です。seedデータや予測式は変更しません。"
        ),
        "teamCount": len(rows),
        "checkedTeamCount": len(rows),
        "fullParityTeamCount": sum(1 for row in rows if row["parityOk"]),
        "mismatchTeamCount": len(mismatch_rows),
        "mismatchSlotCount": sum(row["mismatchCount"] for row in mismatch_rows),
        "incompleteDisplayedLineupTeamCount": len(incomplete_display),
        "incompleteSimulatedLineupTeamCount": len(incomplete_sim),
        "teams": flagged_rows or rows,
        "recommendationsJa": [
            "mismatchTeamCountが0でない場合、表示と試合エンジンで別の選手が使われているため、公開前に必ず止めてください。",
            "incompleteSimulatedLineupTeamCountが0でない場合、対象チームのロスターまたはdefaultFormationを確認してください。",
            "全チームがparityOk=trueの場合、予想スタメンの外部データ更新はシミュレーション本体にも反映される状態です。",
        ],
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    stamp = datetime.now(UTC).date().isoformat()
    out = REPORTS_DIR / f"lineup_engine_parity_audit_{stamp}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(
        "mismatchTeamCount="
        f"{report['mismatchTeamCount']} incompleteSimulatedLineupTeamCount="
        f"{report['incompleteSimulatedLineupTeamCount']}"
    )


if __name__ == "__main__":
    main()
