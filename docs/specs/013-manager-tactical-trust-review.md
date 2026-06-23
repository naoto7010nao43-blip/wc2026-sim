# Spec 013: Manager Tactical Trust Review

Status: Ready. Implement under the autonomous sprint protocol.

## Owner Split

- Codex owns product/data/simulation judgment, verification, and activation.
- Claude Code owns implementation.

## Why This Matters

The simulator now has stronger squad and model diagnostics, but manager/tactical data is still one of the largest trust gaps in match realism. The current seed contains manager names and tactical values, while `managerRatings2026_estimated.json` marks tactical ratings as estimated. These values can materially affect the perceived quality of matchup previews and simulated match narratives even when the core Poisson formulas are unchanged.

Codex added a read-only audit in commit `6761f6e`:

- `backend/scripts/audit_manager_tactical_data.py`
- `backend/reports/manager_tactical_data_audit_2026-06-23.json`
- `backend/tests/test_audit_manager_tactical_data.py`

Initial high-priority manager/tactical review teams from that report:

- ARG
- CRO
- ESP
- IRN
- MAR
- NED
- POR
- URU

Primary reasons: high team-data review priority and missing tactical-profile basis notes for top-20 FIFA teams. This does not mean the values are wrong; it means they are high-value candidates for evidence review.

## Product Goal

Expose manager/tactical trust as a transparent diagnostic, so users and reviewers understand which tactical profiles are well-supported, which are provisional, and which should be reviewed before relying on fine-grained tactical claims.

This spec is about visibility and review workflow. It must not silently rewrite manager names, tactical values, player ratings, formulas, or tournament logic.

## Implementation Scope

### Phase 1: Backend Diagnostic Endpoint

Add a read-only API endpoint that serves the latest `manager_tactical_data_audit_*.json` report.

Recommended endpoint:

- `GET /api/model-diagnostics/manager-tactical-trust`

Response should include:

- `generatedAt`
- `note`
- `teamCount`
- `bandCounts`
- `teams`

Each team row should preserve the report fields:

- `team_id`
- `team_name`
- `fifa_rank`
- `default_formation`
- `manager_name_seed`
- `manager_name_official`
- `manager_name_official_profile`
- `manager_name_mismatch`
- `manager_rating_confidence`
- `missing_manager_rating`
- `has_tactical_basis`
- `tactical_profile`
- `duplicate_profile_team_ids`
- `team_review_priority_band`
- `review_score`
- `review_band`
- `review_reasons`

If no report exists, return a calm empty state with `teamCount: 0` and an explanatory note. Do not crash the page.

### Phase 2: Frontend Data Review Panel

Add a compact panel to `/data-review` after the squad gap section.

Panel requirements:

- Show high/medium/low counts.
- Show top review teams sorted by `review_score`.
- For each row, show team id/name, FIFA rank, manager name, tactical values, review band, and reasons.
- Do not imply the tactical values are verified facts. Use language like "review priority" and "basis note missing".
- Keep the visual density similar to the existing data review panels.
- Mobile must avoid horizontal page overflow.

### Phase 3: Verification

Required checks:

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests\test_audit_manager_tactical_data.py tests\test_model_diagnostics.py
.\venv\Scripts\python.exe scripts\audit_text_encoding.py

cd ..\frontend
npm run lint
npm run build
```

Browser smoke:

- `/data-review` desktop around 1280px
- `/data-review` mobile around 390px

Pass criteria:

- no console errors
- no mojibake
- no full-page horizontal overflow
- manager/tactical panel renders a calm loading, error, and success state

## Hard Prohibitions

- Do not change manager names.
- Do not change tactical values.
- Do not change formations.
- Do not change simulation formulas or model constants.
- Do not add unverified "latest" claims.
- Do not scrape or import new external data in this spec.

## Stop Conditions

Stop and report back to Codex if:

- The manager audit report is missing and cannot be regenerated.
- The implementation requires changing seed data or prediction behavior.
- Tests fail for reasons outside this spec.

## Commit Guidance

When this spec becomes Ready and passes verification, commit locally only. Do not push unless the user explicitly authorizes it.
