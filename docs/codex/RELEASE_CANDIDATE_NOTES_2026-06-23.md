# Release Candidate Notes - 2026-06-23

## Current State

The local branch now contains the rank75 model calibration, refreshed diagnostics, Spec 015 data-review panels, and the next Spec 016 transparency task.

Recent key commits:

- `08be754` - production model changed to `poisson-v2-rank75`
- `207f99c` - diagnostics refreshed for the rank75 model
- `5f211ae` - rating readiness review panels added to `/data-review`
- `8b707c5` - Spec 016 added for model calibration transparency
- `ebe9ab0` - release readiness report tool added
- `e8f1a87` - post-deploy smoke endpoints expanded

## Accuracy Impact

The rank75 model change was evidence-led:

- sandbox best variant: `rank75_current_squad25`
- watchlist implausible cases improved by 5
- overall implausible favorite count improved by 6
- average favorite win probability moved only +0.7pp
- benchmark comparison status: `pass`

The refreshed diagnostics now reflect `poisson-v2-rank75`, not the older `poisson-v1` conclusions.

## Release Blockers

Do not push yet while any of these remain true:

- `docs/specs/CURRENT_TASK.md` lists Spec 016 as Ready or in progress.
- Claude Code has uncommitted Spec 016 work or temporary files.
- `git status --short` is not clean.
- `.\scripts\pre_release_check.ps1` has not been run after Spec 016 completes.
- `/data-review` browser smoke has not been re-run after Spec 016 completes.

## Final Local Gate

After Spec 016 is complete and committed:

```powershell
.\scripts\pre_release_check.ps1
cd backend
.\venv\Scripts\python.exe scripts\build_release_readiness_report.py
```

Expected release-readiness result before push:

- `readyForManualPush=true`
- no blockers
- rank75 benchmark status `pass`
- git status clean

## Post-Deploy Gate

After manual push and deploy:

```powershell
.\scripts\post_deploy_smoke.ps1 -FrontendBaseUrl "https://wc2026-sim-ten.vercel.app" -BackendBaseUrl "<production-backend-url>"
```

The smoke script now checks the main frontend routes, core backend data APIs, the `/data-review` diagnostic APIs, and a sample prediction endpoint.

