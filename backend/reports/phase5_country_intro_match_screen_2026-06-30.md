# Phase 5 (③) — "対戦国ガイド" on the match screen (2026-06-30)

## Goal
The user asked that the **match screen introduce each country** — tactics, key
players and background — for viewers who don't follow these national teams.
Previously the match detail page jumped straight into score / lineups / events,
which assumes the reader already knows who Paraguay or Morocco are.

## What was done

### New component `frontend/src/components/CountryIntroPanel.tsx`
A "対戦国ガイド" panel rendered near the top of every match screen, showing the
two nations side by side. For each country:
- **Badge + link** to the full team page.
- **Basic data** — FIFA ranking, confederation (Japanese label: 欧州/南米/
  北中米カリブ/アフリカ/アジア/オセアニア), manager, formation.
- **Playstyle one-liner** derived from the team's `tactical_profile` (press
  intensity + possession style → e.g. "高い位置からのプレス / ボール保持で主導").
- **注目選手 (key players)** — the squad's top 4 by overall rating, each with
  position, club and overall.

### Wired into `frontend/src/pages/MatchDetailPage.tsx`
The page now fetches both nations' full team data (`api.getTeam`) and renders
`CountryIntroPanel` between the scoreboard and the match timeline. The fetch is
best-effort: if either team request fails, the panel is simply omitted (the
rest of the match screen is unaffected).

## Honesty notes (data governance)
- Every figure shown is **derived from the app's own dataset** — FIFA rank,
  confederation, manager name, tactical profile numbers and player overall
  ratings. Nothing is fabricated.
- Deliberately **no unsourced prose history** (titles won, past tournaments,
  anecdotes). Such claims would need per-nation sourcing; instead the intro is
  built strictly from structured data already in the system, and the panel
  header states the figures are estimates from the app's data
  ("数値は本アプリのデータに基づく推定です").
- The key-player list reflects the same ratings used everywhere else in the
  app (EA FC 26-derived where applicable, marked external — never "official").

## Validation
- `tsc -b` clean; `vite build` succeeds (production bundle builds).
- Panel is additive and isolated; no backend change, no API change.

## Possible follow-ups
- A sourced one-line pedigree per nation (e.g. confederation titles) would add
  colour but requires citable sources for all 48 teams — deferred until the
  data can be gathered with URLs, per the no-unsourced-claims rule.
