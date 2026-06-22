# Progress

## Current Operating Model

- Codex owns product direction, data policy, simulation-quality review, and implementation specs.
- Claude Code owns implementation and test execution.
- The user should not be asked for routine implementation approvals.
- Claude Code should commit Ready-task work after passing verification, then report.
- For longer implementation runs, Claude Code should follow `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`.

## Current Priority

Reduce user handoff work while Codex reviews completed implementation and prepares the next high-value task.

Completed:

- `docs/specs/001-lint-fix.md`
- `docs/specs/003-match-detail-trust-states.md`
- `docs/specs/004-simulator-prediction-panel.md`
- `docs/specs/005-tournament-odds-panel.md`

Primary task:

- None active for Claude Code. Codex is reviewing and planning.

Direction-only context:

- `docs/specs/002-match-detail-v2-direction.md`

## Verification Baseline

Last known baseline from Codex inspection after commit `8b35778`:

- Backend tests: `115 passed`
- Frontend build: passed
- Frontend lint: passed
- Local backend: responding on port 8000
- Local frontend: responding on `localhost:5173`
- Production frontend/backend: responding with HTTP 200

## Open Risks

- Do not ask the user for routine implementation or commit approval.
- Use Claude Code only when Codex has prepared a clear Ready task.
- Match Detail v2 beyond trust states should not be implemented until a concrete follow-up spec is written.
- Player/manager data updates must be evidence-based and should not rely on unverifiable claims.
- Round of 32 third-place assignment uses candidate-pool constraint solving, not the literal FIFA Annex C 495-row table.

## Next After Current Task

Next Codex actions:

1. Continue reducing user handoff overhead.
2. Choose the next high-value spec, likely one of:
   - player/manager data confidence system
   - simulation calibration review
   - Match Detail v2 follow-up
