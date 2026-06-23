# Spec 011: Team Data Review Diagnostics

Status: Ready for Claude Code implementation

## Owner

Claude Code implements. Codex reviews after completion.

## Context

Spec 010 finished the first unattended quality sprint. It found two important but not-yet-actionable accuracy risks:

- `backend/reports/simulation_accuracy_audit_2026-06-23.json` flags several high-rank teams, especially CRO/NED/POR, as potentially underpowered by the current squad-derived ratings.
- `backend/reports/roster_reconciliation_candidates_2026-06-23.json` identifies official roster candidates and ambiguous name pairs, but no player should be added, removed, or rating-tuned without a Codex-reviewed import/data spec.

The next product step is to make these risks reviewable and actionable without mutating simulation formulas or seed player data.

## Non-Negotiable Rules

- Do not change simulation formulas, `ModelConfig`, Poisson weights, shootout bounds, or tournament logic.
- Do not add, delete, or edit seed players, teams, managers, ratings, or official squad JSON.
- Do not use new external data or make claims that are not derived from existing local seed/report files.
- All new behavior must be read-only and reproducible from the repository.
- Keep Japanese UI text clean and calm. Avoid mojibake, replacement characters, and hype language.
- Do not ask the user for routine approval. Commit when verification passes.

## Goal

Create a team data review diagnostic layer that combines the existing simulation accuracy audit and roster reconciliation report into:

1. A deterministic backend report that ranks team data-review priorities.
2. A read-only API endpoint for that diagnostic summary.
3. A frontend data-review page/panel that lets users and Codex see why a team needs review.

This should move the project closer to higher simulation accuracy while keeping the current prediction model safe and auditable.

## Phase 1: Build A Team Data Review Plan Report

Add a read-only script:

- `backend/scripts/build_team_data_review_plan.py`

Inputs:

- latest `backend/reports/simulation_accuracy_audit_*.json`
- latest `backend/reports/roster_reconciliation_candidates_*.json`
- `backend/data/seed/teams.json`
- `backend/data/seed/players.json`

Output:

- `backend/reports/team_data_review_plan_2026-06-23.json`

The report should include:

- `generatedAt`
- `sourceReports`
- `note`
- `teamCount`
- `teams`: one row per team, sorted by review priority descending

Each team row should include, at minimum:

- `team_id`
- `team_name`
- `fifa_rank`
- `seed_roster_size`
- `attack_rating`, `defense_rating`, `strength_rating` when available from the accuracy audit
- `rank_underperformance_flags` or equivalent count/list from the audit
- `high_confidence_add_candidate_count`
- `other_add_candidate_count`
- `ambiguous_pair_count`
- `likely_stale_seed_player_count`
- `priority_score`
- `priority_band`: `high`, `medium`, or `low`
- `review_reasons`: short Japanese reason strings derived only from local report values
- `recommended_next_action`: short Japanese action string, for example:
  - `スカッド能力値レビュー`
  - `ロスター候補レビュー`
  - `名寄せ候補レビュー`
  - `低優先度`

Priority scoring should be transparent and deterministic. A reasonable starting rule:

- add meaningful weight for teams flagged by the simulation audit as repeatedly underperforming their FIFA rank
- add smaller weight for high-confidence add candidates
- add weight for ambiguous pairs and likely stale seed players
- do not rank a team high solely because every 26-man official roster has more players than the current intentionally shallow seed roster

Tests:

- Add focused unit tests for priority scoring, latest-report lookup, and output shape.
- Include a test that CRO/NED/POR-style underperformance can outrank a team with only low-value roster noise.

## Phase 2: Add Read-Only Diagnostics API

Add a backend API endpoint:

- `GET /api/model-diagnostics/team-review`

Recommended implementation:

- `backend/app/services/model_diagnostics.py`
- `backend/app/schemas/model_diagnostics.py`
- `backend/app/api/model_diagnostics.py`
- wire router in `backend/app/main.py`

The endpoint should return the latest `team_data_review_plan_*.json` if present.

Fallback behavior:

- If the report is missing, compute a minimal response from available reports or return a calm empty state with `teams: []` and a note.
- Never fail with a 500 just because an optional report is missing.

Tests:

- Endpoint returns 200 and expected top-level fields.
- Missing-report fallback is covered.
- Endpoint is read-only.

## Phase 3: Add Frontend Data Review Page

Add a frontend page:

- route: `/data-review`
- component name suggestion: `DataReviewPage`
- component/panel suggestion: `TeamDataReviewPanel`

The page should show:

- top summary cards:
  - high-priority teams
  - medium-priority teams
  - teams with ambiguous name pairs
  - teams flagged by model/rank mismatch
- a table or dense card list of teams sorted by `priority_score`
- for each high/medium team:
  - team badge/name
  - FIFA rank
  - priority band
  - seed roster size
  - add/ambiguous/stale counts
  - review reasons
  - recommended next action

Navigation:

- Add a link to `/data-review` from the home data-quality panel or another existing data-quality surface.
- Avoid overloading the top navigation if it becomes too crowded on mobile.

UI requirements:

- Must fit mobile width around 390px without full-page horizontal overflow.
- Do not use marketing-style hero copy.
- Do not bury the actionable high-priority teams below a long explanation.
- Use calm Japanese labels. Examples:
  - `データレビュー`
  - `優先レビュー`
  - `モデル/順位差`
  - `名寄せ候補`
  - `次の確認`

## Phase 4: Explain The Review Boundary

Add short copy in the UI or report notes making this boundary clear:

- This diagnostic does not change match predictions.
- It identifies where Codex should review squad/rating data next.
- Formula changes remain frozen unless a later calibration spec authorizes them.

## Phase 5: Verification

Run:

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest
```

Run:

```powershell
cd frontend
npm run lint
npm run build
```

Run:

```powershell
python backend\scripts\audit_text_encoding.py
```

Browser smoke:

- If Playwright/Chrome is available, check desktop 1280px and mobile 390px for:
  - `/`
  - `/data-review`
  - `/teams`
  - `/tournament`
- Check for:
  - no console errors
  - no full-page horizontal overflow
  - no mojibake/replacement characters

If browser automation is not available, state that clearly and still run lint/build/API checks.

## Acceptance Criteria

- The team data review report is deterministic and committed.
- `/api/model-diagnostics/team-review` returns a stable, read-only summary.
- `/data-review` renders a useful prioritized review list.
- No seed data, ratings, formulas, or simulation results are changed.
- Backend tests pass.
- Frontend lint/build pass.
- Text encoding audit passes.
- `docs/codex/PROGRESS.md` is updated with what was implemented, verification results, and residual risks.
- Commit locally. Do not push.

## Final Report Required

Report:

- commit hash
- changed files
- high-level summary
- top 5 high-priority teams found by the new diagnostic
- verification results
- residual risks and recommended next Codex decision

