# Spec 010: Unattended Site Quality Sprint

## Status

Ready for Claude Code implementation.

## Operating Rule

This is a large unattended sprint task intended to keep work moving until noon without user involvement.

Do not ask the user for routine approval, display checks, or commit approval. Work through the phases in order. If one phase is blocked, document the blocker in `docs/codex/PROGRESS.md`, skip only that blocked phase, and continue to later safe phases.

Commit once all completed phases pass verification. Do not push.

## Important Current Context

Codex has already completed and committed:

- `0b59fcd` Apply safe official squad field updates
- `24801b2` Improve official squad name matching
- `1efd9b2` Apply newly matched official squad fields
- `d870312` Polish simulation Japanese copy
- `bd3f3ed` Fix remaining Japanese mojibake
- `bcdb8dc` Explain tournament odds model

Before editing, inspect current `git log --oneline -8` and `git status --short`. Do not duplicate work already present. Do not revert Codex changes.

## Product Goal

Move the site closer to a polished, trustworthy 2026 World Cup simulation product.

Priorities:

1. More trust and explainability for predictions.
2. Better visibility into data freshness and roster coverage.
3. No visible mojibake or broken Japanese.
4. Compact, mobile-safe football UI.
5. No simulation/rating formula changes unless explicitly requested.

## Hard Boundaries And Aggressive Work Policy

Allowed:

- add read-only data quality summaries from existing seed/report files
- expose read-only quality/trust data through API/UI
- improve copy, empty states, loading states, and responsive layout
- add deterministic audit scripts/tests for text encoding and data quality
- add browser smoke-check notes to `docs/codex/PROGRESS.md`
- make simulation or rating-adjacent changes only when this spec explicitly calls for an isolated, test-covered, before/after-reported experiment
- commit bold changes locally when verification passes, so Codex can review the exact diff afterward

Not allowed:

- add or delete seed players
- overwrite player/manager ratings
- change simulation formulas without a before/after audit report and focused tests
- change rating formulas without a before/after audit report and focused tests
- change market values, career stats, or manual overrides
- fetch or invent unverifiable player/manager data
- broad refactors unrelated to the phases
- push to remote

## Phase 1: Text Encoding Guardrail

Add a deterministic guardrail so mojibake does not silently return.

Suggested implementation:

- Add `backend/scripts/audit_text_encoding.py`
- Scan at least:
  - `frontend/src/**/*.ts`
  - `frontend/src/**/*.tsx`
  - `backend/app/**/*.py`
  - `backend/tests/**/*.py`
  - selected `docs/**/*.md`
- Flag:
  - replacement character `�`
  - halfwidth-katakana characters in source UI strings
  - known mojibake markers such as `縺`, `繝`, `莠`, `蜆`, `螟`, `邇`, `謗`
- Allow explicit test marker lines only when they are part of a test asserting mojibake is absent.

Add tests or a documented command.

Acceptance:

- The script exits non-zero if a temporary file/string with mojibake is included in its scan scope.
- The current repository scan passes.

## Phase 2: Data Quality Summary API

Create a read-only data quality summary from existing local files.

Suggested backend endpoint:

- `GET /api/data-quality/summary`

Suggested fields:

- `seed_player_count`
- `seed_team_count`
- `official_profile_players`
- `official_profile_coverage_pct`
- `remaining_unmatched_official_players`
- `remaining_unmatched_seed_players`
- `coach_mismatch_count`
- `matched_player_field_update_candidates`
- `last_seed_update`
- `last_report_update`
- `control_character_issues`
- `notes: string[]`

Sources:

- `backend/data/seed/players2026_official.json`
- `backend/data/seed/teams2026_official.json`
- `backend/data/seed/metadata.json`
- `backend/reports/fifa_squad_merge_proposal_2026-06-22.json`
- `backend/reports/fifa_squad_diff_2026-06-22.json`

Do not mutate any data.

Acceptance:

- Endpoint returns counts matching the current reports:
  - unmatched official players: 652
  - unmatched seed players: 73
  - matched-player field update candidates: 0
- Control-character issues are 0 for current backend JSON files.
- Tests cover normal summary and missing-report fallback.

## Phase 3: Product-Facing Data Quality Panel

Add a compact data quality panel to the home page or tournament page.

Preferred location:

- Home page, below the two mode cards.

Display:

- official profile coverage percentage
- remaining official/seed unmatched counts
- matched update candidates
- last update
- short notes from the API

UX requirements:

- quiet dashboard style, not a marketing card explosion
- mobile-safe
- no nested cards
- no visible implementation instructions
- if API fails, show a calm small fallback instead of raw error text

Acceptance:

- Home page remains the first usable screen.
- Users can understand that the model has real data coverage and remaining roster risk.

## Phase 4: Match Detail Trust Polish

Improve match detail clarity without changing simulation behavior.

Allowed improvements:

- clearer labels for real result / detailed simulation / score prediction
- compact "data state" line near the score
- better empty state when no events are available
- ensure player ratings panel is absent or calm when data is not meaningful
- improve mobile spacing if text wraps awkwardly

Do not change match API, simulator, events, or scoring formulas unless strictly necessary for display.

Acceptance:

- Real result, detailed simulation, and score-only prediction states remain distinct.
- No blank/garbled state for Poisson prediction matches.

## Phase 5: Browser Smoke Checks

