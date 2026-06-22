# Spec 003: Match Detail Trust States

## Status

Ready for Claude Code implementation.

## Product Goal

Improve the match detail page as the core "watchable football simulation" screen by making data source, confidence, and unavailable sections clear.

This task must not change simulation math. It only improves how existing match data is presented.

## Background

There are multiple match types:

- real results, loaded from seed data
- detailed simulated single matches, with lineups/events/stats/player ratings
- Poisson-generated tournament matches, usually with only scoreline and limited metadata

The current UI mostly handles these cases, but the customer can still wonder why some matches have no pitch, no event log, or no player ratings. We need explicit trust/source states.

## Files To Inspect

- `frontend/src/pages/MatchDetailPage.tsx`
- `frontend/src/components/MatchEventTimeline.tsx`
- `frontend/src/components/PlayerRatingsPanel.tsx`
- `frontend/src/types/domain.ts`
- `frontend/src/api/client.ts`

## Allowed Files To Change

Prefer limiting changes to:

- `frontend/src/pages/MatchDetailPage.tsx`
- `frontend/src/components/MatchEventTimeline.tsx`
- `frontend/src/components/PlayerRatingsPanel.tsx`

Add a small local helper/component file only if it keeps the code cleaner.

## Requirements

### 1. Add a clear match source/confidence strip

Near the top of `MatchDetailPage`, show a compact label explaining the match data type:

- Real result: actual result data.
- Simulated detailed match: event-level simulation.
- Poisson model match: scoreline prediction only.

Use existing fields:

- `match.is_real`
- `match.data_source`
- `match.events.length`
- `match.home_lineup.length`
- `match.player_ratings.length`

Do not add backend fields.

### 2. Improve unavailable states

When the match has no events:

- Do not show an empty timeline as if something failed.
- Show a short, calm explanation that event replay is unavailable for this match type.

When the match has no lineup:

- Keep the existing pitch fallback, but make it clearer that this is a data-availability limitation, not an error.

When there are no player ratings:

- `PlayerRatingsPanel` currently returns `null`.
- Replace this with a compact unavailable state only when the parent chooses to show the ratings section.
- Avoid making the page feel broken.

### 3. Keep current replay behavior for event-rich matches

For matches with events:

- Timeline, slider, play button, pitch, and player ratings should behave as before.
- Do not remove existing functionality.

### 4. Keep Japanese customer-facing copy

Use concise Japanese UI copy.

Tone:

- trustworthy
- analytical
- not apologetic
- no overclaiming

### 5. Keep design restrained

This is an analysis product, not a marketing page.

Use existing Tailwind style conventions:

- slate background
- emerald/amber status accents
- compact panels
- no broad redesign
- no new visual assets

## Explicit Non-Goals

- Do not change backend APIs.
- Do not change simulation formulas.
- Do not add xG unless backend support already exists.
- Do not invent player stats.
- Do not redesign the whole match page.
- Do not touch tournament bracket logic.

## Verification

Run from `frontend/`:

```bash
npm run lint
npm run build
```

Also sanity-check locally if dev servers are running:

- open or curl `http://localhost:5173`
- inspect at least one match detail page if an existing match id is available

If no match id exists, do not create broad backend changes just for this task.

## Acceptance Criteria

- Match detail page explains why data is present or missing.
- Event-rich matches still support replay.
- Scoreline-only matches do not look broken.
- `npm run lint` passes.
- `npm run build` passes.

## Report Back

After implementation and commit, report:

- commit hash
- changed files
- summary
- verification results
- any risks or follow-up suggestions
