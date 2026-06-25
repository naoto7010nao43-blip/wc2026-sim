"""Apply a small, explicit, human-curated set of safe factual seed updates.

This script does not parse free text or guess values. Each entry in
SAFE_UPDATES is a fully specified, source-backed (Tier S/A) factual change
that a human (Claude Code, during Spec 018 Phase 4) read directly from the
external verification candidates and confirmed against the live seed before
listing it here. The script only ever applies an update if the seed's
current value still exactly matches the recorded old value -- if the seed
has already changed (by another process) or disagrees with the recorded old
value, the entry is skipped and held for review rather than overwritten.

This intentionally does not attempt every "ready for Codex review" proposal
in external_current_field_change_proposals_2026-06-24.json. Cross-checking
those proposals against the live seed surfaced several cases that are no
longer safe for blind automation:
  - Tunisia's manager_name candidate conflicts with an earlier, independently
    sourced seed edit (commit 268c1fa, 2026-06-22) that says the opposite
    direction of change. This is a genuine source conflict, not staleness;
    held for Codex, not applied.
  - Ghana and Qatar's fifa_rank candidates were already overtaken by other
    edits to live values that match neither the candidate's recorded "old"
    nor "new" number. Already-moved targets are held rather than applied.
  - club_name and team_strength_rating candidates require free-text value
    extraction (the proposal report deliberately does not fabricate a
    structured "new club" value) or do not map to a literal seed field;
    both remain proposal-only pending a follow-up spec with stricter
    extraction or storage rules.

Usage:
  ./venv/Scripts/python.exe scripts/apply_external_factual_updates.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BACKEND_DIR / "data" / "seed"
REPORTS_DIR = BACKEND_DIR / "reports"
TEAMS_PATH = SEED_DIR / "teams.json"
METADATA_PATH = SEED_DIR / "metadata.json"

# When the v2 official/estimated data layer is present, scripts/seed_db.py
# reads team fifa_rank/etc. from THIS file instead of teams.json (see
# app/rating_v2/seed_pipeline_v2.py's v2_files_present()/load_v2_seed_data()).
# A safe update must be mirrored here too, or the live database keeps
# serving the old value forever regardless of how many times teams.json is
# corrected -- this is exactly what happened to Uruguay's fifa_rank update
# during Spec 018 Phase 9 (see docs/codex/PROGRESS.md for the investigation).
#
# Once this file exists, it is the single source of truth for team data:
# teams.json becomes a generated mirror (see regenerate_legacy_teams_json()),
# not an independently hand-maintained copy, so the two files can never
# silently drift apart again.
TEAMS_V2_PATH = SEED_DIR / "teams2026_official.json"
V2_FIELD_NAME = {"fifa_rank": "fifaRank"}
LEGACY_FIELD_FROM_V2 = {
    "teamId": "id",
    "name": "name",
    "confederation": "confederation",
    "fifaRank": "fifa_rank",
    "defaultFormation": "default_formation",
    "groupId": "group_id",
    "tacticalProfile": "tactical_profile",
}
LEGACY_FIELD_ORDER = ["id", "name", "confederation", "fifa_rank", "default_formation", "group_id", "tactical_profile"]

SAFE_UPDATES: list[dict[str, Any]] = [
    {
        "teamId": "URU",
        "field": "fifa_rank",
        "oldValue": 14,
        "newValue": 16,
        "sourceName": "World Soccer Talk",
        "sourceUrl": "https://worldsoccertalk.com/world-cup/uruguays-updated-fifa-ranking-before-2026-world-cup-clash-with-cape-verde/",
        "sourceTier": "S",
        "observedDate": "2026-06",
        "claim": "FIFA rank as of the pre-tournament June 2026 update is 16, not the seed's 14.",
    },
]

HELD_FOR_REVIEW: list[dict[str, Any]] = [
    {
        "teamId": "TUN",
        "field": "manager_name",
        "reason": (
            "conflicting_evidence: 2026-06-22 commit 268c1fa recorded manager_name as "
            "Renard succeeding Lamouchi (sacked mid-tournament 2026-06-15); 2026-06-25 "
            "external research (CAF official, FIFA.com, Tier S) says Lamouchi succeeded "
            "Trabelsi in January 2026 and led Tunisia through the World Cup, with no "
            "mention of Renard managing Tunisia at all. These two Tier-S-sourced claims "
            "directly disagree; needs Codex/human judgment, not automated resolution."
        ),
    },
    {
        "teamId": "GHA",
        "field": "fifa_rank",
        "reason": (
            "value_overtaken: candidate recorded old=61/new=65, but the live seed value "
            "is 72 -- matches neither, so some other edit already moved this field past "
            "what this candidate proposed. Applying either 61 or 65 now would not reflect "
            "the most current known state; needs a fresh source check."
        ),
    },
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def apply_updates(teams: list[dict], updates: list[dict]) -> tuple[list[dict], list[dict]]:
    by_id = {team["id"]: team for team in teams if isinstance(team, dict) and team.get("id")}
    applied = []
    skipped = []
    for update in updates:
        team = by_id.get(update["teamId"])
        if team is None:
            skipped.append({**update, "skipReason": "team_not_found"})
            continue
        current = team.get(update["field"])
        if current != update["oldValue"]:
            skipped.append({**update, "skipReason": "seed_value_changed_since_candidate", "liveValue": current})
            continue
        team[update["field"]] = update["newValue"]
        applied.append({**update, "appliedAt": True})
    return applied, skipped


def apply_updates_v2(teams_v2: list[dict], updates: list[dict]) -> tuple[list[dict], list[dict]]:
    by_id = {team["teamId"]: team for team in teams_v2 if isinstance(team, dict) and team.get("teamId")}
    applied = []
    skipped = []
    for update in updates:
        v2_field = V2_FIELD_NAME.get(update["field"])
        if v2_field is None:
            continue  # this field has no v2-file equivalent to mirror
        team = by_id.get(update["teamId"])
        if team is None:
            skipped.append({**update, "skipReason": "team_not_found_in_v2_file"})
            continue
        current = team.get(v2_field)
        if current != update["oldValue"]:
            skipped.append({**update, "skipReason": "v2_seed_value_changed_since_candidate", "liveValue": current})
            continue
        team[v2_field] = update["newValue"]
        applied.append({**update, "appliedAt": True, "file": "teams2026_official.json"})
    return applied, skipped


def regenerate_legacy_teams_json(teams_v2: list[dict], existing_teams: list[dict] | None = None) -> list[dict]:
    """Derives teams.json's shape from teams2026_official.json, field-name
    translation only -- no value changes to the fields both files represent.
    Once the v2 layer exists, this makes teams.json a generated mirror
    instead of a hand-maintained parallel file, so a future safe update can
    never again reach one file and not the other (see TEAMS_V2_PATH's
    module-level comment).

    teams.json carries at least one field with no v2 equivalent at all --
    `_tactical_profile_basis`, a sourcing note present for 8/48 teams -- so
    this is not a pure field-rename: any existing per-team key not in
    LEGACY_FIELD_ORDER is carried over unchanged from existing_teams rather
    than silently dropped."""
    existing_by_id = {
        t["id"]: t for t in (existing_teams or []) if isinstance(t, dict) and t.get("id")
    }
    legacy_teams = []
    for team in teams_v2:
        legacy_team = {
            LEGACY_FIELD_FROM_V2[v2_key]: team.get(v2_key)
            for v2_key in LEGACY_FIELD_FROM_V2
        }
        ordered = {field: legacy_team[field] for field in LEGACY_FIELD_ORDER}
        existing = existing_by_id.get(legacy_team["id"], {})
        ordered.update({k: v for k, v in existing.items() if k not in LEGACY_FIELD_ORDER})
        legacy_teams.append(ordered)
    return legacy_teams


def update_metadata_freshness(metadata: dict, checked_at: str) -> dict:
    metadata["lastUpdated"] = checked_at
    for source in metadata.get("sources", []):
        if isinstance(source, dict) and source.get("name") == "FIFA World Ranking (fifa_rank field)":
            source["lastChecked"] = checked_at
    return metadata


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()

    applied: list[dict] = []
    skipped: list[dict] = []
    applied_v2: list[dict] = []
    skipped_v2: list[dict] = []

    if TEAMS_V2_PATH.exists():
        # teams2026_official.json is the single source of truth once it
        # exists -- apply there, then regenerate teams.json from it every
        # run (not just when something changed) so the legacy file can never
        # silently drift again, regardless of what future SAFE_UPDATES add.
        teams_v2 = load_json(TEAMS_V2_PATH)
        applied_v2, skipped_v2 = apply_updates_v2(teams_v2, SAFE_UPDATES)
        if applied_v2:
            write_json(TEAMS_V2_PATH, teams_v2)
        existing_teams = load_json(TEAMS_PATH) if TEAMS_PATH.exists() else []
        write_json(TEAMS_PATH, regenerate_legacy_teams_json(teams_v2, existing_teams))
    else:
        teams = load_json(TEAMS_PATH)
        applied, skipped = apply_updates(teams, SAFE_UPDATES)
        if applied:
            write_json(TEAMS_PATH, teams)

    if applied or applied_v2:
        metadata = load_json(METADATA_PATH)
        update_metadata_freshness(metadata, generated_at)
        write_json(METADATA_PATH, metadata)

    report = {
        "generatedAt": generated_at,
        "note": (
            "外部データ検証候補から、出典と現在のseed値の両方を人が直接確認した、"
            "安全かつ確定的に適用可能な事実項目のみを反映した適用レポートです。"
            "推測による値の生成は行っていません。teams2026_official.json"
            "(v2公式データ層)が存在する場合はそちらにも同じ値を反映します。"
        ),
        "appliedCount": len(applied),
        "skippedCount": len(skipped),
        "appliedCountV2": len(applied_v2),
        "skippedCountV2": len(skipped_v2),
        "heldForReviewCount": len(HELD_FOR_REVIEW),
        "applied": applied,
        "skipped": skipped,
        "appliedV2": applied_v2,
        "skippedV2": skipped_v2,
        "heldForReview": HELD_FOR_REVIEW,
    }
    out_path = REPORTS_DIR / "external_factual_updates_applied_2026-06-24.json"
    write_json(out_path, report)
    print(
        f"Wrote {out_path} "
        f"(applied={len(applied)} skipped={len(skipped)} heldForReview={len(HELD_FOR_REVIEW)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
