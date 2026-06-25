# Current Task

Read first:

- `docs/codex/ROLE_SPLIT.md`
- `docs/codex/HANDOFF_PROTOCOL.md`
- `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`
- `docs/codex/DATA_GOVERNANCE_POLICY.md`

## Active Claude Code Task

None. Awaiting the next Codex-authored Ready spec in `docs/specs/CURRENT_TASK.md`.

Claude Code completed Spec 017 in full (48/48 teams, 346 URL-backed candidates) and worked through Spec 018 Phases 0-7 autonomously while Codex was unavailable (2026-06-25): repaired source traceability for the original 16-team batch (121/346 -> 1/346 missing resolvable URLs), built 4 data-change proposal reports, applied exactly one safe verified factual update (Uruguay fifa_rank 14->16) after holding two genuinely conflicting/overtaken candidates for Codex's judgment, added a substitution-profile prototype to the match engine (neutral-default-preserving, fully tested, not yet wired to real per-team data), re-ran the full diagnostics suite with a confirmed no-regression check, and fixed one stale diagnostic (`substitution_model_gap_audit`) that the engine prototype itself had made inaccurate. See `docs/codex/PROGRESS.md`'s "Current Priority" entries dated 2026-06-25 for full detail on every phase, including two items explicitly held for Codex review rather than auto-resolved: a genuine source conflict on Tunisia's manager identity, and a pre-existing benchmark-methodology number (43 vs a stale report's 27) that needs the "status: pass" framing updated, not a regression.

Phase 8 (release candidate preparation) completed. Phase 9 (production push/deploy): `git push origin master` succeeded as a clean fast-forward (`62dd339..88be2b4`); Vercel deployed correctly. The Render backend deploy genuinely succeeded too (confirmed via the user checking the Render dashboard's Events tab directly) -- **the actual bug was not Render at all**, it was in this session's own Phase 4 work: `app/rating_v2/seed_pipeline_v2.py` makes `scripts/seed_db.py` seed the live database from `teams2026_official.json`'s `fifaRank` field whenever the v2 official/estimated data files are present (they are), not from `teams.json`'s `fifa_rank` -- and `adb1ff7`'s `apply_external_factual_updates.py` only ever wrote to `teams.json`. So Uruguay's corrected `fifa_rank` never reached the file the live app actually reads, on any deploy. Fixed by extending `apply_external_factual_updates.py` with `apply_updates_v2()` (same idempotent safety pattern, mirrors `SAFE_UPDATES` into `teams2026_official.json` too) and re-running it; also hardened `app/main.py`/`scripts/seed_db.py` with `sync_reference_data()` so Team/Player rows always resync from the current seed JSON on every startup rather than only when the table happens to be empty (defense-in-depth, confirmed safe since nothing in the app mutates Team/Player rows at runtime). Full local gate re-verified (393 backend tests passed, frontend lint/build clean, encoding audit passed). See `docs/codex/PROGRESS.md`'s Spec 018 Phase 9 entries for the full investigation trail, including the now-ruled-out Render-infrastructure hypotheses. **Flagged for Codex, not fixed today:** `teams.json` (read directly by diagnostics/benchmark scripts) and `teams2026_official.json` (read by the live app when present) are two independently-maintained sources of truth for the same fields with nothing enforcing they stay in sync -- a real architecture decision (unify the loaders, or generate one file from the other) is needed to prevent this exact class of bug from recurring.

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
- `docs/specs/018-claude-full-delivery-sprint.md` (Phases 0-7 complete; Phase 8/9 in progress -- see "Handoff Notes For Codex" above)

Context-only older direction docs:

- `docs/specs/002-match-detail-v2-direction.md`
- `docs/specs/007-official-squad-data-update-direction.md`
