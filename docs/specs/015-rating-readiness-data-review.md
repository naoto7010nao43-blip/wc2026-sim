# Spec 015 - Rating Readiness Data Review

Status: Ready for Claude Code implementation

Owner split:

- Codex owns product/data/simulation judgment.
- Claude Code owns implementation and verification.

## Objective

Turn the new Codex rating-governance artifacts into a useful `/data-review` experience so the site can show, in Japanese, whether player-rating changes are ready, blocked, or require source review.

This is still a review/diagnostic feature. Do not change player ratings, seed player data, manager data, formulas, simulation behavior, or prediction outputs.

## Context

Claude completed Spec 014 and produced the rating review workbench. Codex then added two read-only audit layers:

- `475f170` - rating decision audit
  - `backend/scripts/build_rating_decision_audit.py`
  - `backend/reports/rating_decision_audit_2026-06-23.json`
  - `docs/codex/RATING_DECISION_AUDIT_2026-06-23.md`
- `93a1127` - source provenance audit
  - `backend/scripts/build_source_provenance_audit.py`
  - `backend/reports/source_provenance_audit_2026-06-23.json`
  - `GET /api/model-diagnostics/source-provenance-audit`
  - `docs/codex/SOURCE_PROVENANCE_AUDIT_2026-06-23.md`

The important product judgment is:

- The raw Spec 014 candidate list is useful but too noisy for rating edits.
- Only 9 candidates are clean enough for a future bounded proposal.
- 42 candidates should not be used for upgrade proposals because they are downgrade-oriented for teams already underperforming the benchmark.
- 8 candidates need source review first.

## Required Implementation

### Phase 1 - Expose rating decision audit API

Add a read-only API endpoint:

- `GET /api/model-diagnostics/rating-decision-audit`

It should serve the latest `backend/reports/rating_decision_audit_*.json`.

Follow the existing model-diagnostics pattern:

- add Pydantic schemas in `backend/app/schemas/model_diagnostics.py`;
- add a service reader in `backend/app/services/model_diagnostics.py`;
- add a route in `backend/app/api/model_diagnostics.py`;
- return a calm empty state if the report is missing;
- do not compute or mutate data inside the service.

Add backend tests covering:

- endpoint returns 200 and expected top-level fields;
- top team row shape is stable;
- missing report fallback;
- read-only behavior;
- Japanese-copy guard for any user-facing `note`, `reason_ja`, `recommendations_ja`, or similar fields.

### Phase 2 - Add frontend types/API methods

Add TypeScript types for:

- `RatingDecisionAuditSummary`;
- decision team rows;
- decision candidates;
- `SourceProvenanceAuditSummary` and its nested rows, matching the API already added by Codex.

Add API client methods:

- `getRatingDecisionAudit()`;
- `getSourceProvenanceAudit()`.

### Phase 3 - Add `/data-review` panels

Add two compact but information-dense panels to `/data-review`:

1. `RatingDecisionAuditPanel`
   - show total bucket counts;
   - show the 8 team rows with:
     - dominant negative driver;
     - later-proposal candidate count;
     - source-review-first count;
     - blocked count;
   - show a short list of later-proposal candidates, grouped by team;
   - show blocked/downgrade-oriented candidates as "変更候補から除外" or equivalent calm Japanese wording;
   - avoid implying that any player is definitely wrong.

2. `SourceProvenanceAuditPanel`
   - show seed-wide source-risk count, e.g. `59 / 669`;
   - show decision-candidate counts:
     - total candidates;
     - clear later-proposal candidates;
     - source-review candidates;
   - show risk marker counts;
   - show source-review candidates with marker/severity and Japanese reason;
   - show the Japanese recommendations.

Design constraints:

- Match the existing `/data-review` dashboard style.
- Keep cards compact; do not nest cards inside cards.
- Use Japanese copy only in UI.
- Do not show raw English notes as primary user-facing explanation.
- Use small labels, tables, or dense rows. This is an operational review tool, not a marketing page.
- Desktop and mobile must have no horizontal page scroll.

### Phase 4 - Verification

Run:

- `cd backend && .\venv\Scripts\python.exe -m pytest`
- `cd backend && .\venv\Scripts\python.exe scripts\audit_text_encoding.py`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

Then browser-check with Playwright or the existing smoke method:

- `/data-review` at desktop width around 1280px;
- `/data-review` at mobile width around 390px;
- confirm no console errors;
- confirm no mojibake;
- confirm no horizontal page scroll;
- confirm the new panels render useful content when reports exist;
- confirm missing-report UI is calm if you test it with a temp reports dir or service unit tests.

## Stop Conditions

Stop and report to Codex instead of guessing if:

- the report schema in `rating_decision_audit_*.json` is insufficient to render the panel;
- adding the panel would require changing rating data, formulas, seeds, or simulation behavior;
- Japanese text appears corrupted in the browser even though lint/build pass;
- a backend or frontend verification command fails and the fix is not local to this spec.

## Commit

If all verification passes, commit locally with a concise message such as:

`Add rating readiness review panels`

Do not push.

