# Progress

## Current Operating Model

- Codex owns product direction, data policy, simulation-quality review, and implementation specs.
- Claude Code owns implementation and test execution.
- The user should not be asked for routine implementation approvals.
- Claude Code should commit Ready-task work after passing verification, then report.
- For longer implementation runs, Claude Code should follow `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`.

## Current Priority

Continue unattended progress with a larger Claude Code task focused on data quality visibility, encoding guardrails, and UI trust polish.

Completed:

- `docs/specs/001-lint-fix.md`
- `docs/specs/003-match-detail-trust-states.md`
- `docs/specs/004-simulator-prediction-panel.md`
- `docs/specs/005-tournament-odds-panel.md`
- `docs/specs/006-overnight-data-trust-sprint.md`
- Spec 007A official squad merge proposal, commit `ebe4064`
- `docs/specs/008-official-squad-safe-field-apply.md`
- `docs/specs/009-official-squad-match-quality.md`
- Spec 009 follow-up: applied official-profile fields for newly matched players and cleaned PDF ligature artifacts.
- Product polish: verified and cleaned Japanese copy across home, tournament, simulator, bracket, match cards, and match detail; expanded prediction API mojibake regression checks.
- Tournament odds transparency: Monte Carlo API now exposes data confidence and method explanation; frontend displays it and remains compatible with older local API responses.

Primary task:

- `docs/specs/010-unattended-site-quality-sprint.md`
- This is intentionally larger than prior tasks so Claude Code can keep working without asking for frequent new specs.

Direction-only context:

- `docs/specs/002-match-detail-v2-direction.md`
- `docs/specs/007-official-squad-data-update-direction.md`

## Verification Baseline

Last known baseline from Codex inspection after Spec 009 follow-up:

- Backend tests: `144 passed`
- Frontend build: passed
- Frontend lint: passed
- Local backend: responding on port 8000
- Local frontend: responding on `localhost:5173`
- Browser smoke check: `/teams/BRA` desktop and mobile width passed; official club/caps-goals fields visible; no full-page horizontal overflow detected.
- Browser smoke check: `/`, `/tournament`, `/simulate`, and a generated match detail page passed; no replacement characters, no halfwidth-kana mojibake, and no full-page horizontal overflow detected.
- Browser smoke check: tournament odds panel calculation renders without blank-page failure even when an older local backend response lacks the new explanation fields.
- Production frontend/backend: responding with HTTP 200

## Open Risks

- Do not ask the user for routine implementation or commit approval.
- Claude Code should continue through the overnight sprint phases without routine user confirmation.
- Match Detail v2 beyond trust states should not be implemented until a concrete follow-up spec is written.
- Player/manager data updates must be evidence-based and should not rely on unverifiable claims.
- FIFA Official Squad List diff report parses 48 teams and 26 official players per team. Current seed has roster drift for all 48 teams and coach mismatches for 16 teams; seed updates need a separate reviewed import spec.
- Spec 008 applied 2,360 safe official-profile fields across 472 existing matched players, with no skipped conflicts, no missing IDs, and no players added or removed.
- Spec 009 improved conservative name matching and regenerated read-only official squad reports. After PDF ligature cleanup, remaining roster risk is now 652 official players and 73 seed players unmatched by the current heuristic, down from 776 and 197.
- Spec 009 follow-up applied official-profile fields for newly matched players. Compared with the previous commit, 124 players gained official profile data; 624 official-profile field values changed in total, including cleanup of PDF `fi` ligature extraction artifacts. The regenerated merge proposal now has 0 matched-player field update candidates.
- All backend JSON files currently scan clean for control characters.
- Prediction API disclaimer/explanation tests now check a broader set of mojibake markers.
- Round of 32 third-place assignment uses candidate-pool constraint solving, not the literal FIFA Annex C 495-row table.

## Next After Current Task

Next Codex actions:

1. Decide later whether/how to resolve remaining unmatched official/seed players.
2. Keep formula changes frozen until an explicit calibration spec exists.
3. Prepare the next product-facing improvement after data trust, likely match detail v2 depth or tournament simulation explanation.
