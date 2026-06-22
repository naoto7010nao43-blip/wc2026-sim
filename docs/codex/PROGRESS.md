# Progress

## Current Operating Model

- Codex owns product direction, data policy, simulation-quality review, and implementation specs.
- Claude Code owns implementation and test execution.
- The user forwards short trigger messages to Claude Code only when needed.

## Current Priority

Stabilize the implementation workflow before larger product changes.

Primary task:

- `docs/specs/001-lint-fix.md`

Direction-only context:

- `docs/specs/002-match-detail-v2-direction.md`

## Verification Baseline

Last known baseline from Codex inspection:

- Backend tests: `104 passed`
- Frontend build: passed
- Frontend lint: failing with 3 errors
- Local backend: responding on port 8000
- Local frontend: responding on `localhost:5173`
- Production frontend/backend: responding with HTTP 200

## Open Risks

- Frontend lint must be fixed before treating the frontend quality gate as clean.
- Match Detail v2 should not be implemented until a concrete spec is written.
- Player/manager data updates must be evidence-based and should not rely on unverifiable claims.
- Round of 32 third-place assignment uses candidate-pool constraint solving, not the literal FIFA Annex C 495-row table.

## Next After Current Task

After the lint task is complete:

1. Codex reviews Claude Code's changes.
2. Codex reruns or checks `npm run lint` and `npm run build`.
3. Codex decides the next spec, likely one of:
   - Match Detail v2 concrete UI task
   - prediction explainability panel
   - player/manager data confidence system
   - simulation calibration review
