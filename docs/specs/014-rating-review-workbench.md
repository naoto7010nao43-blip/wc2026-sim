# Spec 014: Rating Review Workbench

Status: Ready. Implement under the autonomous sprint protocol.

## Owner

Claude Code implements. Codex reviews after completion and decides whether a later data-changing spec is justified.

## Context

Specs 011-013 built the data-review surface and identified the next accuracy problem:

- `docs/specs/011-team-data-review-diagnostics.md`
- `docs/specs/012-squad-rating-gap-review.md`
- `docs/specs/013-manager-tactical-trust-review.md`

The current top squad/rating review teams are:

- CRO
- NED
- POR
- MEX
- MAR
- URU
- ESP
- ARG

Spec 012 showed these teams are flagged because of rank-underperformance signals, not merely because local seed rosters are shallower than official 26-man tournament squads. The next step is to move from team-level diagnosis to player-level rating-review candidates before any rating values are changed.

## Non-Negotiable Rules

- Do not change `players.json`.
- Do not change `players2026_official.json`.
- Do not change `playerRatings2026_estimated.json`.
- Do not change manager/team seed data.
- Do not change formulas, `ModelConfig`, simulation logic, tournament logic, or prediction behavior.
- Do not add external/web data.
- Do not infer real-world player strength from memory or general football knowledge.
- Use only local seed/report fields already present in the repository.
- Keep Japanese UI/report copy clean and calm.

This spec is a workbench and evidence organizer only. It prepares Codex to decide a later data-changing rating spec.

## Product Goal

Give Codex and users a player-level explanation of where the rating model may be undershooting high-priority teams, without pretending the system already knows the correct replacement values.

The `/data-review` page should answer:

- Which players most deserve rating review?
- Is the signal coming from market value, caps/goals, starting probability, low-confidence attributes, shallow roster coverage, or model/rank mismatch?
- Which position groups are dragging the team down?
- What should Codex inspect next before authorizing an update?

## Phase 1: Build Rating Review Workbench Report

Add a read-only script:

- `backend/scripts/build_rating_review_workbench.py`

Inputs:

- `backend/reports/squad_rating_gap_review_*.json`
- `backend/reports/team_data_review_plan_*.json`
- `backend/reports/roster_reconciliation_candidates_*.json`
- `backend/data/seed/teams.json`
- `backend/data/seed/players.json`
- `backend/data/seed/players2026_official.json`
- `backend/data/seed/playerRatings2026_estimated.json`

Output:

- `backend/reports/rating_review_workbench_2026-06-23.json`

Default scope:

- top 8 teams from the latest `squad_rating_gap_review_*.json`

Make the builder testable with helper functions and a `limit` parameter.

Report shape:

- `generatedAt`
- `sourceReports`
- `note`
- `teamCount`
- `teams`

For each team:

- `team_id`
- `team_name`
- `fifa_rank`
- `squad_gap_priority_score`
- `rank_underperformance_flags`
- `recommended_next_action`
- `position_group_summary`
  - GK / DF / MF / FW counts
  - average overall
  - top player
  - review candidate count
- `rating_review_candidates`

For each candidate player:

- `player_id`
- `name`
- `name_ja`
- `primary_position`
- `age`
- `club_name`
- `caps`
- `national_team_goals`
- `market_value_eur`
- `source_citations`
- `current_overall`
- `position_overall`
- `starting_probability`
- `uncertainty`
- `data_confidence`
- `source_breakdown`
- `low_confidence_attributes`
- `qualitative_adjustments`
- `review_score`
- `review_band`
- `review_flags`
- `review_summary_ja`
- `suggested_codex_action`

Candidate scoring should be deterministic and conservative. Suggested signals:

- team has `rank_underperformance_flags > 0`
- player is in a weak position group from the squad-gap report
- player has high market value relative to current overall within this local dataset
- player has high caps/goals relative to current overall within this local dataset
- player has high starting probability but low current overall
- player has many low-confidence attributes
- player has official profile coverage but still remains `estimated`
- roster/team is shallow and the player is one of few top contributors

Do not output numeric rating changes. Output only review priority and action labels.

Allowed `suggested_codex_action` values:

- `inspect_for_possible_upgrade`
- `inspect_for_possible_downgrade`
- `verify_roster_role_first`
- `monitor_only`

Allowed `review_band` values:

- `high`
- `medium`
- `low`

Important scoring rule:

- A player must not become `high` merely because the team has rank underperformance.
- A player-level signal must also exist.

## Phase 2: Backend Endpoint

Add:

- `GET /api/model-diagnostics/rating-review-workbench`

Recommended files:

- extend `backend/app/services/model_diagnostics.py`
- extend `backend/app/schemas/model_diagnostics.py`
- extend `backend/app/api/model_diagnostics.py`

Behavior:

- serve the latest `rating_review_workbench_*.json`
- if missing, return 200 with an empty calm Japanese note
- do not compute the report on request

Tests:

- endpoint returns 200
- fallback returns 200
- top returned team and candidate rows have required fields
- no mutation of seed/rating files

## Phase 3: Frontend Data Review Panel

Add a compact section to `/data-review` after the manager/tactical trust panel:

Suggested heading:

- `能力値レビュー作業台`

Panel requirements:

- Show the scoped team count and a short diagnostic note.
- Show a compact card per top team.
- For each team, show:
  - team badge
  - FIFA rank
  - rank-underperformance flags
  - weak position group summary
  - top 3-5 candidate players
- For each candidate, show:
  - name
  - position
  - current overall
  - starting probability
  - review band
  - review flags translated into Japanese labels
  - `suggested_codex_action` translated into a calm Japanese label

UI copy boundary:

- Do not say "this player is underrated" as fact.
- Say "review candidate", "possible mismatch", or "Codex review needed".
- State that predictions are unchanged.

Mobile:

- 390px width must not have full-page horizontal overflow.
- Long player names, source labels, and summaries must wrap cleanly.

## Phase 4: Verification

Run:

```powershell
cd backend
.\venv\Scripts\python.exe scripts\build_rating_review_workbench.py
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\python.exe scripts\audit_text_encoding.py
```

Run:

```powershell
cd frontend
npm run lint
npm run build
```

Browser smoke, if available:

- `/data-review` at 1280px and 390px
- `/teams/CRO`
- `/simulate`

Pass criteria:

- no console errors
- no mojibake/replacement characters
- no full-page horizontal overflow
- no blank data cards when the report exists

## Acceptance Criteria

- `rating_review_workbench_2026-06-23.json` is generated and committed.
- The workbench is deterministic from local files.
- `/api/model-diagnostics/rating-review-workbench` works and has a missing-report fallback.
- `/data-review` shows player-level rating review candidates.
- No seed player data, player ratings, formulas, model constants, tournament logic, or prediction behavior changes.
- Backend tests pass.
- Frontend lint/build pass.
- Text encoding audit passes.
- `docs/codex/PROGRESS.md` and `docs/specs/CURRENT_TASK.md` are updated.
- Commit locally. Do not push.

## Final Report Required

Report:

- commit hash
- changed files
- top review teams
- top player-level review candidates per team
- verification results
- residual risks
- Codex decision needed next
