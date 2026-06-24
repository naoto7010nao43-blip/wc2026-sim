# Production Release Checklist

This checklist is for the final local-to-production step. It should be run after the active spec is complete and Codex has reviewed the result.

## Release Gate

Do not push/deploy while any of these are true:

- `docs/specs/CURRENT_TASK.md` lists an active unfinished task.
- `git status --short` contains unexpected or unrelated files.
- Backend tests, frontend lint/build, or text encoding audit fail.
- A spec changed seed player data, ratings, formulas, or tournament logic without Codex review.
- Browser smoke finds mojibake, full-page horizontal overflow, blank pages, or console errors.

## Required Local Commands

Run the consolidated script:

```powershell
.\scripts\pre_release_check.ps1
```

This runs:

- `git status --short`
- backend pytest through `backend\venv\Scripts\python.exe`
- frontend lint
- frontend build
- text encoding audit
- release readiness structural check (`build_release_readiness_report.py --check-only --fail-on-blockers`)

For a quick script sanity check while another agent is mid-task:

```powershell
.\scripts\pre_release_check.ps1 -SkipBackendTests -SkipFrontendChecks -SkipReleaseReadiness
```

## Browser Smoke

Before production push, check at least:

- `/`
- `/tournament`
- `/simulate`
- `/teams`
- `/teams/BRA`
- `/data-review`
- one generated detailed match page

Use desktop width around 1280px and mobile width around 390px.

Pass criteria:

- no console errors
- no replacement characters or mojibake
- no full-page horizontal overflow
- main panels render non-empty data or a calm fallback

## Data Safety Review

Confirm the current release does not silently change prediction behavior unless that was explicitly intended:

- no seed player/team/rating JSON changes without a data-import spec
- no `ModelConfig` or Poisson formula changes without a calibration spec
- no manager/lineup/injury claims from unverifiable data
- diagnostic pages clearly say they do not change predictions

## Deployment Notes

- The backend Render CORS origin is configured in `render.yaml` through `ALLOWED_ORIGINS`.
- The frontend must point at the production backend API through its deployment environment variable.
- Push is still manual and should happen only after Codex says the release gate is clean.

## Post-Deploy Smoke

After production deploy finishes, run:

```powershell
.\scripts\post_deploy_smoke.ps1 -FrontendBaseUrl "https://wc2026-sim-ten.vercel.app" -BackendBaseUrl "<production-backend-url>"
```

This checks the public frontend routes plus the core backend API endpoints used by the release gate.
