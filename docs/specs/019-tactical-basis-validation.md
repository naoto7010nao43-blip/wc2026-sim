# Spec 019 - Tactical Basis Validation

Status: Ready for Claude Code

## Objective

Validate the uncommitted `_tactical_profile_basis` candidates currently present in `backend/data/seed/teams.json` before any tactical-basis data is accepted into seed files or used to clear manager/tactical audit findings.

This is a data-governance task. Do not change prediction formulas or tactical numeric values in this spec.

## Context

Codex reviewed the candidate diff and wrote:

- `docs/codex/TACTICAL_BASIS_SOURCE_REVIEW_2026-07-02.md`

Current finding:

- 25 teams have `_tactical_profile_basis` candidate text.
- 51 URLs are referenced.
- 48 URLs were machine-reachable.
- 3 URLs returned 403.
- 8 teams have candidate text but no URL.
- The manager tactical audit changes substantially if a plain `_tactical_profile_basis` string is treated as "basis exists".

Therefore, the candidate diff must not be committed as-is.

## Allowed Work

Claude Code may:

- inspect the uncommitted `teams.json` tactical-basis candidate diff;
- verify URL reachability again if needed;
- read article pages where accessible;
- create a structured review report under `backend/reports/`;
- create tests/guardrails for tactical-basis metadata validation;
- update diagnostics so `has_tactical_basis` requires structured, URL-backed evidence rather than a plain text field;
- commit verified reports, tests, and diagnostic code after verification passes.

Claude Code must not:

- commit `_tactical_profile_basis` into `teams.json` as-is;
- treat URL-less text as verified tactical evidence;
- use 403-blocked or unread article pages as evidence unless manually verified through an accessible browser/source;
- change `press_intensity`, `possession_style`, `defensive_line_height`, `default_formation`, player ratings, manager ratings, or prediction formulas in this spec;
- mark any data as official.

## Required Implementation

1. Preserve the raw candidate diff in a review artifact, not in seed:
   - Output path suggestion: `backend/reports/tactical_basis_candidate_review_2026-07-02.json`.
   - Include per team:
     - `team_id`
     - `candidate_present`
     - `url_count`
     - `reachable_url_count`
     - `blocked_or_failed_url_count`
     - `url_less_candidate`
     - `recommended_status`: `ready_for_human_review`, `needs_sources`, or `blocked_source_review`
     - `notes_ja`

2. Add or update tests so tactical-basis metadata cannot silently clear audit flags unless it is structured and URL-backed.

3. If changing diagnostics:
   - `manager_tactical_data_audit` may use tactical basis only when the basis is structured and source-backed.
   - Existing plain `_tactical_profile_basis` must not be enough.
   - UI copy must remain Japanese.

4. Leave the numeric tactical model unchanged.

## Verification

Run:

- `backend\venv\Scripts\pytest.exe -q`
- `backend\venv\Scripts\python.exe backend\scripts\audit_text_encoding.py`
- `npm run lint` in `frontend`
- `npm run build` in `frontend`

If only backend reports/tests changed, frontend lint/build may still be run as release guardrails.

## Completion Report

Report:

- commit hash;
- whether `teams.json` was left uncommitted or reverted by the user/Codex later;
- report path and summary counts;
- tests run;
- remaining source risks.
