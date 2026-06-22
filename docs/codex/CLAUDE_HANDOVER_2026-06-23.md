# Claude Code Handover - 2026-06-23

## Why this file exists

Codex hit a token limit and was unavailable. The user asked Claude Code to keep
working alone in the meantime, strictly within direction Codex had already
written down (no new product decisions), and to leave this report so Codex can
catch up on exactly what happened and why.

## What was done while Codex was offline

Implemented **Spec 007A: Official Squad Merge Proposal**, the "Next Ready Spec
Candidate" named at the bottom of `docs/specs/007-official-squad-data-update-direction.md`.
This was not a newly invented task — it was the next concrete step Codex had
already scoped and staged; Claude Code only carried out the implementation.

Commit: `ebe4064` — "Add Spec 007A: official squad merge proposal (read-only)"

### New files

- `backend/scripts/build_fifa_squad_merge_proposal.py`
  - Read-only. Reuses `audit_fifa_squad_list.py`'s PDF parsing and
    `official_matches_seed` name-matching rather than re-implementing it, so
    this report and the existing diff report always agree on who matched whom.
  - For each matched player, proposes filling in only the fields the seed
    record currently has as `null`: `dateOfBirth`, `heightCm`, `clubName`,
    `caps`, `nationalTeamGoals`. Never overwrites a field that already has a
    non-null value, and never modifies any seed file — it only writes a new
    report JSON.
- `backend/tests/test_build_fifa_squad_merge_proposal.py` — 4 tests, all
  passing, including one that asserts the script never touches seed files
  (`test_build_merge_proposal_never_touches_seed_files`).
- `backend/reports/fifa_squad_merge_proposal_2026-06-22.json` — generated
  output from a real run against the live FIFA PDF.

### Result of running it against the live PDF

- Matched player field updates proposed: **472**
- Unmatched official players: **776**
- Unmatched seed players: **197**
- Coach mismatches: **16**

These numbers are large because the seed's existing roster is still much
smaller than the official 26-per-team squad list (the same drift
`fifa_squad_diff_2026-06-22.json` already documented) — this report does not
fix that drift, it only stages proposed field-level updates for players that
already matched.

### Verification performed

- Backend test suite: **129 passed** (full suite, not just the new file).
- Frontend `npm run lint` and `npm run build`: clean (run defensively; no
  frontend files were touched this task).
- `git status --short` confirmed before committing that no file under
  `backend/data/seed/` was modified.
- Spot-checked a handful of BRA proposed updates by eye (e.g. Alisson Becker:
  DOB `02/10/1992`, club `Liverpool FC (ENG)`, caps `80`) against what's in the
  official PDF text extraction — all plausible, no fabricated values.

## What was deliberately NOT done

- **Did not apply any of the 472 proposed updates to seed files.** Spec 007's
  own staging explicitly separates "merge proposal" (007A, done) from
  "reviewed seed update" (a later stage requiring its own spec). Applying
  updates without review is exactly what spec 007's "Do Not Do Yet" list warns
  against.
- Did not touch the 776 unmatched official players or the 197 unmatched seed
  players beyond listing them in the report. No new players were added, no
  existing seed players were deleted.
- Did not change any simulation formula, rating model, or the existing
  `audit_fifa_squad_list.py` matching heuristic.
- Did not write any new product-direction or policy document — this report
  and the script's own docstring are implementation notes, not direction.
- Did not push to the remote (per existing protocol: commit locally, never
  push without explicit instruction).

## Known caveat carried over from the existing audit

The name-matching heuristic (`official_matches_seed`, in
`audit_fifa_squad_list.py`, unmodified by this task) is known to be
imperfect — e.g. it previously missed `BRA_EDERSON` against the official
"EDERSON Ederson SANTANA DE MORAES" name block. That means some of the 776
"unmatched official players" and 197 "unmatched seed players" in the new
report are likely real matches the heuristic missed, not actually new/extra
players. This was already a known, documented limitation before this task;
it was not introduced or fixed here.

## Additional verification performed (browser smoke check)

`docs/codex/PROGRESS.md`'s "Next Codex actions" listed "Review TeamPage
data-trust UX after local visual smoke checks" as still open. With remaining
time before Codex's recovery, Claude Code ran a full browser-driven smoke
check (headless Playwright via `npx playwright`, both backend `:8000` and
frontend `:5173` dev servers already running) across every route, to give
Codex concrete visual evidence to review rather than just code. No code was
changed for this — verification only.

Checked, all clean (no console errors, no failed requests, no layout
overflow):

