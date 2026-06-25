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
longer safe for, or no longer need, blind automation:
  - Qatar's fifa_rank candidate (recorded old=42 -> new=56) is already
    satisfied: the live seed already reads 56, the proposed new value, so
    there is nothing to apply. The old-value-match guard would skip it as a
    no-op regardless. Already-at-target candidates are not re-applied.
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

# players.json is the legacy-layer equivalent of teams.json: a snake_case
# mirror of a subset of players2026_official.json's fields. The live app seeds
# players from the v2 layer (players2026_official.json + the separate
# playerRatings2026_estimated.json, see app/rating_v2/seed_pipeline_v2.py), NOT
# from players.json -- players.json is read only by the diagnostics/benchmark
# scripts. So, exactly like teams.json, it is regenerated from the v2 official
# file every run and guarded by a consistency test, so it can never silently
# drift from the production source the way teams.json's fifa_rank once did.
PLAYERS_PATH = SEED_DIR / "players.json"
PLAYERS_V2_PATH = SEED_DIR / "players2026_official.json"
LEGACY_PLAYER_FIELD_FROM_V2 = {
    "id": "playerId",
    "team_id": "teamId",
    "name": "name",
    "age": "age",
    "primary_position": "primaryPosition",
    "secondary_positions": "secondaryPositions",
    "career_stats": "careerStats",  # nested keys translated via CAREER_STATS_LEGACY_FROM_V2
    "market_value_eur": "marketValueEur",
    "qualitative_adjustments": "qualitativeAdjustments",
    "source_citations": "sourceCitations",
    "stamina_max": "staminaMax",
    "name_ja": "nameJa",
}
LEGACY_PLAYER_FIELD_ORDER = list(LEGACY_PLAYER_FIELD_FROM_V2.keys())
# Ordered so the goalkeeper-only stats (save_pct, goals_conceded_per90) land
# last, matching the existing players.json layout exactly; outfielders simply
# omit those two keys (they are absent from their v2 careerStats too).
CAREER_STATS_LEGACY_FROM_V2 = {
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

# Conflicts raised in an earlier pass of this script that have since been
# resolved by fresh live verification, kept here (rather than silently
# deleted) so the audit trail of how/why the conflict closed is not lost.
RESOLVED_CONFLICTS: list[dict[str, Any]] = [
    {
        "teamId": "TUN",
        "field": "manager_name",
        "resolution": (
            "Both prior claims were correct for their own point in time, not "
            "conflicting: Lamouchi succeeded Trabelsi in January 2026 (CAF "
            "official/FIFA.com, Tier S, dated 2026-01), then Tunisia sacked "
            "Lamouchi mid-tournament after their opening loss to Sweden and "
            "named Herve Renard as manager on 2026-06-16 (confirmed live via "
            "FIFA.com, World Soccer Talk, and Wikipedia on 2026-06-26). The "
            "2026-06-25 research's Tier-S sources simply predated the in-"
            "tournament change. teams.json's current value (\"Herve Renard\") "
            "is already correct; no data change was needed."
        ),
        "sources": [
            {
                "name": "FIFA.com",
                "url": "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/tunisia-sabri-lamouchi-coach",
                "tier": "S",
            },
            {
                "name": "World Soccer Talk",
                "url": "https://worldsoccertalk.com/world-cup/who-is-tunisias-new-head-coach-at-the-2026-world-cup/",
                "tier": "S",
            },
        ],
    },
    {
        "teamId": "GHA",
        "field": "fifa_rank",
        "resolution": (
            "The candidate's recorded old=61 was itself inaccurate, not overtaken: "
            "FIFA's own official ranking page (inside.fifa.com) confirms the last "
            "official list, dated 2026-06-11, placed Ghana at 73rd pre-tournament -- "
            "matching the live seed's 72 closely (within ordinary source/rounding "
            "variance, not a real discrepancy worth chasing). The candidate's new=65 "
            "is an unofficial post-match 'live ranking' projection following Ghana's "
            "Panama win (Al Jazeera/GhanaSoccerNet/Flashscore, 2026-06-18-26), not yet "
            "a finalized FIFA list entry -- FIFA's site states the next official "
            "update is not until 2026-07-20. Applying an unofficial projected number "
            "now would violate this project's no-speculative-data policy. teams.json's "
            "current value (72) is left unchanged; recommend a fresh check once the "
            "2026-07-20 official list is published."
        ),
        "sources": [
            {
                "name": "FIFA.com (official ranking page)",
                "url": "https://inside.fifa.com/fifa-world-ranking/GHA",
                "tier": "S",
            },
            {
                "name": "World Soccer Talk",
                "url": "https://worldsoccertalk.com/world-cup/what-is-ghanas-current-fifa-ranking-ahead-of-its-2026-world-cup-match-vs-england/",
                "tier": "A",
            },
        ],
    },
]

HELD_FOR_REVIEW: list[dict[str, Any]] = []


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


def _legacy_career_stats(v2_career_stats: dict) -> dict:
    """Snake_case mirror of a v2 careerStats block, preserving the canonical
    key order. Any v2 inner key with no legacy name is carried over verbatim
    rather than dropped, so a future stat can never be silently lost from the
    legacy file even though it would arrive un-renamed."""
    out = {
        legacy_key: v2_career_stats[v2_key]
        for legacy_key, v2_key in CAREER_STATS_LEGACY_FROM_V2.items()
        if v2_key in v2_career_stats
    }
    known_v2 = set(CAREER_STATS_LEGACY_FROM_V2.values())
    out.update({k: v for k, v in v2_career_stats.items() if k not in known_v2})
    return out


def regenerate_legacy_players_json(players_v2: list[dict], existing_players: list[dict] | None = None) -> list[dict]:
    """players.json counterpart of regenerate_legacy_teams_json(): derives the
    legacy players.json shape from players2026_official.json by field-name
    translation only -- no value changes to the fields both files represent.
    Like the teams version, any existing per-player key not in
    LEGACY_PLAYER_FIELD_ORDER is carried over unchanged from existing_players
    rather than silently dropped, so a legacy-only annotation (should one ever
    be added) survives regeneration."""
    existing_by_id = {
        p["id"]: p for p in (existing_players or []) if isinstance(p, dict) and p.get("id")
    }
    legacy_players = []
    for player in players_v2:
        row: dict[str, Any] = {}
        for legacy_key in LEGACY_PLAYER_FIELD_ORDER:
            v2_key = LEGACY_PLAYER_FIELD_FROM_V2[legacy_key]
            if legacy_key == "career_stats":
                row[legacy_key] = _legacy_career_stats(player.get(v2_key) or {})
            else:
                row[legacy_key] = player.get(v2_key)
        existing = existing_by_id.get(row["id"], {})
        row.update({k: v for k, v in existing.items() if k not in LEGACY_PLAYER_FIELD_ORDER})
        legacy_players.append(row)
    return legacy_players


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

    # players.json is likewise a generated mirror of players2026_official.json
    # whenever the v2 layer exists -- regenerate it every run so it can never
    # silently drift from the production source the diagnostics scripts read.
    if PLAYERS_V2_PATH.exists():
        players_v2 = load_json(PLAYERS_V2_PATH)
        existing_players = load_json(PLAYERS_PATH) if PLAYERS_PATH.exists() else []
        write_json(PLAYERS_PATH, regenerate_legacy_players_json(players_v2, existing_players))

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
        "resolvedConflictCount": len(RESOLVED_CONFLICTS),
        "applied": applied,
        "skipped": skipped,
        "appliedV2": applied_v2,
        "skippedV2": skipped_v2,
        "heldForReview": HELD_FOR_REVIEW,
        "resolvedConflicts": RESOLVED_CONFLICTS,
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
