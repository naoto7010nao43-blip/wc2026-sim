"""One-time migration: restructures the existing teams.json/players.json
into the v2 official/estimated data layer the user specified, with NO new
research -- every field already present in the existing seed data is
carried over; every field that doesn't exist yet (clubName, caps,
heightCm, injuryStatus, etc.) is left as null with no fabricated values,
per this project's "treat missing as missing" rule.

Writes (all under backend/data/seed/):
  teams2026_official.json
  managers2026_official.json
  players2026_official.json
  manualPlayerOverrides2026.json   (starts empty)
  metadata.json

Safe to re-run -- it's a pure re-derivation from teams.json/players.json,
not an accumulating diff.

Usage: ./venv/Scripts/python.exe scripts/migrate_to_player_data_v2.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rating.seed_pipeline import load_seed_data

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"

CAREER_STATS_KEY_MAP = {
    "appearances": "appearances",
    "goals": "goals",
    "assists": "assists",
    "minutes_played": "minutesPlayed",
    "key_passes_per90": "keyPassesPer90",
    "successful_dribbles_per90": "successfulDribblesPer90",
    "tackles_per90": "tacklesPer90",
    "interceptions_per90": "interceptionsPer90",
    "aerial_duels_won_pct": "aerialDuelsWonPct",
    "pass_completion_pct": "passCompletionPct",
    "save_pct": "savePct",
    "goals_conceded_per90": "goalsConcededPer90",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _migrate_team(t: dict, now: str) -> dict:
    return {
        "teamId": t["id"],
        "teamCode": t["id"],
        "name": t["name"],
        "confederation": t["confederation"],
        "fifaRank": t.get("fifa_rank"),
        "defaultFormation": t["default_formation"],
        "groupId": t.get("group_id"),
        "tacticalProfile": t.get("tactical_profile"),
        "dataConfidence": "official" if t.get("fifa_rank") is not None else "missing",
        "lastUpdated": now,
    }


def _migrate_manager(t: dict, now: str) -> dict:
    profile = t.get("tactical_profile") or {}
    name = profile.get("manager_name")
    return {
        "managerId": f"mgr_{t['id'].lower()}",
        "teamCode": t["id"],
        "name": name,
        "dataConfidence": "external" if name else "missing",
        "lastUpdated": now,
    }


def _migrate_career_stats(stats: dict | None) -> dict | None:
    if not stats:
        return None
    return {CAREER_STATS_KEY_MAP.get(k, k): v for k, v in stats.items()}


def _migrate_player(p: dict, now: str) -> dict:
    return {
        "playerId": p["id"],
        "teamId": p["team_id"],
        "teamCode": p["team_id"],
        "name": p["name"],
        "nameJa": p.get("name_ja"),
        "age": p.get("age"),
        "dateOfBirth": None,
        "shirtNumber": None,
        "primaryPosition": p["primary_position"],
        "secondaryPositions": p.get("secondary_positions", []),
        "preferredFoot": "unknown",
        "heightCm": None,
        "weightKg": None,
        "clubName": None,
        "clubCountry": None,
        "leagueName": None,
        "caps": None,
        "nationalTeamGoals": None,
        "marketValueEur": p.get("market_value_eur"),
        "careerStats": _migrate_career_stats(p.get("career_stats")),
        "qualitativeAdjustments": p.get("qualitative_adjustments", {}),
        "sourceCitations": p.get("source_citations", []),
        "staminaMax": p.get("stamina_max", 100),
        # "external" not "official": this roster/stats data is sourced from
        # Transfermarkt/league-stats research (see sourceCitations), not a
        # verified direct feed from FIFA's own publications.
        "dataConfidence": "external",
        "lastUpdated": now,
    }


def _build_metadata(now: str) -> dict:
    return {
        "dataVersion": "2026.2.0",
        "modelVersion": "player-rating-v2",
        "lastUpdated": now,
        "sources": [
            {"name": "Existing project seed data (career stats, market value, source citations)", "tier": "A", "lastChecked": now, "status": "active"},
            {"name": "FIFA Official Squad feed", "tier": "S", "lastChecked": None, "status": "not_yet_integrated"},
            {"name": "FIFA World Ranking (fifa_rank field)", "tier": "S", "lastChecked": now, "status": "active"},
            {"name": "World Football Elo Ratings", "tier": "A", "lastChecked": None, "status": "not_yet_integrated"},
            {"name": "Transfermarkt-derived market values", "tier": "A", "lastChecked": now, "status": "active"},
        ],
        "freshnessPolicy": {
            "officialRosterMaxAgeHours": 24,
            "injuryNewsMaxAgeHours": 12,
            "matchResultMaxAgeHours": 1,
            "fifaRankingMaxAgeDays": 30,
            "eloMaxAgeDays": 7,
            "marketValueMaxAgeDays": 14,
            "clubMinutesMaxAgeDays": 7,
            "playerRatingsMaxAgeDays": 3,
        },
    }


def main():
    teams_raw, players_raw = load_seed_data()
    now = _now_iso()

    teams_out = [_migrate_team(t, now) for t in teams_raw]
    managers_out = [_migrate_manager(t, now) for t in teams_raw]
    players_out = [_migrate_player(p, now) for p in players_raw]
    metadata = _build_metadata(now)

    (SEED_DIR / "teams2026_official.json").write_text(
        json.dumps(teams_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (SEED_DIR / "managers2026_official.json").write_text(
        json.dumps(managers_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (SEED_DIR / "players2026_official.json").write_text(
        json.dumps(players_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    overrides_path = SEED_DIR / "manualPlayerOverrides2026.json"
    if not overrides_path.exists():
        overrides_path.write_text(json.dumps([], indent=2), encoding="utf-8")
    (SEED_DIR / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Migrated {len(teams_out)} teams, {len(managers_out)} managers, {len(players_out)} players.")


if __name__ == "__main__":
    main()
