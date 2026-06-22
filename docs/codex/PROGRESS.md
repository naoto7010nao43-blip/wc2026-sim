# Progress

## Current Operating Model

- Codex owns product direction, data policy, simulation-quality review, and implementation specs.
- Claude Code owns implementation and test execution.
- The user should not be asked for routine implementation approvals.
- Claude Code should commit Ready-task work after passing verification, then report.
- For longer implementation runs, Claude Code should follow `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`.

## Current Priority

Continue unattended progress after applying safe official squad fields.

Completed:

- `docs/specs/001-lint-fix.md`
- `docs/specs/003-match-detail-trust-states.md`
- `docs/specs/004-simulator-prediction-panel.md`
- `docs/specs/005-tournament-odds-panel.md`
- `docs/specs/006-overnight-data-trust-sprint.md`
- Spec 007A official squad merge proposal, commit `ebe4064`
- `docs/specs/008-official-squad-safe-field-apply.md`

Primary task:

- None active for Claude Code. Codex is preparing the next task.

Direction-only context:

- `docs/specs/002-match-detail-v2-direction.md`
- `docs/specs/007-official-squad-data-update-direction.md`

## Verification Baseline

Last known baseline from Codex inspection during Spec 008:

- Backend tests: `134 passed`
- Frontend build: passed
- Frontend lint: passed
- Local backend: responding on port 8000
- Local frontend: responding on `localhost:5173`
- Browser smoke check: `/teams/BRA` desktop and mobile width passed; official club/caps-goals fields visible; no full-page horizontal overflow detected.
- Production frontend/backend: responding with HTTP 200

## Open Risks

- Do not ask the user for routine implementation or commit approval.
- Claude Code should continue through the overnight sprint phases without routine user confirmation.
- Match Detail v2 beyond trust states should not be implemented until a concrete follow-up spec is written.
- Player/manager data updates must be evidence-based and should not rely on unverifiable claims.
- FIFA Official Squad List diff report parses 48 teams and 26 official players per team. Current seed has roster drift for all 48 teams and coach mismatches for 16 teams; seed updates need a separate reviewed import spec.
- Spec 008 applied 2,360 safe official-profile fields across 472 existing matched players, with no skipped conflicts, no missing IDs, and no players added or removed.
- Remaining roster risk: 776 official players and 197 seed players are still unmatched by the current heuristic.
- Round of 32 third-place assignment uses candidate-pool constraint solving, not the literal FIFA Annex C 495-row table.

## Next After Current Task

Next Codex actions:

1. Prepare the next unattended task, likely matching-quality improvement before adding/removing official squad players.
2. Decide later whether/how to resolve the 776 unmatched official players and 197 unmatched seed players.
3. Keep formula changes frozen until an explicit calibration spec exists.
