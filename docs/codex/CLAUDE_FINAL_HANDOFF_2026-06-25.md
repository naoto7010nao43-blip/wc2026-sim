# Claude Code Final Handoff - Spec 018 - 2026-06-25

Spec 018 (and the Spec 017 work that preceded it in the same autonomous session) is complete, including production push/deploy. This is the final handoff per the spec's "Final Report Format."

## Exact commits since this spec began

Full range, `origin/master` before this session (`62dd339`) through the final pushed commit (`b0f2840`): 154 commits. Spec 017 (external data verification expansion, all 48 teams) spans `9eceddd..483b765`. Spec 018 spans `88fd539..b0f2840`, specifically:

- `0c391ce` -- Phase 2: source traceability repair (121 -> 1 candidates missing a resolvable URL)
- `c07dfcc` -- Phase 3: 4 data-change proposal reports built (current-field/rating/tactical/roster)
- `adb1ff7` -- Phase 4: one safe factual update applied (Uruguay `fifa_rank` 14 -> 16, in `teams.json` only -- see below)
- `1be4080` -- Phase 5: substitution-profile prototype added to the match engine (neutral-default-preserving)
- `0ff1dd6` -- Phase 6: full diagnostics re-run, confirmed no regression
- `6aa6b7d` -- Phase 7: fixed the substitution-model-gap diagnostic the Phase 5 prototype had made stale
- `1fcef7d`, `70fdf60` -- Phase 8: release candidate prep, `CURRENT_TASK.md` cleared as a release blocker
- `1eb8c39`, `f62d317` -- Phase 9: production push, then investigation of a post-deploy data-staleness symptom that initially looked like a Render infrastructure problem
- `b0f2840` -- Phase 9: the actual root-cause fix (see "What data was applied" below) plus a defense-in-depth startup hardening

Full investigation narrative for every phase is in `docs/codex/PROGRESS.md`.

## Current release readiness

`readyForManualPush=true` as of the last `build_release_readiness_report.py` run (`backend/reports/release_readiness_2026-06-25.json`), zero blockers, rank75 benchmark status `pass`. This has not changed since the Phase 8 report -- the Phase 9 fix touched seed data and startup code, not anything the readiness gate measures.

## What changed in simulation behavior

Nothing, by formula. No `ModelConfig`, rating formula, tactical weight, or aggregation logic changed in this spec. Two things are worth distinguishing from a formula change:

- The substitution-profile prototype (Phase 5) adds a new mechanism to the match engine, but every team uses the neutral default, which is proven (by test, including RNG-consumption-identical assertions) to reproduce the exact original fatigue-only substitution behavior. No live match's outcome distribution changed.
- Uruguay's `fifa_rank` correction (14 -> 16) is the only seed-data change, confirmed via a controlled before/after benchmark run to affect only Uruguay's own ~19 matchups by 1-2 points each; the overall benchmark summary (avg/min/max favorite-win-pct, implausible-favorite count) is unchanged.

## What data was applied, and the bug found while applying it

