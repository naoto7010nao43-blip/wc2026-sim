# Spec 012: Squad Rating Gap Review

Status: Ready for Claude Code implementation

## Owner

Claude Code implements. Codex reviews after completion.

## Context

Spec 011 produced a read-only team review priority ranking. The highest-priority teams are:

1. CRO
2. NED
3. POR
4. MEX
5. MAR

Spec 010/011 indicate these are likely data-review problems, not formula problems. The next step is to explain why the current squad/rating data may be undershooting those teams before any seed data or rating methodology is changed.

## Non-Negotiable Rules

- Do not change seed player data, team data, manager data, rating values, formulas, `ModelConfig`, tournament logic, or prediction behavior.
- Do not add external data.
- Do not infer that a player should be better/worse from real-world knowledge unless that claim is already present in local data.
- Do not auto-apply roster additions or name-pair merges.
- This task is diagnostic only.
- Keep Japanese UI/report copy clean and calm.

## Goal

Create a deterministic squad-rating gap diagnostic that explains, using only local data:

- why high-priority teams such as CRO/NED/POR are flagged,
- whether the issue appears to come from shallow roster coverage, position-group weakness, low-confidence attributes, stale seed players, or missing official profile fields,
- what Codex should review next before authorizing any data import or rating update.

## Phase 1: Build Squad Gap Review Report

Add a read-only script:

- `backend/scripts/build_squad_rating_gap_review.py`

Inputs:

- `backend/reports/team_data_review_plan_*.json`
- `backend/reports/roster_reconciliation_candidates_*.json`
- `backend/data/seed/teams.json`
- `backend/data/seed/players.json`
- `backend/data/seed/playerRatings2026_estimated.json`

Output:

- `backend/reports/squad_rating_gap_review_2026-06-23.json`

Report shape:

- `generatedAt`
- `sourceReports`
- `note`
- `teams`

Include at least the top 8 high-priority teams from Spec 011, but make the implementation general enough to accept a `--limit` argument or a helper parameter for tests.

For each team:

- `team_id`
- `team_name`
- `fifa_rank`
- `priority_score`
- `rank_underperformance_flags`
- `seed_roster_size`
- `position_groups`
  - GK / DF / MF / FW counts
  - average overall
  - average starting probability
  - top player by overall
- `rating_distribution`
  - min/median/max overall
  - top 5 players by overall
  - count of players with overall >= 75, >= 70, < 60
- `trust_profile`
  - data confidence counts
  - average uncertainty where available
  - low-confidence attribute count
  - official profile coverage for club/caps/goals/height/dateOfBirth
- `roster_reconciliation`
  - high-confidence add count
  - other add count
  - ambiguous pair count
  - likely stale seed count
  - top ambiguous pairs if present
- `diagnostic_flags`
  - short machine-readable flags, for example:
    - `shallow_seed_roster`
    - `thin_defensive_depth`
    - `thin_attacking_depth`
    - `low_official_profile_coverage`
    - `many_low_confidence_attributes`
    - `stale_seed_review_needed`
    - `name_pair_review_needed`
- `review_summary_ja`
  - 2-4 Japanese bullet strings explaining what Codex should inspect next.
- `recommended_next_action`
  - one of:
    - `rating_data_review`
    - `roster_reconciliation_review`
    - `name_matching_review`
    - `monitor_only`

Important: The report must clearly distinguish between:

- "this team has many official add candidates because the local seed roster is intentionally shallow"
- "this team has model/rank mismatch and therefore needs rating-data review"

Tests:

- focused tests for median calculation, position grouping, flag generation, and recommendation selection
- test that CRO/NED/POR-like rank-underperformance produces `rating_data_review`
- test that a team with only add candidates but no rank-underperformance is not automatically treated as a rating-data issue

## Phase 2: Add Backend Endpoint

Add:

- `GET /api/model-diagnostics/squad-gaps`

Recommended files:

- extend `backend/app/services/model_diagnostics.py`
- extend `backend/app/schemas/model_diagnostics.py`
- extend `backend/app/api/model_diagnostics.py`

Behavior:

- serve latest `squad_rating_gap_review_*.json`
- if missing, return 200 with an empty/calming note, not 500
- do not compute expensive reports on request

Tests:

- endpoint returns 200
- fallback returns 200
- at least one returned top team has expected fields

## Phase 3: Frontend Review Surface

Add a compact section to the existing `/data-review` page, below the team priority list:

- heading: `スカッド評価ギャップ`
- top team cards for the squad gap report
- for each team show:
  - team badge
  - priority score / FIFA rank
  - position-group summary
  - rating distribution summary
  - diagnostic flags as Japanese labels
  - review summary bullets
  - recommended next action

Do not overload the page with giant JSON-like tables. It should be dense but readable.

UI copy boundary:

- state that this is diagnostic and does not change predictions
- state that formula tuning remains frozen

Mobile:

- 390px width must not have full-page horizontal overflow
- long player names and bullets must wrap/truncate cleanly

## Phase 4: Verification

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

- If browser automation is available, check `/data-review` at 1280px and 390px.
- Also check `/`, `/teams/CRO`, `/simulate`.
- Verify:
  - no console errors
  - no mojibake/replacement characters
  - no full-page horizontal overflow

## Acceptance Criteria

- `squad_rating_gap_review_2026-06-23.json` is generated and committed.
- The report is read-only and deterministic from local files.
- `/api/model-diagnostics/squad-gaps` works and has a missing-report fallback.
- `/data-review` shows the new squad-gap section.
- No seed data, formula, rating methodology, or prediction behavior is changed.
- Backend tests pass.
- Frontend lint/build pass.
- Text encoding audit passes.
- `docs/codex/PROGRESS.md` and `docs/specs/CURRENT_TASK.md` are updated.
- Commit locally. Do not push.

## Final Report Required

Report:

- commit hash
- changed files
- top squad-gap teams and their recommended actions
- verification results
- residual risks
- Codex decision needed next

