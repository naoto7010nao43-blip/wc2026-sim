# Current Task

Read first:

- `docs/codex/ROLE_SPLIT.md`
- `docs/codex/HANDOFF_PROTOCOL.md`
- `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`

## Active Claude Code Task

Ready: `docs/specs/017-external-data-verification-expansion.md`

Claude Code should continue without routine user confirmation. This is a read-only research/reporting task:

- expand external verification beyond the already-covered teams;
- add substitution-tendency research for all 48 teams where evidence exists;
- write structured candidate reports only;
- do not change seed data, ratings, manager/tactical values, formulas, simulation logic, or UI behavior;
- commit locally when verification passes;
- do not push.

Progress note for Claude Code:

- Codex found and validated a partial JSON report at `backend/reports/external_data_verification_candidates_2026-06-24.json`.
- It currently covers 16 teams: ARG, ESP, ENG, FRA, POR, CRO, NED, MEX, BRA, MAR, BEL, GER, URU, COL, USA, JPN.
- Validation output is committed at `backend/reports/external_data_verification_validation_2026-06-24.json`.
- Validation result: valid=true, 121 candidates, 16 future-engine substitution candidates, 16/16 teams strong signal, 4 warnings.
- Codex added a decision queue at `backend/reports/external_data_decision_queue_2026-06-24.json`: 73 current-field review candidates, 4 warning-hold candidates, 15 future-engine candidates, and 29 provisional-context candidates.
- Codex added a source-traceability audit at `backend/reports/external_source_traceability_audit_2026-06-24.json`: all 121 current candidates are missing resolvable source URLs, so they are useful research signal but blocked for seed/rating/tactical data changes until URL-backed citations are added.
- Continue from the remaining teams listed inside that JSON instead of restarting the already-covered 16.
- For any newly researched team, include a resolvable `url` field for every material source whenever the claim may become a current-field candidate. If a URL cannot be found, keep the item as a review question or provisional context rather than a data-change candidate.

This task intentionally reduces user workload. Stop only on the hard stop conditions in the spec.

Codex hit a usage limit on 2026-06-23; the user authorized Claude Code to work solo for the rest of that day, within Codex's existing policy direction (no new spec invention, no data/rating/formula changes). See `docs/codex/PROGRESS.md` "Current Priority" for the full list of verification/diagnostics-only work done.

The benchmark-methodology finding from that solo pass has now been resolved by Codex: synthetic prediction benchmarks use a dual-order average (`benchmarkMethod=dual_order_average`) so FIFA-better-ranked teams no longer receive a correlated home-advantage bonus. See `docs/codex/BENCHMARK_METHOD_UPDATE_2026-06-24.md`. The rank75 calibration remains justified under the corrected method. No production simulation behavior changed.

Also see `docs/codex/EXTERNAL_DATA_VERIFICATION_CANDIDATES_2026-06-24.md` (new, 2026-06-24): at the user's explicit request, read-only web research across 8 priority teams comparing seed data (manager/formation/tactics/squad) against real-world current status. Several high-priority candidates (missing star players, stale club transfers, a non-selected player still in the seed roster) plus 3 cross-team patterns Codex may want to investigate further. No seed/rating/formula files touched -- purely a candidate document awaiting Codex's review.

Additional policy context:

- `docs/codex/DATA_GOVERNANCE_POLICY.md`

Spec 016 is complete.

Spec 015 is complete.

Spec 014 is complete.

Spec 013 is complete and committed as `b08ed51`. The production release checklist/diagnostic-copy guardrail follow-up is committed as `934df98`.

Spec 012 is complete and committed as `10a3f84`.

Spec 011 is complete.

Spec 010 is complete.

Spec 008 has been implemented and committed by Codex while continuing the unattended sprint.
Spec 009 has been implemented and committed by Codex while continuing the unattended sprint.
Codex also applied the newly safe official-profile fields found by Spec 009 and regenerated reports.

Context only:

- `docs/specs/002-match-detail-v2-direction.md`
- `docs/specs/007-official-squad-data-update-direction.md`

Completed:

- `docs/specs/001-lint-fix.md`
- `docs/specs/003-match-detail-trust-states.md`
- `docs/specs/004-simulator-prediction-panel.md`
- `docs/specs/005-tournament-odds-panel.md`
- `docs/specs/006-overnight-data-trust-sprint.md`
- Spec 007A official squad merge proposal, implemented as commit `ebe4064`
- `docs/specs/008-official-squad-safe-field-apply.md`
- `docs/specs/009-official-squad-match-quality.md`
- Spec 009 follow-up safe field apply for newly matched players
- `docs/specs/010-unattended-site-quality-sprint.md` Phases 1-6, 8, 9, and one Phase-10 cycle (Phase 7 skipped, documented)
- `docs/specs/011-team-data-review-diagnostics.md`
- `docs/specs/012-squad-rating-gap-review.md`
- `docs/specs/013-manager-tactical-trust-review.md`
- `docs/specs/014-rating-review-workbench.md`
- `docs/specs/015-rating-readiness-data-review.md`
- `docs/specs/016-model-calibration-transparency.md`

When Codex adds a new Ready task here, follow the autonomous sprint protocol and commit when the spec passes its verification commands.
