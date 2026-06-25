# Current Task

Read first:

- `docs/codex/ROLE_SPLIT.md`
- `docs/codex/HANDOFF_PROTOCOL.md`
- `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`
- `docs/codex/DATA_GOVERNANCE_POLICY.md`

## Active Claude Code Task

None. Awaiting the next Codex-authored Ready spec in `docs/specs/CURRENT_TASK.md`.

**Spec 017 and Spec 018 are both fully complete, including production push/deploy (2026-06-25).** Full final report: `docs/codex/CLAUDE_FINAL_HANDOFF_2026-06-25.md`. Summary: Claude Code completed Spec 017 in full (48/48 teams, 346 URL-backed candidates), then worked through all of Spec 018's phases autonomously while Codex was unavailable -- repaired source traceability (121/346 -> 1/346 missing resolvable URLs), built 4 data-change proposal reports, applied exactly one safe verified factual update (Uruguay fifa_rank 14->16) after holding two genuinely conflicting/overtaken candidates for Codex's judgment, added a substitution-profile prototype to the match engine (neutral-default-preserving, fully tested, not yet wired to real per-team data), re-ran the full diagnostics suite with a confirmed no-regression check, fixed one stale diagnostic the prototype itself had made inaccurate, prepared a release candidate, and pushed to production.

**Production deploy found and fixed a real bug in this session's own earlier work, not a Render problem:** `app/rating_v2/seed_pipeline_v2.py` makes `scripts/seed_db.py` seed the live database from `teams2026_official.json`'s `fifaRank` field whenever the v2 official/estimated data files are present (they are), not from `teams.json`'s `fifa_rank` -- and the Uruguay fix had only been written to `teams.json`. So the corrected value never reached the file the live app actually reads, on any deploy, and looked at first like a stuck Render deployment. Fixed (commit `b0f2840`) by mirroring the same already-sourced update into `teams2026_official.json` and hardening `app/main.py`'s startup to always resync Team/Player rows from the current seed JSON rather than only when the table happens to be empty. **Verified live after the fix**: `curl https://wc2026-backend-tdih.onrender.com/api/teams` returns Uruguay `fifa_rank: 16`; `scripts/post_deploy_smoke.ps1` against both production URLs returned HTTP 200 on all 20 checks. Full detail and investigation trail: `docs/codex/PROGRESS.md`'s Spec 018 Phase 9 entries, `docs/codex/PRODUCTION_DEPLOYMENT_NOTE_2026-06-25.md`.

**Flagged for Codex, not fixed today:** `teams.json` (read directly by diagnostics/benchmark scripts) and `teams2026_official.json` (read by the live app when present) are two independently-maintained sources of truth for the same fields with nothing enforcing they stay in sync -- this is exactly what caused the production bug above. A real architecture decision (unify the loaders, or generate one file from the other) is needed to prevent this exact class of bug from recurring; recommended as Codex's next priority alongside the Tunisia manager-identity conflict and Ghana's overtaken fifa_rank candidate.

## Critical Worktree Warning

`backend/reports/external_data_verification_candidates_2026-06-24.json` is now complete (48/48 teams) and committed. No in-progress worktree state remains for Spec 017.

## Handoff Notes For Codex

- 5 stale-manager findings from Spec 017 research: Tunisia, Saudi Arabia, Uzbekistan, Czech Republic, Ghana. 4 of 5 (KSA/UZB/CZE/GHA) were already corrected in `teams.json` by an earlier process before this handoff. Tunisia's case is a genuine, unresolved **conflict** between two independently Tier-S-sourced claims (see `backend/reports/external_factual_updates_applied_2026-06-24.json`'s `heldForReview` entry) -- needs a human/Codex decision, not automation.
- A seeded Curacao player, "Gevero Markus" (CB, overall 52), could not be matched to any of Curacao's actual 26-man World Cup squad -- flagged as a possible fabricated/hallucinated seed identity in `docs/codex/CLAUDE_EXTERNAL_DATA_VERIFICATION_FINAL_REPORT_2026-06-25.md`; not auto-corrected.
- `backend/reports/prediction_benchmark_baseline_2026-06-25.json` is the first committed report reflecting the benchmark script's already-installed dual-order-averaging fix; `implausible_favorite_count` is correctly 43 under that methodology, not the stale 06-23 report's single-order-biased 27. The rank75-over-v1 improvement itself was separately confirmed to hold under both orderings.
- 4 new data-change proposal reports (`external_current_field_change_proposals`, `external_rating_change_proposals`, `external_tactical_change_proposals`, `external_roster_change_proposals`, all dated 2026-06-24) are ready for review; only Uruguay's fifa_rank has been applied from them so far.
- The substitution-profile prototype (Spec 018 Phase 5) is implemented and tested but has zero real per-team data; populating it needs a follow-up Codex-reviewed spec (DB column + migration + seed loader from the future-engine decision-queue candidates).

## Autonomy Rules

Claude Code may:

- continue in long batches;
- commit after verification passes;
- proceed from one phase to the next without asking;
- improve UI, diagnostics, reports, tests, and bounded implementation details named in Spec 018;
- create release-candidate notes and final handoff docs.

Claude Code must not:

- delete in-progress work;
- apply URL-less external claims to seed/rating/tactical data;
- apply Tier C claims as data;
- silently mark estimated data as official.

Claude Code must stop before production only if the production target/branch/URLs cannot be determined from local configuration or project docs, or if deployment/post-deploy smoke fails and the safe recovery path is unclear.

## Current Context

The benchmark-methodology issue has already been fixed by Codex with dual-order synthetic benchmarks. The rank75 model remains justified under corrected benchmarking.

The site currently has `/data-review` diagnostics for:

- release readiness;
- model calibration;
- simulation stability;
- external data verification;
- external decision queue;
- source traceability;
- substitution model gap;
- team/squad/manager/rating/source audits.

Use these diagnostics as product surfaces, not just backend reports.

## Reporting

After each committed phase, Claude Code should report:

- commit hash;
- changed files;
- summary;
- verification results;
- data/system changes made;
- remaining risks;
- next phase to continue.

Do not ask the user whether to commit or whether to continue when verification has passed.

## Completed Context

Completed specs:

- `docs/specs/001-lint-fix.md`
- `docs/specs/003-match-detail-trust-states.md`
- `docs/specs/004-simulator-prediction-panel.md`
- `docs/specs/005-tournament-odds-panel.md`
- `docs/specs/006-overnight-data-trust-sprint.md`
- `docs/specs/008-official-squad-safe-field-apply.md`
- `docs/specs/009-official-squad-match-quality.md`
- `docs/specs/010-unattended-site-quality-sprint.md`
- `docs/specs/011-team-data-review-diagnostics.md`
- `docs/specs/012-squad-rating-gap-review.md`
- `docs/specs/013-manager-tactical-trust-review.md`
- `docs/specs/014-rating-review-workbench.md`
- `docs/specs/015-rating-readiness-data-review.md`
- `docs/specs/016-model-calibration-transparency.md`
- `docs/specs/017-external-data-verification-expansion.md`
- `docs/specs/018-claude-full-delivery-sprint.md` (fully complete, all phases 0-9, including production push/deploy and a mid-deploy bug fix -- see `docs/codex/CLAUDE_FINAL_HANDOFF_2026-06-25.md`)

Context-only older direction docs:

- `docs/specs/002-match-detail-v2-direction.md`
- `docs/specs/007-official-squad-data-update-direction.md`
