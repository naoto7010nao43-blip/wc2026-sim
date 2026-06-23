# Rating Probe Sensitivity - 2026-06-23

## Purpose

This is a read-only sensitivity check for the 9 clean later-proposal candidates identified by the Codex rating decision audit. It asks whether a tiny hypothetical +2 bump to each candidate's overall and driver-relevant attributes would improve the prediction benchmark.

This is not a rating proposal. It does not change seed data, ratings, formulas, or prediction behavior.

## Added Artifacts

- `backend/scripts/build_rating_probe_sensitivity.py`
- `backend/reports/rating_probe_sensitivity_2026-06-23.json`
- `backend/tests/test_build_rating_probe_sensitivity.py`

## Probe Design

For each clean later-proposal candidate:

- add +2 to `overall` and `positionOverall` in memory only;
- add +2 to driver-relevant attributes in memory only;
- rebuild the deterministic top-20 benchmark sample;
- compare the probe benchmark against `prediction_benchmark_baseline_2026-06-23.json`.

Applied probe candidates:

- CRO: Mateo Kovacic, Mario Pasalic
- MEX: Raul Jimenez, Orbelin Pineda
- MAR: Sofyan Amrabat
- URU: Fernando Muslera
- ARG: Rodrigo De Paul, Nicolas Otamendi, Leandro Paredes

## Result

The probe did not reduce watchlist implausibility.

Key deltas:

| Metric | Delta |
| --- | ---: |
| Overall average favorite win probability | -0.1pp |
| Implausible favorite count | 0 |
| Minimum favorite win probability | +0.2pp |
| Watchlist implausible reduction | 0 |

Team-level watchlist deltas were also small:

- CRO minimum favorite win probability: +0.2pp
- MEX minimum favorite win probability: +0.7pp
- MAR minimum favorite win probability: -0.7pp
- ARG minimum favorite win probability: -0.2pp
- NED, POR, ESP, URU: effectively unchanged

## Product Judgment

The current clean player-level candidates are not enough to fix the model's benchmark concerns. This means the next precision work should not rush into numeric player edits.

More valuable next investigations:

- whether top teams have enough starter-level seed players in the correct positions;
- whether `attack_rating`, `defense_rating`, or `team_strength_rating` underweight elite players or over-rely on squad averages;
- whether starting probability and likely XI selection should feed the prediction benchmark more directly;
- whether benchmark floors are too strict for certain rank gaps.

Future rating edits can still happen, but this probe says they should be treated as data-cleanup work, not as the main fix for benchmark underperformance.

