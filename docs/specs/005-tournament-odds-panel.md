# Spec 005: Tournament Odds Panel

## Status

Ready for Claude Code implementation.

## Product Goal

Make tournament-level simulation accuracy more visible and explainable.

The tournament page should show Monte Carlo odds from the existing backend endpoint so customers can compare a single generated bracket with broader probability estimates.

## Background

Backend already exposes:

- `POST /api/tournament/simulate-monte-carlo`

Response shape is defined in:

- `backend/app/schemas/prediction.py`

The frontend currently runs a single full tournament but does not expose aggregate stage/champion odds.

## Files To Inspect

- `frontend/src/pages/TournamentPage.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/types/domain.ts`
- `backend/app/schemas/prediction.py`
- `backend/app/api/tournament.py`

## Allowed Files To Change

Prefer limiting changes to:

- `frontend/src/pages/TournamentPage.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/types/domain.ts`

Add a small component under `frontend/src/components/` only if it keeps `TournamentPage.tsx` readable.

## Requirements

### 1. Add frontend typing and API client support

Add a TypeScript type matching `TournamentSimulationOut`:

- `iterations`
- `model_version`
- `round_of_32_pct`
- `round_of_16_pct`
- `quarterfinal_pct`
- `semifinal_pct`
- `final_pct`
- `champion_pct`
- `disclaimer`

Add an API client method:

- `simulateTournamentMonteCarlo(opts?: { iterations?: number; seed?: number })`

Use the existing backend endpoint. Do not change backend code.

### 2. Add a tournament odds panel

On `TournamentPage`, add a compact panel for Monte Carlo odds.

Minimum display:

- run button for odds calculation
- loading state
- error state
- iteration count
- model version
- disclaimer
- top champion probabilities
- preferably top final or semifinal probabilities if the UI remains compact

Use team names through existing `TeamBadge` where practical.

### 3. Keep performance safe

Default to a modest iteration count, such as 500 or 1000.

Do not call the Monte Carlo endpoint automatically on page load.

The user should trigger it manually because the endpoint is CPU-heavy and rate-limited.

### 4. Avoid misleading certainty

Label the panel as probability estimates.

Show the backend disclaimer.

Do not imply that the top champion probability is a prediction guarantee.

### 5. Preserve existing tournament flow

Do not change:

- `/api/tournament/run`
- full tournament simulation behavior
- bracket rendering
- group standings rendering
- tournament state restore behavior

## Explicit Non-Goals

- Do not alter Monte Carlo math.
- Do not change backend endpoints.
- Do not auto-run Monte Carlo on every render.
- Do not add charts that require new dependencies.
- Do not push to remote.

## Verification

Run from `frontend/`:

```bash
npm run lint
npm run build
```

If local backend is running, smoke-check:

- `POST http://localhost:8000/api/tournament/simulate-monte-carlo` with a small iteration count
- `http://localhost:5173/tournament`

If local backend is not running, do not block the task solely on that. Report the smoke check as skipped/unavailable.

## Acceptance Criteria

- Tournament page can manually run Monte Carlo odds.
- Odds panel shows top champion probabilities and model/disclaimer metadata.
- It does not auto-run expensive requests.
- Existing full tournament button still works.
- `npm run lint` passes.
- `npm run build` passes.

## Report Back

After implementation and commit, report:

- commit hash
- changed files
- summary
- verification results
- risks or follow-up suggestions
