# Current Task

Read first:

- `docs/codex/ROLE_SPLIT.md`
- `docs/codex/HANDOFF_PROTOCOL.md`
- `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`
- `docs/codex/DATA_GOVERNANCE_POLICY.md`

## Active Claude Code Task

**Player rating accuracy (started 2026-06-26, autonomous).** The user reported that player
abilities are poorly reflected on the site. Root cause: the from-scratch estimation pipeline
(`compute_player_rating_v2` -> Stage A/B/C) compresses the top of the scale — before the fix,
pool max was 82 with ZERO players >= 85, and marquee players sat 20-30 points low. Fix: an
external-reference injection path using EA SPORTS FC 26 as a citable Tier-A source (sofifa is
403-blocked). A new seed `data/seed/externalPlayerRatings2026.json` holds EA's overall + six
face stats per player (with source URL + EA id); when present these replace the estimate
verbatim, but all sub-attributes are still derived from that base so the player stays
internally consistent. Marked `dataConfidence="external"` (never "official"). **Pilot done:
11 marquee players, committed (bd1deb2), 406 tests pass.** Pool max 82->91, players >=85: 0->11.
Full methodology: `backend/reports/external_rating_injection_methodology_2026-06-26.md`.

**Open decision:** scaling to the remaining ~658 players (approach is the user's call —
full multi-agent workflow vs. prioritized squad-importance batches vs. incremental). The
infrastructure is idempotent: scaling = adding rows to the seed + re-running the rebuild.

(Codex is no longer involved — Claude now owns all decisions/execution on this project.)

**Spec 017 and Spec 018 are both fully complete, including production push/deploy (2026-06-25).** Full final report: `docs/codex/CLAUDE_FINAL_HANDOFF_2026-06-25.md`. Summary: Claude Code completed Spec 017 in full (48/48 teams, 346 URL-backed candidates), then worked through all of Spec 018's phases autonomously while Codex was unavailable -- repaired source traceability (121/346 -> 1/346 missing resolvable URLs), built 4 data-change proposal reports, applied exactly one safe verified factual update (Uruguay fifa_rank 14->16) after holding two genuinely conflicting/overtaken candidates for Codex's judgment, added a substitution-profile prototype to the match engine (neutral-default-preserving, fully tested, not yet wired to real per-team data), re-ran the full diagnostics suite with a confirmed no-regression check, fixed one stale diagnostic the prototype itself had made inaccurate, prepared a release candidate, and pushed to production.

**Production deploy found and fixed a real bug in this session's own earlier work, not a Render problem:** `app/rating_v2/seed_pipeline_v2.py` makes `scripts/seed_db.py` seed the live database from `teams2026_official.json`'s `fifaRank` field whenever the v2 official/estimated data files are present (they are), not from `teams.json`'s `fifa_rank` -- and the Uruguay fix had only been written to `teams.json`. So the corrected value never reached the file the live app actually reads, on any deploy, and looked at first like a stuck Render deployment. Fixed (commit `b0f2840`) by mirroring the same already-sourced update into `teams2026_official.json` and hardening `app/main.py`'s startup to always resync Team/Player rows from the current seed JSON rather than only when the table happens to be empty. **Verified live after the fix**: `curl https://wc2026-backend-tdih.onrender.com/api/teams` returns Uruguay `fifa_rank: 16`; `scripts/post_deploy_smoke.ps1` against both production URLs returned HTTP 200 on all 20 checks. Full detail and investigation trail: `docs/codex/PROGRESS.md`'s Spec 018 Phase 9 entries, `docs/codex/PRODUCTION_DEPLOYMENT_NOTE_2026-06-25.md`.

**Closed at the user's request, same day:** the `teams.json`/`teams2026_official.json` dual-source-of-truth risk above is fixed. `teams2026_official.json` is now the single source of truth whenever it exists; `apply_external_factual_updates.py` regenerates `teams.json` from it on every run via `regenerate_legacy_teams_json()`, and `tests/test_seed_file_consistency.py` asserts the two files stay consistent regardless of cause (not just future runs of that one script). Caught and avoided a real data-loss bug while building this: a first draft of the regeneration silently deleted `_tactical_profile_basis` (a sourcing note with no v2 equivalent, present for 8/48 teams) -- caught from the diff before committing, fixed by preserving any per-team field the v2 file doesn't represent. See `docs/codex/PROGRESS.md`'s follow-up entry for full detail.

**Smaller, lower-severity follow-up -- now also closed (2026-06-26):** `players.json` (read by 13 diagnostics/benchmark scripts) could still drift from `players2026_official.json` (the v2 player layer the live app actually seeds from) over time, the same way `teams.json` did. Closed by extending the exact same mirror+guardrail pattern to the player layer: `apply_external_factual_updates.py` now regenerates `players.json` from `players2026_official.json` on every run via `regenerate_legacy_players_json()` (field-name + nested `careerStats` snake_case translation only, with the same carry-over-any-unmapped-key safety as the teams version), and `tests/test_seed_file_consistency.py` now asserts the two player files stay consistent regardless of cause. Verified the regeneration is a pure pass-through against the live repo: zero value drift across all 669 players, the only on-disk change being a trailing-newline normalization that brings `players.json` in line with every other seed file. (Both Tunisia's manager-identity item and Ghana's overtaken fifa_rank item are also resolved, see the Handoff Notes section below.)

## Critical Worktree Warning

`backend/reports/external_data_verification_candidates_2026-06-24.json` is now complete (48/48 teams) and committed. No in-progress worktree state remains for Spec 017.

## Handoff Notes For Codex

- 5 stale-manager findings from Spec 017 research: Tunisia, Saudi Arabia, Uzbekistan, Czech Republic, Ghana. 4 of 5 (KSA/UZB/CZE/GHA) were already corrected in `teams.json` by an earlier process before this handoff. Tunisia's apparent conflict is now resolved (2026-06-26): both prior claims were correct for their own point in time, not contradictory -- Lamouchi succeeded Trabelsi in January 2026, then was sacked mid-tournament after the Sweden loss and replaced by Herve Renard on 2026-06-16, confirmed live via FIFA.com/World Soccer Talk/Wikipedia. `teams.json`'s current value ("Herve Renard") is already correct; see `backend/reports/external_factual_updates_applied_2026-06-24.json`'s `resolvedConflicts` entry.
- Ghana's overtaken `fifa_rank` candidate is now resolved (2026-06-26) -- no longer a held item. Live web re-verification showed the candidate's recorded old=61 was itself inaccurate, not overtaken: FIFA's official ranking page lists the last official update (dated 2026-06-11) as Ghana 73rd pre-tournament, closely matching the live seed's 72 (within ordinary source/rounding variance). The candidate's new=65 is an unofficial post-Panama-win "live ranking" projection, not a finalized FIFA list entry -- FIFA's next official update is not until 2026-07-20, so applying 65 now would violate the no-speculative-data policy. `teams.json`'s value (72) is left unchanged; recommend a fresh check once the 2026-07-20 official list publishes. See `backend/reports/external_factual_updates_applied_2026-06-24.json`'s `resolvedConflicts` entry (now 2: TUN, GHA). With this, all stale-manager / overtaken-rank handoff items are closed; `heldForReviewCount` is now 0.
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
