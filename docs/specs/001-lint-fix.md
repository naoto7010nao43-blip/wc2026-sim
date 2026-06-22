# Spec 001: Frontend Lint Fix

## Status

Ready for Claude Code implementation.

## Goal

Fix the current frontend lint failures without changing user-visible behavior.

## Background

`npm run build` passes, but `npm run lint` currently fails with three errors:

- `frontend/src/context/TeamsContext.tsx`
  - `react-refresh/only-export-components` on exported hooks.
- `frontend/src/pages/MatchDetailPage.tsx`
  - `react-hooks/set-state-in-effect` caused by synchronous `setMatch(null)` inside an effect.

This is a hygiene task. Keep the patch small.

## Files To Inspect

- `frontend/src/context/TeamsContext.tsx`
- `frontend/src/pages/MatchDetailPage.tsx`
- Any directly necessary small helper file if needed.

## Implementation Constraints

- Do not redesign UI.
- Do not change API behavior.
- Do not change simulation logic.
- Do not touch backend files.
- Do not perform broad refactors.
- Keep behavior effectively identical from the user's perspective.

## Expected Approach

For `TeamsContext.tsx`:

- Move non-component exports, such as `useTeamsMap` and `useTeam`, into a separate hook file if that is the smallest clean fix.
- Keep `TeamsProvider` behavior unchanged.

For `MatchDetailPage.tsx`:

- Remove or restructure the synchronous `setMatch(null)` inside the effect.
- Preserve loading behavior when navigating between match pages.
- Avoid introducing stale response races if the route changes while a request is in flight.

## Verification

Run from `frontend/`:

```bash
npm run lint
npm run build
```

Expected result:

- `npm run lint` passes.
- `npm run build` passes.

## Report Back

After implementation, report:

- changed files
- short summary
- lint result
- build result
- any behavior risk noticed