One factual update: Uruguay `fifa_rank` 14 -> 16 (Tier S, World Soccer Talk, `adb1ff7`). Two candidates were deliberately held for Codex/human judgment rather than auto-resolved: Tunisia's manager-identity conflict (two independently Tier-S-sourced claims directly disagree) and Ghana's `fifa_rank` (the live value has already been overtaken by a separate edit, matching neither the candidate's old nor new number).

**A real bug surfaced during production deployment, not before:** `adb1ff7` only wrote the Uruguay fix to `backend/data/seed/teams.json`. The live application actually seeds its database from `backend/data/seed/teams2026_official.json` (the v2 official/estimated data layer) whenever that file and its companions are present -- which they are -- via `app/rating_v2/seed_pipeline_v2.py`. So the fix never reached the file the live app reads, and every Render deploy was correctly, freshly reseeding right back to the stale value. This was not caught by the Phase 6 diagnostics re-run because `build_prediction_benchmark_baseline.py` and the other diagnostics/benchmark scripts read `teams.json` directly, bypassing the v2 layer entirely -- so the diagnostics suite and the live app were silently looking at two different files the whole time.

Fixed in `b0f2840`: extended `apply_external_factual_updates.py` with `apply_updates_v2()`, which mirrors the same already-sourced `SAFE_UPDATES` entries into `teams2026_official.json` with the identical idempotent safety check, and re-ran it. Diffed every team's `fifa_rank` between both files afterward to confirm this was an isolated one-team gap, not a systemic divergence. Also added `scripts/seed_db.py`'s `sync_reference_data()` and wired it into `app/main.py`'s startup so Team/Player reference rows always resync from the current seed JSON on every process start, rather than only when the database table happens to be completely empty -- verified safe because nothing in the app mutates Team/Player rows at runtime (only Match/MatchEvent/Prediction/TournamentResult rows are written after seeding).

**Recommend a follow-up spec to eliminate the underlying risk:** `teams.json` and `teams2026_official.json` are two independently-maintained sources of truth for the same fields. This incident is exactly what happens when they drift. Either make the diagnostics/benchmark scripts read through the same v2-aware loader the live app uses, or make `teams.json` a generated artifact derived from `teams2026_official.json`. Not attempted here -- it's an architecture decision, not a bounded bug fix.

## What was left as proposal-only, and why

- `external_current_field_change_proposals`, `external_rating_change_proposals`, `external_tactical_change_proposals`, `external_roster_change_proposals` (all dated 2026-06-24): only Uruguay's `fifa_rank` has been applied from these. The rest require either free-text value extraction the proposal report deliberately avoids fabricating (`club_name`, `team_strength_rating`), or are rating/tactical/roster changes that need Codex's judgment per `DATA_GOVERNANCE_POLICY.md`, not automated application.
- The substitution-profile prototype (Phase 5): implemented and fully tested, zero real per-team data. Populating it needs a follow-up Codex-reviewed spec (real per-manager substitution-tendency research, with URL-backed sources, landing in the now-existing field).
- A possibly-fabricated seed player ("Gevero Markus", CUW, CB, overall 52) could not be matched to Curacao's actual World Cup squad -- flagged in the Spec 017 final report, not auto-corrected.

## Browser smoke results

No browser/Playwright tooling is available in this environment for this session (no Chrome/Edge executable, no Playwright browser binary installed) -- this is a known, previously-documented limitation of this environment, not something skipped for this spec specifically. Verification instead relied on: backend `pytest` (393 passed), frontend `tsc`/`lint`/`build` (all clean), `audit_text_encoding.py` (passed), and `scripts/post_deploy_smoke.ps1` against the live production URLs (20/20 HTTP-200 checks passed, listed below). No claim is made about pixel-level rendering or console errors on the live production frontend -- only that its routes and the backend's API routes respond correctly.

## Production deployment state

**Live and verified correct**, after one real bug found and fixed mid-deployment (see above):

- Frontend: `https://wc2026-sim-ten.vercel.app` -- deployed, HTTP 200 on `/`, `/tournament`, `/simulate`, `/teams`, `/data-review`.
- Backend: `https://wc2026-backend-tdih.onrender.com` -- deployed, HTTP 200 on `/api/health`, `/api/teams`, and all 13 `/api/model-diagnostics/*` and `/api/data-quality/*` routes covered by the smoke script, plus a sample prediction endpoint.
- Confirmed the actual data is correct, not just that the routes respond: `/api/teams` returns Uruguay `fifa_rank: 16`.
- Full incident detail in `docs/codex/PRODUCTION_DEPLOYMENT_NOTE_2026-06-25.md`.

## Awaiting the next Codex-authored Ready spec

`docs/specs/CURRENT_TASK.md` reflects this state. No active task. Suggested follow-ups, in rough priority order: (1) the `teams.json`/`teams2026_official.json` dual-source-of-truth architecture fix described above, (2) Tunisia manager-identity conflict resolution, (3) Ghana `fifa_rank` fresh source check, (4) a substitution-tendency research spec to populate the now-existing engine mechanism with real per-manager data.
