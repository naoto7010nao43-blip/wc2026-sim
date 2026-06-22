# Progress

## Current Operating Model

- Codex owns product direction, data policy, simulation-quality review, and implementation specs.
- Claude Code owns implementation and test execution.
- The user should not be asked for routine implementation approvals.
- Claude Code should commit Ready-task work after passing verification, then report.
- For longer implementation runs, Claude Code should follow `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`.

## Current Priority

Run a long unattended official squad data sprint.

Completed:

- `docs/specs/001-lint-fix.md`
- `docs/specs/003-match-detail-trust-states.md`
- `docs/specs/004-simulator-prediction-panel.md`
- `docs/specs/005-tournament-odds-panel.md`
- `docs/specs/006-overnight-data-trust-sprint.md`
- Spec 007A official squad merge proposal, commit `ebe4064`

Primary task:

- `docs/specs/008-official-squad-safe-field-apply.md`

Direction-only context:

- `docs/specs/002-match-detail-v2-direction.md`
- `docs/specs/007-official-squad-data-update-direction.md`

## Verification Baseline

Last known baseline from Claude/Codex inspection after commit `ef40525`:

- Backend tests: `130 passed`
- Frontend build: passed
- Frontend lint: passed
- Local backend: responding on port 8000
- Local frontend: responding on `localhost:5173`
- Browser smoke check: `/teams/BRA` desktop and mobile width passed, no horizontal overflow detected.
- Production frontend/backend: responding with HTTP 200

## Open Risks

- Do not ask the user for routine implementation or commit approval.
- Claude Code should continue through the overnight sprint phases without routine user confirmation.
- Match Detail v2 beyond trust states should not be implemented until a concrete follow-up spec is written.
- Player/manager data updates must be evidence-based and should not rely on unverifiable claims.
- FIFA Official Squad List diff report parses 48 teams and 26 official players per team. Current seed has roster drift for all 48 teams and coach mismatches for 16 teams; seed updates need a separate reviewed import spec.
- Spec 008 is allowed to apply only existing matched-player null-field updates from the official proposal; it must not add or remove players.
- Round of 32 third-place assignment uses candidate-pool constraint solving, not the literal FIFA Annex C 495-row table.

## Next After Current Task

Next Codex actions:

1. Let Claude Code implement Spec 008.
2. Codex reviews the resulting applied field report and TeamPage UI.
3. Decide later whether to improve matching for the 776 unmatched official players and 197 unmatched seed players.
4. Keep formula changes frozen until an explicit calibration spec exists.