- `/teams/BRA` — desktop (1280px) and mobile (390px) viewports. Data-trust
  panel (3-axis tactical bars + 選手数/推定/平均不確実性/低信頼度属性あり
  summary), roster table sorted by overall, predicted lineup with starting
  probability badges — all rendered correctly at both widths, no horizontal
  overflow on mobile.
- `/tournament` — ran the full 104-match batch simulation
  (`大会を一括シミュレーション`) and the Monte Carlo title-odds panel
  (`優勝確率を計算する`). Bracket, group standings, and odds list all
  rendered. Re-visiting the page after a run correctly showed persisted
  server-side tournament state (button label changed to
  `もう一度シミュレーション` + a `リセット` button appeared) — confirms
  `/api/tournament/state` round-trips correctly.
- A knockout-round match from that batch run (`/matches/8bf5602b-...`,
  Round of 32, GER vs CZE) and a group-stage match
  (`/matches/f926b2a5-...`, CRO vs PAN) both opened correctly with the
  `スコア予測モデル` trust badge and the spec-003 explanation
  ("この試合はスコア予測モデルによる結果のため、イベント再現は利用できません。").
  Worth noting for Codex: the bulk tournament-simulation endpoint appears to
  use the Stage B Poisson model for every match, including group stage — not
  just knockout rounds. The micro-simulator with full event replay is only
  reachable through the dedicated single-match `試合シミュレーター`
  (`/simulate`) flow. This matches the two modes' own descriptions on the
  homepage, so it reads as intentional design rather than a bug, but it's
  worth Codex explicitly confirming that's the intended behavior.
- `/simulate` — spec 004's prediction panel rendered correctly (win/draw/win
  probability bars, expected goals, top scorelines with probabilities, model
  name `poisson-v1`, data confidence `estimated`, disclaimer text). Running
  an actual simulation (CZE vs MEX) navigated to a match detail page with the
  `詳細シミュレーション` badge, full event timeline, pitch visualization,
  possession/shots/cards stats, Man of the Match, and a complete player
  ratings table for both teams — all rendered correctly with no errors.

No bugs found. This is evidence for Codex's pending UX review, not a
substitute for it — Codex should still make the actual call on whether the
data-trust panel's wording/layout meets product bar.

## Follow-up fixes found during the smoke check

The browser sweep above also surfaced one real, narrowly-scoped bug, which
was fixed (not just noted), verified, and committed separately:

- **Commit `ca27388`** — "Show calm not-found messages instead of raw fetch
  errors". Visiting `/teams/<invalid-id>` or `/matches/<invalid-id>` rendered
  the raw `Error: GET /api/teams/ZZZ failed: 404` string with no way back —
  the whole page was just `String(e)` dumped into a `<p>`. Replaced with a
  calm Japanese not-found message plus a link back (`TeamPage.tsx`,
  `MatchDetailPage.tsx`), matching the calm-wording-over-raw-text precedent
  spec 006 already established for `PlayerRatingsPanel.tsx`. Verified with
  `npm run lint` / `npm run build` (clean) and a re-run of the same Playwright
  check on both invalid routes (now shows the friendly message). Deliberately
  left the other 6 inline-error spots in the app (`TournamentPage`,
  `SimulatorPage`, `LikelyLineupPanel`, `MatchPredictionPanel`,
  `TournamentOddsPanel`) untouched — those keep the rest of the page visible
  and already prefix the raw error with a labelled Japanese sentence, so they
  read as acceptable as-is; only the two full-page replacements were broken.
- **Commit `3789379`** — added a test for `build_merge_proposal`'s
  "team entirely absent from the official PDF" branch
  (`teamsMissingInOfficialPdf`), which the original spec 007A test fixture
  never exercised. No behavior change, backend suite now at 130 passed.
- Also did a full console-message sweep (not just errors) across `/`,
  `/tournament`, `/simulate`, `/teams/BRA` — no React warnings (no missing
  `key` props, no act() warnings, nothing) — and a mobile-viewport
  (390px) overflow check on `/`, `/tournament`, `/simulate` — all clean, no
  horizontal overflow, no console errors.

## Suggested next step for Codex

The natural follow-up is deciding whether/how to spend a "Spec 007B" on:

1. Reviewing `backend/reports/fifa_squad_merge_proposal_2026-06-22.json` and
   deciding which of the 472 proposed field updates to actually apply to seed
   files (the "reviewed seed update" stage spec 007 already anticipated).
2. Optionally tightening `official_matches_seed` first, since a better
   matcher would shrink the unmatched lists before any manual review effort
   is spent on them.

Both are product/data-policy calls, so left to Codex rather than decided here.
