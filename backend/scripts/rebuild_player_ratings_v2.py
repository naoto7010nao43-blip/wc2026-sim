"""Recomputes playerRatings2026_estimated.json and
managerRatings2026_estimated.json from players2026_official.json /
managers2026_official.json / teams2026_official.json /
manualPlayerOverrides2026.json, via app.rating_v2.player_rating_model /
manager_rating_model. Also writes a diff report (vs. the previous
ratings file, if one exists) to reports/player_rating_diff_<date>.json
and refreshes metadata.json's lastUpdated.

Safe to re-run at any time (e.g. after editing manualPlayerOverrides2026.json
or after players2026_official.json changes).

Usage: ./venv/Scripts/python.exe scripts/rebuild_player_ratings_v2.py
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rating.formulas import POSITION_GROUPS
from app.rating_v2.manager_rating_model import compute_manager_rating_v2
from app.rating_v2.player_rating_model import compute_player_rating_v2

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

LOW_CONFIDENCE_UNCERTAINTY_THRESHOLD = 0.5


def _load(name: str):
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _peer_market_values(players: list[dict]) -> dict[str, list[float]]:
    by_group: dict[str, list[float]] = {}
    for p in players:
        group = POSITION_GROUPS.get(p["primaryPosition"], "MID")
        value = p.get("marketValueEur")
        if value:
            by_group.setdefault(group, []).append(value)
    return by_group


def _overrides_by_player_id(overrides: list[dict]) -> dict[str, dict]:
    return {o["playerId"]: o for o in overrides}


def main():
    players = _load("players2026_official.json")
    teams = _load("teams2026_official.json")
    managers = _load("managers2026_official.json")
    overrides_path = SEED_DIR / "manualPlayerOverrides2026.json"
    overrides = json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.exists() else []

    peer_values_by_group = _peer_market_values(players)
    overrides_by_id = _overrides_by_player_id(overrides)

    previous_ratings_by_id: dict[str, dict] = {}
    ratings_path = SEED_DIR / "playerRatings2026_estimated.json"
    if ratings_path.exists():
        previous_ratings_by_id = {r["playerId"]: r for r in json.loads(ratings_path.read_text(encoding="utf-8"))}

    new_ratings = []
    for p in players:
        group = POSITION_GROUPS.get(p["primaryPosition"], "MID")
        rating = compute_player_rating_v2(p, peer_values_by_group.get(group, []), overrides_by_id.get(p["playerId"]))
        new_ratings.append(rating.to_json_dict())

    team_by_code = {t["teamCode"]: t for t in teams}
    new_manager_ratings = []
    for m in managers:
        team = team_by_code.get(m["teamCode"], {})
        rating = compute_manager_rating_v2(m["managerId"], m["teamCode"], team.get("tacticalProfile"))
        new_manager_ratings.append(rating.to_json_dict())

    ratings_path.write_text(json.dumps(new_ratings, indent=2, ensure_ascii=False), encoding="utf-8")
    (SEED_DIR / "managerRatings2026_estimated.json").write_text(
        json.dumps(new_manager_ratings, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Diff report.
    biggest_risers, biggest_fallers = [], []
    for r in new_ratings:
        prev = previous_ratings_by_id.get(r["playerId"])
        if prev is None:
            continue
        delta = r["overall"] - prev["overall"]
        if delta != 0:
            (biggest_risers if delta > 0 else biggest_fallers).append({
                "playerId": r["playerId"], "delta": delta, "from": prev["overall"], "to": r["overall"],
            })
    biggest_risers.sort(key=lambda x: -x["delta"])
    biggest_fallers.sort(key=lambda x: x["delta"])

    low_confidence_players = [
        {"playerId": r["playerId"], "uncertainty": r["uncertainty"], "dataConfidence": r["dataConfidence"]}
        for r in new_ratings if r["uncertainty"] >= LOW_CONFIDENCE_UNCERTAINTY_THRESHOLD
    ]
    missing_critical_data = [
        r["playerId"] for r in new_ratings if r["dataConfidence"] == "missing"
    ]
    changed_by_manual_override = [
        r["playerId"] for r in new_ratings if r["sourceBreakdown"]["manualOverrideUsed"]
    ]

    report = {
        "generatedAt": _now_iso(),
        "totalPlayers": len(new_ratings),
        "biggestRisers": biggest_risers[:10],
        "biggestFallers": biggest_fallers[:10],
        "changedByManualOverride": changed_by_manual_override,
        "lowConfidencePlayers": low_confidence_players,
        "missingCriticalData": missing_critical_data,
    }
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"player_rating_diff_{date.today().isoformat()}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    metadata_path = SEED_DIR / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["lastUpdated"] = _now_iso()
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Rebuilt {len(new_ratings)} player ratings, {len(new_manager_ratings)} manager ratings.")
    print(f"Low-confidence players (uncertainty >= {LOW_CONFIDENCE_UNCERTAINTY_THRESHOLD}): {len(low_confidence_players)}")
    print(f"Missing-critical-data players: {len(missing_critical_data)}")
    print(f"Diff report written to {report_path}")


if __name__ == "__main__":
    main()
