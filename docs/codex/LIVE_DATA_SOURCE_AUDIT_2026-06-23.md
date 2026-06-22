# Live Data Source Audit - 2026-06-23

## Purpose

Identify the next reliable data sources for improving 2026 World Cup simulation accuracy.

This audit is source planning only. It does not update seed data or ratings.

## Confirmed Source Candidates

### FIFA Official Squad List

URL:

https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf

Observed current document:

- Title: `FIFA World Cup 2026`
- Coverage: squad list pages for the 48 teams
- Includes: player position, player name, date of birth, club, height, caps, goals
- Includes: head coach name and nationality
- Observed timestamp: `Monday, 22 June 2026 | 03:11 UTC | Version 1`

Why it matters:

- This should become the roster/coach source of truth.
- It can fill the project's current high-risk missing fields:
  - caps
  - national-team goals
  - height
  - club
  - official coach name
  - official position class

Current project state:

- `backend/data/seed/metadata.json` still marks `FIFA Official Squad feed` as `not_yet_integrated`.
- Player/manager data therefore remains partly estimated even when the current tournament source exists.

### FIFA Schedule / Fixtures / Results

URL:

https://www.fifa.com/en/articles/match-schedule-fixtures-results-teams-stadiums

Why it matters:

- This should be the preferred source for completed match results.
- Completed group matches should be fixed inputs in simulations, not resampled.

Current project state:

- The backend already has `backend/data/seed/real_results/`.
- The remaining gap is source-backed sync freshness, not core modeling.

### FIFA World Rankings

URL:

https://www.fifa.com/en/world-rankings

Why it matters:

- The Poisson model currently uses FIFA rank as one team-strength input.
- Ranking values should be updated from the current official ranking table before any calibration tuning.

Current project state:

- Metadata marks `FIFA World Ranking (fifa_rank field)` as active.
- Freshness policy is `30` days.

## Source Priority

1. Official match results
   - Highest impact during the live tournament.
   - Prevents already-played games from being simulated incorrectly.

2. Official squad list
   - Highest impact for player/manager credibility.
   - Enables better starting probability, caps, age, height, club context, and coach validation.

3. Injury/suspension availability
   - Very high impact but not yet source-wired.
   - Must be labelled as missing until a reliable source is selected.

4. Rankings / Elo
   - Useful for team strength calibration.
   - Should not override real results or roster availability.

## Recommended Next Spec

After Spec 006:

`Spec 007: Official FIFA Squad Importer`

Goal:

- Add a read-only/import script that can parse or ingest the official FIFA squad list into a normalized intermediate JSON report.
- Do not overwrite current seed data automatically.
- Generate a diff report first:
  - missing players
  - extra players
  - coach mismatches
  - club/caps/goals/height fields newly available
  - teams with strong data drift

Acceptance:

- Running the importer produces a report under `backend/reports/`.
- No simulation formulas change.
- No seed data changes without a separate reviewed spec.

## Decision

Do not manually patch individual player data tonight.

The correct next move is a controlled official-source ingestion/diff workflow, because hand-editing player and manager data would create hidden provenance risk.
