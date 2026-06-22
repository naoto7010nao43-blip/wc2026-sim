"""Checks backend/data/seed/metadata.json's sources/freshnessPolicy and
reports which inputs are stale (or were never wired up at all). Intended
to be run as part of the daily maintenance routine (see
scripts/daily_maintenance_prompt.txt) -- this project has no JS build
step to hook a freshness gate into, so this is a standalone, explicitly
run check rather than an automated CI failure.

Exit code 0 if everything is within policy (or only has "missing
integration" notices), 1 if anything has gone stale past its threshold.

Usage: ./venv/Scripts/python.exe scripts/check_data_freshness.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"

# Maps a metadata.sources[].name to the freshnessPolicy key that governs
# it, and whether that key is expressed in hours or days.
SOURCE_POLICY_MAP = {
    "FIFA Official Squad feed": ("officialRosterMaxAgeHours", "hours"),
    "FIFA World Ranking (fifa_rank field)": ("fifaRankingMaxAgeDays", "days"),
    "World Football Elo Ratings": ("eloMaxAgeDays", "days"),
    "Transfermarkt-derived market values": ("marketValueMaxAgeDays", "days"),
    "Existing project seed data (career stats, market value, source citations)": ("clubMinutesMaxAgeDays", "days"),
}


def _age_hours(iso_timestamp: str) -> float:
    checked = datetime.fromisoformat(iso_timestamp)
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - checked).total_seconds() / 3600.0


def check_freshness(metadata: dict) -> list[dict]:
    findings = []
    policy = metadata.get("freshnessPolicy", {})

    for source in metadata.get("sources", []):
        name = source["name"]
        if source.get("status") == "not_yet_integrated":
            findings.append({"level": "notice", "message": f"{name}: not yet integrated (no live feed wired up)"})
            continue
        last_checked = source.get("lastChecked")
        if not last_checked:
            findings.append({"level": "warning", "message": f"{name}: marked active but has no lastChecked timestamp"})
            continue
        mapping = SOURCE_POLICY_MAP.get(name)
        if mapping is None:
            continue
        policy_key, unit = mapping
        max_age = policy.get(policy_key)
        if max_age is None:
            continue
        age_hours = _age_hours(last_checked)
        max_age_hours = max_age if unit == "hours" else max_age * 24
        if age_hours > max_age_hours:
            findings.append({
                "level": "critical" if unit == "hours" else "warning",
                "message": f"{name}: stale ({age_hours:.1f}h old, max {max_age_hours:.0f}h per {policy_key})",
            })

    last_updated = metadata.get("lastUpdated")
    ratings_max_age_days = policy.get("playerRatingsMaxAgeDays")
    if last_updated and ratings_max_age_days is not None:
        age_hours = _age_hours(last_updated)
        if age_hours > ratings_max_age_days * 24:
            findings.append({
                "level": "warning",
                "message": f"metadata.lastUpdated is {age_hours / 24:.1f} days old (max {ratings_max_age_days} per playerRatingsMaxAgeDays) -- consider re-running rebuild_player_ratings_v2.py",
            })

    return findings


def main() -> int:
    metadata_path = SEED_DIR / "metadata.json"
    if not metadata_path.exists():
        print("metadata.json not found -- run migrate_to_player_data_v2.py first.")
        return 1

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    findings = check_freshness(metadata)

    if not findings:
        print("All data sources within freshness policy.")
        return 0

    for f in findings:
        print(f"[{f['level'].upper()}] {f['message']}")

    return 1 if any(f["level"] == "critical" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
