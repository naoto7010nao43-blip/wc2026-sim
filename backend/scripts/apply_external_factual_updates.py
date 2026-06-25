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


def update_metadata_freshness(metadata: dict, checked_at: str) -> dict:
    metadata["lastUpdated"] = checked_at
    for source in metadata.get("sources", []):
        if isinstance(source, dict) and source.get("name") == "FIFA World Ranking (fifa_rank field)":
            source["lastChecked"] = checked_at
    return metadata


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()

    teams = load_json(TEAMS_PATH)
    applied, skipped = apply_updates(teams, SAFE_UPDATES)

    if applied:
        write_json(TEAMS_PATH, teams)
        metadata = load_json(METADATA_PATH)
        update_metadata_freshness(metadata, generated_at)
        write_json(METADATA_PATH, metadata)

    report = {
        "generatedAt": generated_at,
        "note": (
            "外部データ検証候補から、出典と現在のseed値の両方を人が直接確認した、"
            "安全かつ確定的に適用可能な事実項目のみを反映した適用レポートです。"
            "推測による値の生成は行っていません。"
        ),
        "appliedCount": len(applied),
        "skippedCount": len(skipped),
        "heldForReviewCount": len(HELD_FOR_REVIEW),
        "applied": applied,
        "skipped": skipped,
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
