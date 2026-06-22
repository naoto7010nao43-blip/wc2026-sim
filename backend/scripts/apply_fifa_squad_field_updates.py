"""Apply only safe, matched-player field updates from the FIFA squad
merge proposal.

This script is intentionally narrow:
- it updates existing players only, by exact playerId
- it only fills fields that are currently null
- it never adds or removes players
- it records conflicts instead of overwriting non-null values

Usage:
    ./venv/Scripts/python.exe scripts/apply_fifa_squad_field_updates.py
    ./venv/Scripts/python.exe scripts/apply_fifa_squad_field_updates.py --proposal backend/reports/fifa_squad_merge_proposal_2026-06-22.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DEFAULT_PROPOSAL_PATH = REPORTS_DIR / "fifa_squad_merge_proposal_2026-06-22.json"
DEFAULT_OUTPUT_NAME = "fifa_squad_field_updates_applied"
SAFE_FIELDS = ("dateOfBirth", "heightCm", "clubName", "caps", "nationalTeamGoals")
FIFA_SOURCE_NAME = "FIFA Official Squad feed"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _proposal_timestamp(proposal: dict, fallback: str) -> str:
    return proposal.get("generatedAt") or fallback


def _update_metadata(metadata: dict, timestamp: str, now: str) -> dict:
    updated = dict(metadata)
    updated["lastUpdated"] = now
    sources = []
    source_found = False
    for source in metadata.get("sources", []):
        next_source = dict(source)
        if next_source.get("name") == FIFA_SOURCE_NAME:
            next_source["status"] = "active"
            next_source["lastChecked"] = timestamp
            source_found = True
        sources.append(next_source)
    if not source_found:
        sources.append({
            "name": FIFA_SOURCE_NAME,
            "tier": "S",
            "lastChecked": timestamp,
            "status": "active",
        })
    updated["sources"] = sources
    return updated


def apply_updates(
    proposal_path: Path = DEFAULT_PROPOSAL_PATH,
    seed_dir: Path = SEED_DIR,
    reports_dir: Path = REPORTS_DIR,
    now: str | None = None,
) -> tuple[dict, list[dict], dict]:
    """Return (report, updated_players, updated_metadata)."""
    now = now or _now_iso()
    proposal = _load_json(proposal_path)
    players_path = seed_dir / "players2026_official.json"
    metadata_path = seed_dir / "metadata.json"
    players = _load_json(players_path)
    metadata = _load_json(metadata_path)

    original_player_ids = [p["playerId"] for p in players]
    players_by_id = {p["playerId"]: p for p in players}
    applied_by_field: Counter[str] = Counter()
    touched_player_ids: set[str] = set()
    skipped_conflicts: list[dict] = []
    missing_player_ids: list[str] = []
    ignored_unsafe_fields: list[dict] = []

    proposal_updates = proposal.get("matchedPlayerFieldUpdates", [])
    total_field_updates_read = 0
    for entry in proposal_updates:
        player_id = entry["playerId"]
        proposed = entry.get("proposedUpdates", {})
        player = players_by_id.get(player_id)
        if player is None:
            missing_player_ids.append(player_id)
            continue

        for field, value in proposed.items():
            total_field_updates_read += 1
            if field not in SAFE_FIELDS:
                ignored_unsafe_fields.append({"playerId": player_id, "field": field, "value": value})
                continue
            current = player.get(field)
            if current is None:
                player[field] = value
                applied_by_field[field] += 1
                touched_player_ids.add(player_id)
            elif current != value:
                skipped_conflicts.append({
                    "playerId": player_id,
                    "field": field,
                    "current": current,
                    "proposed": value,
                })

    updated_player_ids = [p["playerId"] for p in players]
    no_players_added_or_removed = original_player_ids == updated_player_ids
    updated_metadata = _update_metadata(metadata, _proposal_timestamp(proposal, now), now)

    report = {
        "generatedAt": now,
        "sourceProposal": str(proposal_path),
        "totalProposalEntriesRead": len(proposal_updates),
        "totalFieldUpdatesRead": total_field_updates_read,
        "playersTouched": len(touched_player_ids),
        "touchedPlayerIds": sorted(touched_player_ids),
        "fieldsAppliedByFieldName": dict(sorted(applied_by_field.items())),
        "totalFieldsApplied": sum(applied_by_field.values()),
        "skippedConflicts": skipped_conflicts,
        "missingPlayerIds": sorted(set(missing_player_ids)),
        "ignoredUnsafeFields": ignored_unsafe_fields,
        "originalPlayerCount": len(original_player_ids),
        "updatedPlayerCount": len(updated_player_ids),
        "noPlayersAddedOrRemoved": no_players_added_or_removed,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    return report, players, updated_metadata


def write_outputs(
    report: dict,
    players: list[dict],
    metadata: dict,
    seed_dir: Path = SEED_DIR,
    reports_dir: Path = REPORTS_DIR,
) -> Path:
    _write_json(seed_dir / "players2026_official.json", players)
    _write_json(seed_dir / "metadata.json", metadata)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = reports_dir / f"{DEFAULT_OUTPUT_NAME}_{stamp}.json"
    _write_json(report_path, report)
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", default=str(DEFAULT_PROPOSAL_PATH), help="Merge proposal JSON path")
    args = parser.parse_args()

    report, players, metadata = apply_updates(Path(args.proposal))
    report_path = write_outputs(report, players, metadata)

    print(f"Proposal entries read: {report['totalProposalEntriesRead']}")
    print(f"Fields applied: {report['totalFieldsApplied']}")
    print(f"Players touched: {report['playersTouched']}")
    print(f"Skipped conflicts: {len(report['skippedConflicts'])}")
    print(f"Missing player IDs: {len(report['missingPlayerIds'])}")
    print(f"No players added or removed: {report['noPlayersAddedOrRemoved']}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
