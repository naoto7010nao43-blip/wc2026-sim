# Team Rating Component Audit - 2026-06-23

## Purpose

The rating probe sensitivity check showed that small player-level bumps to the 9 clean candidates do not materially improve the benchmark. This audit breaks the team-strength model into components to find the next precision target.

No seed data, ratings, formulas, or prediction behavior were changed.

## Added Artifacts

- `backend/scripts/build_team_rating_component_audit.py`
- `backend/reports/team_rating_component_audit_2026-06-23.json`
- `backend/tests/test_build_team_rating_component_audit.py`

## Main Findings

Top-20 flag counts:

| Flag | Count |
| --- | ---: |
| `few_elite_seed_players_for_top_15_team` | 11 |
| `best_xi_overall_low_for_top_ranked_team` | 7 |
| `rank_signal_far_above_squad_strength` | 3 |
| `thin_attacking_seed_depth` | 1 |
| `attack_component_below_neutral` | 1 |
| `defense_component_below_neutral` | 1 |

Watchlist-specific flag counts:

| Flag | Count |
| --- | ---: |
| `few_elite_seed_players_for_top_15_team` | 7 |
| `best_xi_overall_low_for_top_ranked_team` | 2 |
| `rank_signal_far_above_squad_strength` | 2 |
| `thin_attacking_seed_depth` | 1 |

Examples:

- ARG: FIFA rank 1, rank score 95.0, squad strength 61.1, 70+ overall players 0
- POR: FIFA rank 5, squad strength 64.8, 70+ overall players 1
- NED: FIFA rank 7, squad strength 62.9, 70+ overall players 0
- MAR: FIFA rank 8, squad strength 60.7, 70+ overall players 0
- CRO: FIFA rank 10, top XI average 57.4, 70+ overall players 1
- MEX: FIFA rank 14, top XI average 56.5, 70+ overall players 0
- URU: FIFA rank 14, 70+ overall players 0 and thin attacking seed depth

## Product Judgment

The likely bottleneck is not just a few individual rating edits. The current seed/rating scale compresses top-team player quality enough that elite national teams can look too ordinary at the player layer, even when FIFA rank is strong.

This points toward two next workstreams:

1. Data completeness: confirm that top teams have enough starter-level and elite-level players in seed data.
2. Aggregation calibration: inspect whether `squad_strength_rating`, `attack_rating`, `defense_rating`, and the 60/40 rank-squad blend are underweighting elite players or over-penalizing compressed squad averages.

The next data-changing move should wait. A better next engineering task is a read-only calibration sandbox that compares alternate aggregation formulas against the frozen prediction benchmark before any formula is changed.

