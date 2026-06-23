# Rating Decision Audit - 2026-06-23

## Purpose

Spec 014 added a useful player-level rating review workbench, but that workbench is intentionally not a permission slip to edit ratings. This Codex audit adds a second gate before any data-changing spec:

- keep candidates that align with the model's measured matchup weakness;
- block candidates that would move an underperforming team in the wrong direction;
- separate candidates whose source trail looks too soft or future-looking for direct use;
- avoid any numeric rating proposal until the evidence and benchmark gates are satisfied.

The audit is read-only. It does not change seed data, ratings, formulas, or prediction behavior.

## Inputs

- `backend/reports/rating_review_workbench_2026-06-23.json`
- `backend/reports/matchup_driver_audit_2026-06-23.json`

## Output

- `backend/reports/rating_decision_audit_2026-06-23.json`

Overall bucket counts:

| Bucket | Count | Meaning |
| --- | ---: | --- |
| `candidate_for_later_proposal` | 9 | Possible input to a future bounded proposal, still requires evidence review. |
| `source_review_first` | 8 | Candidate references soft or risky source markers and must be checked before use. |
| `do_not_use_for_upgrade_proposal` | 42 | Usually downgrade-oriented candidates for teams already underperforming the FIFA-rank benchmark. |
| `monitor_only` | 21 | Useful context, but not aligned enough for a rating-change proposal. |

## Team Readout

| Team | Dominant Negative Driver | Later Proposal Candidates | Source Review First | Blocked For Upgrade Proposal |
| --- | --- | ---: | ---: | ---: |
| CRO | defense | 2 | 2 | 4 |
| NED | defense | 0 | 0 | 6 |
| POR | defense | 0 | 0 | 9 |
| MEX | attack | 2 | 3 | 0 |
| MAR | attack | 1 | 2 | 2 |
| URU | defense | 1 | 0 | 5 |
| ESP | defense | 0 | 0 | 10 |
| ARG | defense | 3 | 1 | 6 |

## Candidate Examples

Potential later proposal candidates:

- CRO: Mateo Kovacic, Mario Pasalic
- MEX: Raul Jimenez, Orbelin Pineda
- MAR: Sofyan Amrabat
- URU: Fernando Muslera
- ARG: Rodrigo De Paul, Nicolas Otamendi, Leandro Paredes

Source-review-first examples:

- CRO: Martin Baturina, Luka Modric
- MEX: Santiago Gimenez, Raul Rangel, Edson Alvarez
- MAR: Issa Diop, Soufiane Rahimi
- ARG: Lionel Messi

## Product Judgment

Spec 014 successfully created the review surface, but the raw candidate set is too noisy for direct rating edits. The important discovery is that many high-visibility candidates are downgrade-oriented even though the team-level model audit says the team is already too weak versus the FIFA-rank benchmark. Those candidates should not feed an upgrade proposal.

The next responsible step is not to change ratings yet. The next step should be a source-provenance and proposal-readiness pass that checks whether the remaining 9 proposal candidates and 8 source-risk candidates have acceptable evidence. Only after that should a bounded numeric proposal be generated and run through the prediction benchmark comparison gate.

