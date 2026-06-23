# Rating Update Proposal Gate

## Purpose

This gate defines what must exist before Codex approves any player-rating data change.

The project has enough diagnostics to identify likely rating issues, but a future update must still be bounded, evidence-backed, and benchmarked. No agent should directly edit `playerRatings2026_estimated.json` without passing this gate.

## Required Artifacts

Before a data-changing rating spec:

1. Player-level workbench report
   - `backend/reports/rating_review_workbench_*.json`
2. Prediction before-state
   - `backend/reports/prediction_benchmark_baseline_*.json`
3. Matchup driver audit
   - `backend/reports/matchup_driver_audit_*.json`
4. Proposed rating-change JSON
   - must pass `backend/scripts/validate_rating_update_proposal.py`
5. Prediction after-state and comparison
   - regenerate `prediction_benchmark_baseline_*.json` after applying a branch/local draft
   - compare with `backend/scripts/compare_prediction_benchmarks.py`

## Hard Limits

- Overall or positionOverall change: max 5 points per player per proposal.
- Attribute change: max 8 points per field per proposal.
- No source tier C.
- Every changed field needs evidence references and a reason.
- The benchmark comparison must pass before the proposal can be considered.
- Large proposals should be split when possible.

## Required Validator

Run:

```powershell
cd backend
.\venv\Scripts\python.exe scripts\validate_rating_update_proposal.py path\to\proposal.json
```

The validator checks:

- required proposal shape
- allowed rating fields
- bounded numeric deltas
- source tier
- evidence references
- duplicate player/field changes
- passing benchmark comparison

## Codex Decision Rule

Passing the validator is necessary but not sufficient. Codex still reviews whether the proposed changes are product-appropriate and whether the UI remains honest about data confidence.

If the benchmark improves watchlist teams but globally shifts favorite probabilities too much, stop and redesign the proposal instead of tuning formulas.
