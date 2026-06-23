# Benchmark Method Update - 2026-06-24

## Decision

Codex resolved the benchmark-methodology finding reported after Spec 016 by changing synthetic prediction benchmarks to use an order-neutral matchup convention.

The production simulator is unchanged. Real tournament and match simulations still use the fixture order they are given.

## Why

The earlier benchmark assigned the FIFA-better-ranked team as `home` in every synthetic matchup. Because the production Poisson model applies a generic `home_advantage`, that benchmark gave the favorite a rank-correlated bonus that does not exist in real fixture ordering.

This distorted the absolute `implausible_favorite_count` framing. Claude's follow-up check showed the rank75 decision itself was still directionally sound, but the benchmark evidence needed a cleaner method.

## New Method

For each synthetic matchup:

1. Predict the favorite as home.
2. Predict the same favorite as away.
3. Average the favorite win probability, draw probability, opponent win probability, and expected goals across both orders.

Reports mark this as:

- `benchmarkMethod`: `dual_order_average`
- `scope.benchmarkOrderingMethod`: `dual_order_average`

`most_likely_scores` remain in favorite-home order only for readability; probability fields are the order-neutral averages.

## Results

Generated reports:

- `backend/reports/prediction_benchmark_v1_order_neutral_2026-06-23.json`
- `backend/reports/prediction_benchmark_rank75_order_neutral_2026-06-23.json`
- `backend/reports/prediction_benchmark_comparison_rank75_order_neutral_2026-06-23.json`

Order-neutral comparison:

- Status: `pass`
- Model comparison: `poisson-v1-rank60-order-neutral` -> `poisson-v2-rank75-order-neutral`
- Overall implausible favorite delta: `-9`
- Average favorite win probability delta: `+0.8pt`
- Watchlist implausible reduction: `3`

The rank75 calibration remains justified under the corrected benchmark method, while the absolute benchmark counts are now more conservative and no longer depend on assigning stronger teams as home.

## Verification

- Backend: `333 passed, 1 warning`
- Frontend: `npm run lint` passed
- Frontend: `npm run build` passed
- Encoding audit: passed

## Follow-Up

The matchup driver audit still has a `home_order` driver that is rarely useful under favorite-focused diagnostics. It is not product-facing and does not affect the rank75 decision, but a future diagnostic cleanup can either make that audit order-neutral as well or remove the driver category from favorite-underperformance explanations.
