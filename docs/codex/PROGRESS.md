# Progress

## Current Operating Model

- Codex owns product direction, data policy, simulation-quality review, and implementation specs.
- Claude Code owns implementation and test execution.
- The user forwards short trigger messages to Claude Code only when needed.
- For longer implementation runs, Claude Code should follow `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`.

## Current Priority

Improve the match detail page as the core "watchable football simulation" screen while preserving simulation behavior.

Completed:

- `docs/specs/001-lint-fix.md`

Primary task:

- `docs/specs/003-match-detail-trust-states.md`

Direction-only context:

- `docs/specs/002-match-detail-v2-direction.md`

## Verification Baseline

Last known baseline from Codex inspection after commit `62dd339`:

- Backend tests: `115 passed`
- Frontend build: passed
- Frontend lint: passed
- Local backend: responding on port 8000
- Local frontend: responding on `localhost:5173`
- Production frontend/backend: responding with HTTP 200

## Open Risks

- Match Detail trust-state improvements must not imply missing simulated event/player data is a bug.
- Match Detail v2 beyond trust states should not be implemented until a concrete follow-up spec is written.
- Player/manager data updates must be evidence-based and should not rely on unverifiable claims.
- Round of 32 third-place assignment uses candidate-pool constraint solving, not the literal FIFA Annex C 495-row table.

## Next After Current Task

After the match-detail trust-state task is complete:

1. Codex reviews Claude Code's changes.
2. Codex reruns or checks `npm run lint` and `npm run build`.
3. Codex decides the next spec, likely one of:
   - prediction explainability panel
   - player/manager data confidence system
   - simulation calibration review
