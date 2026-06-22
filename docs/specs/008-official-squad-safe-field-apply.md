# Spec 008: Official Squad Safe Field Apply

## Status

Ready for Claude Code implementation.

## Operating Rule

This is a long unattended sprint task. The user will not touch the computer until around noon.

Work through all phases without routine confirmation. Commit when verification passes. Do not ask the user whether to continue, whether the display looks okay, or whether to commit.

If one phase is blocked, document the blocker in `docs/codex/PROGRESS.md`, skip only that blocked phase, and continue to any later phase that is still safe.

## Product/Data Decision

Codex approves applying only the high-confidence, matched-player field updates from the official FIFA squad merge proposal.

Allowed:

- fill existing `null` official-profile fields for already matched seed players
- expose those official-profile fields through API/UI
- regenerate derived rating/seed artifacts when required

Not allowed:

- add unmatched official players
- delete unmatched seed players
- overwrite non-null seed fields
- change simulation formulas
- change player rating formulas
- change market values, career stats, or manual overrides
- push to remote

## Why This Matters

The current seed roster is smaller than the FIFA official 26-player squad list. Spec 007A produced a read-only proposal:

- `backend/reports/fifa_squad_merge_proposal_2026-06-22.json`
- Proposed matched-player field updates: 472
- Unmatched official players: 776
- Unmatched seed players: 197
- Coach mismatches: 16

This spec should safely apply the 472 already-matched field updates first. This improves data credibility without inventing ratings for unmatched/new players.

## Files To Inspect

- `backend/scripts/build_fifa_squad_merge_proposal.py`
- `backend/reports/fifa_squad_merge_proposal_2026-06-22.json`
- `backend/data/seed/players2026_official.json`
- `backend/data/seed/metadata.json`
- `backend/app/rating_v2/seed_pipeline_v2.py`
- `backend/app/models/player.py`
- `backend/app/schemas/player.py`
- `frontend/src/pages/TeamPage.tsx`
- `frontend/src/types/domain.ts`

## Phase 1: Apply Safe Matched Field Updates

Create a script:

- `backend/scripts/apply_fifa_squad_field_updates.py`

Behavior:

1. Read `backend/reports/fifa_squad_merge_proposal_2026-06-22.json` by default.
2. Load `backend/data/seed/players2026_official.json`.
3. For each `matchedPlayerFieldUpdates[]` entry:
   - find the exact `playerId`
   - only update fields listed in `proposedUpdates`
   - only update when the current seed field is `null`
   - if the current value is non-null and differs, record a skipped conflict; do not overwrite
4. Do not add or remove players.
5. Write updated `players2026_official.json`.
6. Update `metadata.json`:
   - mark `FIFA Official Squad feed` as `active`
   - set its `lastChecked` to the proposal/report timestamp if available, otherwise current UTC
   - refresh top-level `lastUpdated`
7. Write an apply report under `backend/reports/`, e.g.
   - `fifa_squad_field_updates_applied_YYYY-MM-DD.json`

Apply report should include:

- total proposal updates read
- players touched
- fields applied by field name
- skipped conflicts
- missing player IDs
- explicit confirmation that no players were added or removed

## Phase 2: Preserve Official Profile Fields In Runtime Data

The website should be able to show these fields after seeding from v2 files.

Add these official-profile fields into `Player.attributes` when `load_v2_seed_data()` builds player rows:

- `dateOfBirth`
- `heightCm`
- `clubName`
- `caps`
- `nationalTeamGoals`

Expose them through `PlayerSummary` and `PlayerOut` as optional snake_case fields:

- `date_of_birth`
- `height_cm`
- `club_name`
- `caps`
- `national_team_goals`

Prefer ORM properties on `Player` that read from `attributes`, following the existing trust-metadata pattern.

Backward compatibility:

- missing fields must serialize as `null`
- legacy data must not crash

## Phase 3: TeamPage UI Upgrade

Update the team roster scan to display official-profile context compactly.

Minimum:

- show club when available
- show caps and national-team goals when available
- keep current columns for position, overall, starting probability, and data confidence
- remain compact and mobile-safe
- do not remove the data-trust panel or likely-lineup panel

Suggested layout:

- On desktop: player name + small club line; columns for position, overall, caps/goals, starting probability, confidence.
- On mobile: allow the existing table/container to scroll or compress cleanly; no full-page horizontal overflow.

## Phase 4: Regenerate Derived Artifacts

After applying seed official fields:

Run:

```bash
cd backend
.\venv\Scripts\python.exe scripts/rebuild_player_ratings_v2.py
```

Reason:

- refresh metadata lastUpdated
- regenerate player rating diff report
- keep derived files in sync

Do not run `seed_db.py` unless needed for a local smoke check; the SQLite DB is ignored and should not be committed.

## Phase 5: Tests

Add focused tests for:

1. apply script does not add or remove players
2. apply script only fills null fields and skips non-null conflicts
3. metadata marks FIFA Official Squad feed active after apply
4. API serializes new official-profile fields when present
5. API serializes legacy/missing fields as null

Keep tests deterministic by using temp files or monkeypatching paths where practical.

## Verification

Run:

```bash
cd backend
.\venv\Scripts\python.exe -m pytest
```

Run:

```bash
cd frontend
npm run lint
npm run build
```

If local servers are running or easy to start, smoke-check:

- `/teams/BRA`
- `/api/teams/BRA`
- `/api/players/BRA_ALISSON`

At minimum verify no horizontal overflow on `/teams/BRA` at a 390px viewport if browser tooling is available. If unavailable, report as skipped.

## Acceptance Criteria

- Existing matched players receive official DOB/height/club/caps/goals where those seed fields were null.
- No unmatched official players are added.
- No seed players are removed.
- Non-null seed fields are never overwritten.
- TeamPage shows official-profile context in the roster scan.
- Backend tests pass.
- Frontend lint/build pass.
- Work is committed locally.

## Commit Policy

Commit when all required verification passes.

Suggested commit message:

```text
Apply safe official squad field updates
```

Do not push.

## Report Back

After committing, report:

- commit hash
- files changed
- number of fields applied
- fields applied by field name
- any skipped conflicts or missing player IDs
- verification results
- smoke checks performed or skipped
- remaining data risks, especially unmatched official/seed players