Use local servers if available, or start them if needed.

Smoke-check:

- `/`
- `/simulate`
- `/tournament`
- `/teams/BRA`
- one generated match detail page

At desktop width and at least one mobile-ish width, verify:

- no replacement characters
- no halfwidth-katakana mojibake
- no full-page horizontal overflow
- key panels render

Document results in `docs/codex/PROGRESS.md`.

## Phase 6: Simulation Accuracy Audit Report

This phase is intentionally more ambitious. Produce a concrete audit of current simulation behavior before making formula changes.

Add a script, for example:

- `backend/scripts/audit_simulation_accuracy.py`

Use existing local data only.

The report should answer:

- Which teams have the highest/lowest attack, defense, and strength ratings?
- Which top-20 team matchups look implausible by expected goals or win probability?
- Are host-nation advantages visible for USA/MEX/CAN?
- Are tactical profiles actually moving expected goals in realistic directions?
- How often do underdogs win in Monte Carlo at 100/500 iteration samples?
- Do current champion odds look too concentrated or too flat?

Write:

- `backend/reports/simulation_accuracy_audit_YYYY-MM-DD.json`

Include:

- model version
- sample matchups
- champion odds sample
- warnings
- recommended changes

Acceptance:

- This phase may produce warnings without changing formulas.
- The report must be deterministic when given a seed.
- Tests should cover at least one deterministic audit helper.

## Phase 7: Formula Improvement Experiment

This phase may change simulation behavior, but only with guardrails.

Allowed changes:

- tune existing `ModelConfig` constants
- adjust how tactical matchup modifier is weighted
- adjust host advantage if audit shows it is too weak/strong
- improve penalty shootout probability bounds if clearly justified

Not allowed:

- introduce a new complex simulation engine
- add new player attributes without evidence
- make arbitrary changes because one favorite team "feels wrong"

Required:

1. Keep the change small and explainable.
2. Add a before/after report under `backend/reports/`, e.g.
   - `simulation_formula_experiment_YYYY-MM-DD.json`
3. Include:
   - before config
   - after config
   - 10 representative matchup deltas
   - champion odds before/after for at least 200 Monte Carlo iterations
   - risk notes
4. Add focused tests for deterministic behavior and probability sanity.

Acceptance:

- Backend tests pass.
- Changes are explainable from the audit, not arbitrary.
- Codex can later revert the commit cleanly if the experiment is not good enough.

## Phase 8: Roster Reconciliation Candidate Report

Work on the remaining roster risk more aggressively, but still do not directly add/delete players.

Current remaining risk after Codex work:

- unmatched official players: 652
- unmatched seed players: 73

Create a candidate report:

- `backend/reports/roster_reconciliation_candidates_YYYY-MM-DD.json`

For each team, propose:

- high-confidence add candidates from official list
- likely stale seed players
- ambiguous pairs requiring Codex/user review
- candidate reason
- risk level: `low`, `medium`, `high`

Signals may include:

- official player unmatched and seed roster below 26 players
- seed player unmatched and official roster has same position group
- team has clear stale 2022-style names
- name similarity after conservative normalization

Do not mutate seed files.

Acceptance:

- Report is useful enough for Codex to decide the next import spec.
- Tests cover candidate classification helpers.

## Phase 9: Match Detail Analysis Upgrade

This phase may touch frontend and backend response shape if needed.

Product goal:

- make match detail feel like a serious football analysis page, not just a replay.

Allowed:

- add derived match insights from existing Match fields/events:
  - turning point event
  - xG-like expected pressure summary if already derivable from events or shots
  - momentum segments
  - key player contributions from existing player ratings/events
  - tactical note using formations and manager/tactical profile
- expose a small read-only `analysis` object on match detail API if clean
- show it compactly on `MatchDetailPage`

Not allowed:

- fabricate event data for Poisson-only prediction matches
- change event generation unless part of Phase 7 and covered by tests

Acceptance:

- Detailed simulation matches gain visible analysis.
- Real/score-only matches show calm limited-data states.
- Mobile layout remains readable.

## Phase 10: Long-Run Autonomous Loop

If all phases above complete before noon, do not stop immediately.

Continue with this loop:

1. Run the encoding audit.
2. Run backend tests.
3. Run frontend lint/build.
4. Inspect `docs/codex/PROGRESS.md` open risks.
5. Pick the highest-impact remaining risk that does not violate boundaries.
6. Implement a focused fix with tests.
7. Commit and report.

Only stop if:

- a Stop condition in `AUTONOMOUS_SPRINT_PROTOCOL.md` applies
- tests fail and focused investigation cannot isolate the cause
- the only remaining meaningful work requires unverifiable external player/manager facts

## Verification

Run:

```bash
cd backend
.\venv\Scripts\python.exe -m pytest
```

Run:

```bash
cd frontend
npm run lint
npm run build
```

Run the new text/data-quality audit command if added.

For Phase 6/7, also run the new simulation audit/experiment scripts and record report paths.

## Commit Policy

Commit when required verification passes.

Suggested commit messages:

```text
Add data quality summary and UI guardrails
Audit simulation accuracy and tune model
Add roster reconciliation candidate report
Upgrade match detail analysis
```

Do not push.

## Report Back

After committing, report:

- commit hash
- phases completed/skipped
- changed files
- verification results
- browser smoke checks
- remaining risks
