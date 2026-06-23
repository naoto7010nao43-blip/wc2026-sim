# Rank75 Team Strength Formula Implementation - 2026-06-23

## Change

Changed the production team-strength blend from:

- FIFA rank signal: 60%
- squad strength signal: 40%

to:

- FIFA rank signal: 75%
- squad strength signal: 25%

The model version was bumped from `poisson-v1` to `poisson-v2-rank75`.

## Why

The preceding read-only audits showed:

- small player-level rating probes reduced watchlist implausibility by 0;
- top-team seed/rating values are compressed versus FIFA-rank signal;
- the aggregation sandbox found `rank75_current_squad25` as the best tested variant.

## Before / After

Comparison report:

- `backend/reports/prediction_benchmark_comparison_rank75_2026-06-23.json`

Benchmark report after the change:

- `backend/reports/prediction_benchmark_rank75_2026-06-23.json`

Key deltas versus the frozen `prediction_benchmark_baseline_2026-06-23.json`:

| Metric | Delta |
| --- | ---: |
| Overall average favorite win probability | +0.7pp |
| Overall implausible favorite count | -6 |
| Minimum favorite win probability | +0.6pp |
| Maximum favorite win probability | +1.2pp |
| Watchlist implausible reduction | 5 |

Watchlist improvements:

- ARG: -2 implausible cases
- ESP: -1 implausible case
- NED: -1 implausible case
- POR: -1 implausible case

No warning was emitted by the benchmark comparison gate.

## Scope

Changed:

- `backend/app/prediction/ratings.py`
- `backend/app/prediction/model_config.py`

Not changed:

- seed player data
- player rating data
- manager data
- simulation engine event generation
- frontend UI

## Product Judgment

This is a conservative accuracy fix. It trusts FIFA rank slightly more when squad ratings are compressed, while still preserving the squad layer as a meaningful 25% part of team strength.

This should improve top-team plausibility immediately without the risk of hand-editing many individual player values from incomplete evidence.

