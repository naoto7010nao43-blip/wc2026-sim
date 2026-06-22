# Spec 006: Overnight Data Trust Sprint

## Status

Ready for Claude Code implementation.

## Operating Rule

This is an overnight sprint task. Work through all phases in order without asking the user for routine confirmation.

Commit completed work after verification passes. If one phase becomes blocked, document the blocker in `docs/codex/PROGRESS.md`, skip only that phase, and continue to the next phase when possible.

Do not ask the user:

- whether the display looks okay
- whether to commit
- whether to continue to the next phase
- for wording approval

Ask only if a Stop Condition in `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md` applies and you cannot safely continue with any later phase.

## Product Goal

Improve simulation trust and customer confidence by making the data quality behind players, lineups, and manager tactics visible.

The site should feel more serious: not just "here is a number", but "here is what this number is based on, and how much uncertainty remains."

## Non-Negotiable Boundaries

Do not change:

- match simulation formulas
- Poisson prediction formulas
- Monte Carlo math
- player rating formulas
- manager rating formulas
- seed player values, manager values, market values, or roster facts
- production deployment or remote push behavior

This sprint exposes existing confidence signals and improves UI/wording. It does not invent new data.

## Phase 1: Preserve Rating Trust Metadata In The API

### Context

The v2 rating model already computes metadata such as:

- `uncertainty`
- `dataConfidence`
- `sourceBreakdown`
- `lowConfidenceAttributes`
- `startingProbability`

But the current API mostly exposes legacy player fields, so the frontend cannot explain data trust well.

### Files To Inspect

- `backend/app/rating_v2/types.py`
- `backend/app/rating_v2/legacy_bridge.py`
- `backend/app/rating_v2/seed_pipeline_v2.py`
- `backend/app/models/player.py`
- `backend/app/schemas/player.py`
- `backend/app/schemas/team.py`
- `backend/app/api/teams.py`
- `backend/tests/test_likely_lineup_api.py`
- `backend/tests/test_player_ratings.py`

### Requirements

1. Add rating trust metadata into `Player.attributes` when seeding from v2 ratings.
   - Include at minimum:
     - `dataConfidence`
     - `uncertainty`
     - `sourceBreakdown`
     - `lowConfidenceAttributes`
     - `lastUpdated`
   - Keep existing legacy and v2 skill attributes intact.

2. Extend player API schemas so `TeamOut.players` and `PlayerOut` can expose:
   - `starting_probability`
   - `data_confidence`
   - `uncertainty`
   - `source_breakdown`
   - `low_confidence_attributes`
   - `rating_last_updated`

3. Implement the schema plumbing conservatively.
   - Prefer ORM properties on `Player` that read from the existing `attributes` JSON.
   - Missing fields should return `None` or `[]`, not crash.
   - Preserve backward compatibility with legacy seed data.

4. Add focused backend tests.
   - Verify a player response includes trust fields when attributes contain them.
   - Verify legacy/missing metadata still serializes without failure.

## Phase 2: Add Team Data Trust UI

### Files To Inspect

- `frontend/src/pages/TeamPage.tsx`
- `frontend/src/types/domain.ts`
- `frontend/src/components/LikelyLineupPanel.tsx`
- `frontend/src/components/TeamBadge.tsx`
- `frontend/src/index.css`

### Requirements

1. Update TypeScript types to match the new optional API fields.

2. Add a compact team data trust section to `TeamPage`.

Minimum display:

- manager name, default formation, FIFA rank
- three tactical profile axes if available:
  - press intensity
  - possession style
  - defensive line height
- roster trust summary:
  - count of players by `data_confidence`
  - average uncertainty when available
  - count of players with low-confidence attributes
- a concise note that lineups and ratings are estimates, not official FIFA starting elevens.

3. Add a useful roster scan table/list.

Minimum columns:

- player name
- position
- overall
- starting probability if available
- data confidence if available

Keep it compact and scan-friendly. Do not create a marketing-style hero.

4. Preserve the existing likely lineup panel.

5. Avoid nested card-heavy layouts. Team page should feel like a serious analysis surface.

## Phase 3: Copy/Encoding Sweep

### Requirements

Scan user-facing frontend/backend strings for mojibake remnants from earlier terminal encoding issues.

Focus on:

- `frontend/src/**/*.tsx`
- `backend/app/schemas/**/*.py`
- backend tests that assert user-facing Japanese strings

If a file is actually UTF-8 correct but PowerShell displays it incorrectly, do not change it just because the terminal output looks strange. Use a UTF-8-aware check.

Fix only real mojibake in user-facing strings. Do not churn unrelated copy.

## Verification

Run:

```bash
cd frontend
npm run lint
npm run build
```

Run:

```bash
cd backend
pytest
```

If local servers are already running, smoke-check:

- `/teams/BRA`
- `/api/teams/BRA`
- `/api/players/<one-known-player-id>`

If local servers are not running, do not block only on smoke checks. Report them as skipped.

## Commit Policy

Commit when all verification commands pass.

Suggested commit message:

```text
Expose player data trust metadata on team pages
```

Do not push.

## Acceptance Criteria

- API exposes player trust metadata without breaking legacy/missing data.
- Team page shows a useful trust summary and compact roster scan.
- Existing likely lineup, simulator, tournament, and match detail routes are not intentionally changed.
- No simulation/rating formulas are changed.
- `npm run lint`, `npm run build`, and backend `pytest` pass.

## Report Back

After committing, report:

- commit hash
- changed files
- what was implemented by phase
- verification results
- any skipped smoke checks
- remaining product/data risks
