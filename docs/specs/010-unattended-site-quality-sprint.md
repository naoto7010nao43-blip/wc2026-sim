# Spec 010: Unattended Site Quality Sprint

## Status

Ready for Claude Code implementation.

## Operating Rule

This is a large unattended sprint task intended to keep work moving until noon without user involvement.

Do not ask the user for routine approval, display checks, or commit approval. Work through the phases in order. If one phase is blocked, document the blocker in `docs/codex/PROGRESS.md`, skip only that blocked phase, and continue to later safe phases.

Commit once all completed phases pass verification. Do not push.

## Important Current Context

Codex has already completed and committed:

- `0b59fcd` Apply safe official squad field updates
- `24801b2` Improve official squad name matching
- `1efd9b2` Apply newly matched official squad fields
- `d870312` Polish simulation Japanese copy
- `bd3f3ed` Fix remaining Japanese mojibake
- `bcdb8dc` Explain tournament odds model

Before editing, inspect current `git log --oneline -8` and `git status --short`. Do not duplicate work already present. Do not revert Codex changes.

## Product Goal

Move the site closer to a polished, trustworthy 2026 World Cup simulation product.

Priorities:

1. More trust and explainability for predictions.
2. Better visibility into data freshness and roster coverage.
3. No visible mojibake or broken Japanese.
4. Compact, mobile-safe football UI.
5. No simulation/rating formula changes unless explicitly requested.

## Hard Boundaries

Allowed:

- add read-only data quality summaries from existing seed/report files
- expose read-only quality/trust data through API/UI
- improve copy, empty states, loading states, and responsive layout
- add deterministic audit scripts/tests for text encoding and data quality
- add browser smoke-check notes to `docs/codex/PROGRESS.md`

Not allowed:

- add or delete seed players
- overwrite player/manager ratings
- change simulation formulas
- change rating formulas
- change market values, career stats, or manual overrides
- fetch or invent unverifiable player/manager data
- broad refactors unrelated to the phases
- push to remote

## Phase 1: Text Encoding Guardrail

Add a deterministic guardrail so mojibake does not silently return.

Suggested implementation:

- Add `backend/scripts/audit_text_encoding.py`
- Scan at least:
  - `frontend/src/**/*.ts`
  - `frontend/src/**/*.tsx`
  - `backend/app/**/*.py`
  - `backend/tests/**/*.py`
  - selected `docs/**/*.md`
- Flag:
  - replacement character `�`
  - halfwidth-katakana characters in source UI strings
  - known mojibake markers such as `縺`, `繝`, `莠`, `蜆`, `螟`, `邇`, `謗`
- Allow explicit test marker lines only when they are part of a test asserting mojibake is absent.

Add tests or a documented command.

Acceptance:

- The script exits non-zero if a temporary file/string with mojibake is included in its scan scope.
- The current repository scan passes.

## Phase 2: Data Quality Summary API

Create a read-only data quality summary from existing local files.

Suggested backend endpoint:

- `GET /api/data-quality/summary`

Suggested fields:

- `seed_player_count`
- `seed_team_count`
- `official_profile_players`
- `official_profile_coverage_pct`
- `remaining_unmatched_official_players`
- `remaining_unmatched_seed_players`
- `coach_mismatch_count`
- `matched_player_field_update_candidates`
- `last_seed_update`
- `last_report_update`
- `control_character_issues`
- `notes: string[]`

Sources:

- `backend/data/seed/players2026_official.json`
- `backend/data/seed/teams2026_official.json`
- `backend/data/seed/metadata.json`
- `backend/reports/fifa_squad_merge_proposal_2026-06-22.json`
- `backend/reports/fifa_squad_diff_2026-06-22.json`

Do not mutate any data.

Acceptance:

- Endpoint returns counts matching the current reports:
  - unmatched official players: 652
  - unmatched seed players: 73
  - matched-player field update candidates: 0
- Control-character issues are 0 for current backend JSON files.
- Tests cover normal summary and missing-report fallback.

## Phase 3: Product-Facing Data Quality Panel

Add a compact data quality panel to the home page or tournament page.

Preferred location:

- Home page, below the two mode cards.

Display:

- official profile coverage percentage
- remaining official/seed unmatched counts
- matched update candidates
- last update
- short notes from the API

UX requirements:

- quiet dashboard style, not a marketing card explosion
- mobile-safe
- no nested cards
- no visible implementation instructions
- if API fails, show a calm small fallback instead of raw error text

Acceptance:

- Home page remains the first usable screen.
- Users can understand that the model has real data coverage and remaining roster risk.

## Phase 4: Match Detail Trust Polish

Improve match detail clarity without changing simulation behavior.

Allowed improvements:

- clearer labels for real result / detailed simulation / score prediction
- compact "data state" line near the score
- better empty state when no events are available
- ensure player ratings panel is absent or calm when data is not meaningful
- improve mobile spacing if text wraps awkwardly

Do not change match API, simulator, events, or scoring formulas unless strictly necessary for display.

Acceptance:

- Real result, detailed simulation, and score-only prediction states remain distinct.
- No blank/garbled state for Poisson prediction matches.

## Phase 5: Browser Smoke Checks

Use local servers if available, or start them if needed.

Smoke-check:

- `/`
- `/simulate`
- `/tournament`
- `/teams/BRA`
- one generated match detail page

At desktop width and at least one mobile-ish width, verify:

- no replacement characters
- no halfwidth-katakana mojibake
- no full-page horizontal overflow
- key panels render

Document results in `docs/codex/PROGRESS.md`.

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

Run the new text/data-quality audit command if added.

## Commit Policy

Commit when required verification passes.

Suggested commit message:

```text
Add data quality summary and UI guardrails
```

Do not push.

## Report Back

After committing, report:

- commit hash
- phases completed/skipped
- changed files
- verification results
- browser smoke checks
- remaining risks
