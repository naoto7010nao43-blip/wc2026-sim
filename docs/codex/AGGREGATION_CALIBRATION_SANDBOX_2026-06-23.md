# Aggregation Calibration Sandbox - 2026-06-23

## Purpose

The previous audits showed two things:

- small player-level rating probes did not reduce watchlist implausibility;
- top teams' seed/rating layer is compressed versus their FIFA-rank signal.

This sandbox compares alternate team-strength aggregation formulas in memory only. It does not change production model code, seed data, ratings, formulas, or prediction behavior.

## Added Artifacts

- `backend/scripts/build_aggregation_calibration_sandbox.py`
- `backend/reports/aggregation_calibration_sandbox_2026-06-23.json`
- `backend/tests/test_build_aggregation_calibration_sandbox.py`

## Variants Compared

| Variant | Watchlist Implausible Reduction | Overall Avg Favorite Win Delta | Status |
| --- | ---: | ---: | --- |
| `rank70_current_squad30` | 3 | +0.4pp | pass |
| `rank75_current_squad25` | 4 | +0.6pp | pass |
| `rank65_elite_squad35` | 2 | +0.2pp | pass |
| `rank70_elite_squad30` | 3 | +0.4pp | pass |

Best sandbox variant: `rank75_current_squad25`.

## Product Judgment

The strongest safe candidate is a conservative shift from the current 60/40 FIFA-rank/squad-strength blend to 75/25. It directly targets the observed compression problem while keeping the overall benchmark movement small.

This is a better immediate accuracy fix than editing a handful of individual players, because the player-level +2 probe reduced watchlist implausibility by 0, while the 75/25 aggregation sandbox reduced it by 4.

Recommended implementation, if proceeding:

- change only the team-strength blend in `app/prediction/ratings.py`;
- name the weights as constants so future calibration is explicit;
- bump `DEFAULT_MODEL_CONFIG.model_version`;
- regenerate the prediction benchmark after the change;
- compare before/after against `prediction_benchmark_baseline_2026-06-23.json`;
- run the full backend and frontend verification gate.

