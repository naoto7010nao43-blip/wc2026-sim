# Rank75 Report Refresh - 2026-06-23

## Purpose

After `poisson-v2-rank75` was implemented, the diagnostics reports that power `/data-review` needed to be regenerated so the site would not display stale `poisson-v1` audit conclusions.

No code, seed data, player ratings, manager data, or formulas were changed in this refresh. It only regenerated read-only reports from the current model.

## Regenerated Reports

- `backend/reports/simulation_accuracy_audit_2026-06-23.json`
- `backend/reports/matchup_driver_audit_2026-06-23.json`
- `backend/reports/team_data_review_plan_2026-06-23.json`
- `backend/reports/squad_rating_gap_review_2026-06-23.json`
- `backend/reports/rating_review_workbench_2026-06-23.json`
- `backend/reports/rating_decision_audit_2026-06-23.json`
- `backend/reports/source_provenance_audit_2026-06-23.json`
- `backend/reports/team_rating_component_audit_2026-06-23.json`

## Notable Changes

`rating_decision_audit` narrowed after the rank75 formula change:

- `candidate_for_later_proposal`: 4
- `source_review_first`: 13
- `do_not_use_for_upgrade_proposal`: 19
- `monitor_only`: 28

The top `/data-review` priority teams also shifted. The first four model/rating priorities remain:

- CRO
- NED
- POR
- MEX

The remaining top-eight slots now include roster/name-review-heavy teams:

- JOR
- BIH
- AUS
- PAR

This is expected: after rank75 improves some top-team plausibility, the residual review queue becomes a mix of model-rating review and roster/name reconciliation.

## Verification

- Backend full suite: 319 passed, 1 warning
- Text encoding audit: passed
- Frontend lint: passed
- Frontend build: passed

