# Production Deployment Note - 2026-06-25

## What was pushed

`git push origin master`, three pushes in sequence, all clean fast-forwards from `origin/master` at `62dd339`:

1. `62dd339..88be2b4` -- the full Spec 017 + Spec 018 Phases 0-8 work (150 commits; see `RELEASE_CANDIDATE_NOTES_2026-06-25.md` for the pre-push gate results).
2. `88be2b4..1eb8c39` and `1eb8c39..f62d317` -- docs-only commits logging the post-deploy investigation in progress (no code/data change).
3. `f62d317..b0f2840` -- the actual fix for the bug described below.

## Deploy targets

- Frontend: `https://wc2026-sim-ten.vercel.app` (Vercel, auto-deploy on push to `master`) -- deployed correctly and immediately for every one of the four pushes above.
- Backend: `https://wc2026-backend-tdih.onrender.com` (Render, auto-deploy on push to `master`, plan `Free`, no persistent disk) -- deployed correctly for every push; see "Incident" below for why the live data still looked wrong for a while after the first deploy.

## Incident during this deploy (now resolved)

After the first push (`88be2b4`), `/api/teams` kept returning Uruguay's old `fifa_rank: 14` instead of the corrected `16` for roughly an hour. This looked like a Render deployment problem at first -- GitHub's Deployments API reported `success`, but the data never changed, even after a second no-op push to retrigger the webhook.

It was not a Render problem. The user checked the Render dashboard's Events tab directly and confirmed the original deploy genuinely went live within a minute of the push, exactly as reported. The real bug was in this session's own earlier work: `scripts/seed_db.py` seeds the live database from `backend/data/seed/teams2026_official.json` (the "v2 official data layer") whenever that file and its companions are present, which they are in this repo -- not from the older `teams.json`. The Uruguay `fifa_rank` fix applied earlier in this spec (`adb1ff7`) only touched `teams.json`. So every Render deploy was correctly and freshly reseeding the database -- right back to the stale value still sitting in the file the seeder actually reads.

Fixed in `b0f2840`: mirrored the same already-sourced, already-verified factual update into `teams2026_official.json`, and added a defense-in-depth fix so the app always re-syncs Team/Player reference rows from the current seed JSON on every startup rather than only when the database table happens to be empty. Full details and the investigation trail are in `docs/codex/PROGRESS.md`'s Spec 018 Phase 9 entries.

## Post-deploy verification (after the `b0f2840` fix)

- `gh api .../deployments` confirms both Vercel and Render created deployment records for `b0f2840` (`5194976417`, `5194973873`).
- `curl https://wc2026-backend-tdih.onrender.com/api/teams` confirms Uruguay's `fifa_rank` is now `16` live.
- `scripts/post_deploy_smoke.ps1 -FrontendBaseUrl "https://wc2026-sim-ten.vercel.app" -BackendBaseUrl "https://wc2026-backend-tdih.onrender.com"` -- all 20 checks (5 frontend routes, 15 backend endpoints) returned HTTP 200. No failures.

## Risk carried forward

`teams.json`/`metadata.json` (read directly by the diagnostics/benchmark scripts) and `teams2026_official.json` (read by the live app) are two independently-maintained sources of truth for the same fields, with nothing enforcing they stay in sync. This is exactly how this incident happened and could recur for any future seed correction unless a follow-up spec unifies them. Flagged for Codex in `docs/specs/CURRENT_TASK.md`'s handoff notes; not changed unilaterally here since it's an architecture decision, not a bounded bug fix.
