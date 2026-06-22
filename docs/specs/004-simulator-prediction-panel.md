# Spec 004: Simulator Prediction Panel

## Status

Ready for Claude Code implementation.

## Product Goal

Improve simulation accuracy explainability before the user runs a single-match simulation.

The simulator page should show the model's pre-match prediction for the selected teams, using the existing backend prediction endpoint. This helps customers understand why a simulated result is plausible instead of feeling random.

## Background

Backend already exposes:

- `GET /api/predictions/{home_team_id}/{away_team_id}`

Response shape is defined in:

- `backend/app/schemas/prediction.py`

The frontend currently does not expose this prediction data in the simulator flow.

## Files To Inspect

- `frontend/src/pages/SimulatorPage.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/types/domain.ts`
- `backend/app/schemas/prediction.py`
- `backend/app/api/predictions.py`

## Allowed Files To Change

Prefer limiting changes to:

- `frontend/src/pages/SimulatorPage.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/types/domain.ts`

Add a small component under `frontend/src/components/` only if it keeps the page readable.

## Requirements

### 1. Add frontend typing and API client support

Add a TypeScript type for the existing `MatchPredictionOut` response:

- `home_team_id`
- `away_team_id`
- `home_win_pct`
- `draw_pct`
- `away_win_pct`
- `home_expected_goals`
- `away_expected_goals`
- `most_likely_scores`
- `data_confidence`
- `explanation`
- `model_version`
- `disclaimer`

Add an API client method:

- `getMatchPrediction(homeTeamId, awayTeamId)`

Do not change backend schemas.

### 2. Show prediction panel on SimulatorPage

When two different teams are selected:

- fetch prediction data
- show win/draw probabilities
- show expected goals for both teams
- show the top likely scorelines
- show 2-4 explanation lines from the backend
- show model version and data confidence in compact form
- show the disclaimer in restrained small text

When teams are missing or identical:

- do not fetch
- show no prediction panel or show a compact neutral empty state

### 3. Handle loading and stale responses

When the selected teams change:

- avoid showing stale prediction data for the previous matchup as if it belongs to the new one
- show a small loading state while fetching
- show a compact error state if prediction fetch fails

Use a cancellation flag or request key, similar to the MatchDetail route-change guard.

### 4. Keep UI compact and analytical

This is an analysis feature, not a marketing block.

Use existing visual style:

- slate panels
- emerald/amber accents
- compact grids
- readable on mobile

Do not add a large hero section or unrelated graphics.

### 5. Preserve simulation flow

The existing "run simulation" button and match creation behavior must continue to work.

Do not change:

- `api.simulateMatch`
- backend match simulation
- seed handling
- decisive/no-draw behavior

## Explicit Non-Goals

- Do not change prediction formulas.
- Do not add xG beyond the already returned expected goals.
- Do not invent new explanation text on the client. Use backend explanation/disclaimer.
- Do not add new backend endpoints.
- Do not touch tournament logic.

## Verification

Run from `frontend/`:

```bash
npm run lint
npm run build
```

If local servers are running, sanity-check:

- `http://localhost:5173/simulate`
- selecting two different teams displays a prediction panel
- selecting the same team does not show a misleading prediction
- the run simulation button still navigates to a match detail page

Run backend tests only if backend files were changed. Backend changes are not expected.

## Acceptance Criteria

- Prediction data appears before simulation for valid team pairs.
- Probabilities, expected goals, likely scores, explanations, model version, confidence, and disclaimer are visible.
- Stale prediction data is not shown after team changes.
- Existing single-match simulation still works.
- `npm run lint` passes.
- `npm run build` passes.

## Report Back

After implementation and commit, report:

- commit hash
- changed files
- summary
- verification results
- risks or follow-up suggestions
