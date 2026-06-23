# Spec 016 - Model Calibration Transparency

Status: Ready for Claude Code implementation

Owner split:

- Codex owns product/data/simulation judgment and formula-change approval.
- Claude Code owns implementation and verification.

## Objective

Expose the newly implemented `poisson-v2-rank75` calibration in a calm, user-facing diagnostic panel so the site explains why the model changed and what the benchmark impact was.

This is a transparency/readout feature. Do not change formulas, seed data, player ratings, manager data, or simulation behavior.

## Context

Codex implemented the formula change in:

- `08be754` - `Calibrate team strength rank blend`

Codex then regenerated diagnostics in:

- `207f99c` - `Refresh diagnostics for rank75 model`

Relevant docs/reports:

- `docs/codex/RANK75_FORMULA_IMPLEMENTATION_2026-06-23.md`
- `docs/codex/RANK75_REPORT_REFRESH_2026-06-23.md`
- `backend/reports/prediction_benchmark_comparison_rank75_2026-06-23.json`
- `backend/reports/prediction_benchmark_rank75_2026-06-23.json`
- `backend/reports/aggregation_calibration_sandbox_2026-06-23.json`

Key benchmark result:

- model version changed to `poisson-v2-rank75`
- overall implausible favorite count improved by 6
- watchlist implausible cases improved by 5
- average favorite win probability moved only +0.7pp
- comparison gate status: `pass`

## Required Implementation

### Phase 1 - Backend summary API

Add a read-only model calibration endpoint:

- `GET /api/model-diagnostics/model-calibration`

It should read the latest relevant local report files:

- `prediction_benchmark_comparison_rank75_*.json`
- `prediction_benchmark_rank75_*.json`
- optionally `aggregation_calibration_sandbox_*.json`

Return a compact summary shape suitable for UI:

- `generatedAt`
- `modelVersionBefore`
- `modelVersionAfter`
- `status`
- `overall`
  - matchup count before/after
  - average favorite win delta
  - implausible favorite count delta
  - minimum/maximum favorite win deltas
- `watchlist`
  - watchlist implausible reduction
  - per-team rows for ARG/ESP/NED/POR/etc. from the comparison
- `bestSandboxVariantId`
- `note`
- `recommendations_ja`

Follow existing `model_diagnostics.py` patterns:

- Pydantic schemas in `backend/app/schemas/model_diagnostics.py`
- service reader in `backend/app/services/model_diagnostics.py`
- route in `backend/app/api/model_diagnostics.py`
- calm empty state if reports are missing
- no calculations that mutate anything
- no formulas or seed files changed

Add backend tests:

- endpoint returns 200 with expected fields
- missing-report fallback
- read-only behavior
- Japanese-copy guard for user-facing `note` / `recommendations_ja`

### Phase 2 - Frontend types/client

Add TypeScript types for the model calibration summary.

Add:

- `api.getModelCalibrationSummary()`

### Phase 3 - `/data-review` panel

Add a compact panel to `/data-review`, placed near the top after the page intro and before the team-data review sections.

Panel name suggestion:

- `ModelCalibrationPanel`

It should show:

- current model: `poisson-v2-rank75`
- gate status: pass/review
- watchlist improvement: `5件改善`
- overall implausible favorite count delta: `-6`
- average favorite win shift: `+0.7pt`
- a small per-team watchlist table for teams with nonzero improvement
- short Japanese explanation that the model now trusts FIFA rank slightly more when local squad ratings are compressed

Copy constraints:

- Japanese only
- do not overclaim that the simulator is "accurate" or "correct"
- phrase as "検証上の改善" / "ベンチマーク上の改善"
- do not show raw English warnings as primary UI text
- keep it compact and operational, not promotional
- no nested cards

### Phase 4 - Verification

Run:

- `cd backend && .\venv\Scripts\python.exe -m pytest`
- `cd backend && .\venv\Scripts\python.exe scripts\audit_text_encoding.py`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

Browser smoke:

- `/data-review` at desktop 1280px
- `/data-review` at mobile 390px
- confirm no console errors
- confirm no mojibake
- confirm no horizontal page scroll
- confirm the model calibration panel renders useful content

## Stop Conditions

Stop and report to Codex if:

- the comparison report shape is insufficient or ambiguous
- implementing this would require changing prediction formulas or seed data
- Japanese text appears corrupted in the browser
- a verification command fails and the fix is outside this spec

## Commit

If all verification passes, commit locally with:

`Add model calibration transparency panel`

Do not push.

