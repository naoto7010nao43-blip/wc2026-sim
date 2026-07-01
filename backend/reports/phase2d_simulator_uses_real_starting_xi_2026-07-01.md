# Phase 2d — the simulator now fields the real starting XI (2026-07-01)

## The bug (found while auditing Phase 2a–2c)
The site had **two different lineup selectors that disagreed**:

- `app.rating_v2.lineup_builder.build_likely_lineup` (the **displayed** XI) scored
  players by **`startingProbability`** — real-world starting likelihood.
- `app.engine.state.build_team_state` (the **simulator**) scored players by raw
  **`overall`** — "strongest available per slot".

So every sourced real-starter correction from Phase 2a/2b/2c fixed only the *shown*
lineup; the **actual simulation still fielded someone else**. Measured impact:

> **29 of 48 teams simulated a different XI than the site displayed** (34 player-slots).

The most concrete cases were **goalkeepers**: the Phase 2a No.1-keeper fixes (ESP Unai
Simón, SUI Kobel, USA Freese, COL, URU, CAN…) corrected the display, but the simulator
kept fielding a higher-`overall` **backup** keeper. Outfield too — Scotland's newly added
Ben Doak (OVR 71) was still benched in-sim behind Kieran Tierney (OVR 77, a left-back),
re-creating in the simulation the exact wrong-position start we'd just fixed on screen.
Even Japan's Keito Nakamura (added Phase 2b) was shown but not simulated.

## The fix
Extracted a single shared selector, `app.engine.lineup_selection.select_starting_assignments`
(scored by `startingProbability`, falling back to `overall`, with strict GK/outfield pool
separation), and made **both** `build_team_state` and `build_likely_lineup` call it. The
displayed XI is now, by construction, the XI that gets simulated.

- New module: `app/engine/lineup_selection.py` (`select_starting_assignments`, `lineup_score`).
- `app/engine/state.py::build_team_state` — delegates slot assignment to the shared selector
  (removed its private `overall`-only `pick()`), then builds `PlayerState`s + bench as before.
- `app/rating_v2/lineup_builder.py::build_likely_lineup` — delegates to the same selector,
  then formats display dicts. (Its old "deliberately kept separate / scored by overall"
  docstring described the very divergence that was the bug; updated accordingly.)

This reverses an earlier *intentional* separation. That separation existed so display edits
couldn't perturb simulation results — but the correct goal for a realism simulator is the
opposite: the sourced real-starter data *should* drive what gets simulated.

## Result (verified)
- Divergence: **29/48 → 0/48 teams**. Simulated XI == displayed XI for all 48.
- Simulator now fields the real No.1 keepers (e.g. ESP → Unai Simón), real wingers
  (SCO → Ben Doak, not Tierney), and every other sourced starter (JPN → Zion Suzuki + Nakamura).
- Backend suite: **442 passed** (438 + 4 new). New `tests/test_lineup_selection.py` locks the
  invariant: a lower-overall No.1 keeper / real winger is fielded over a stronger substitute,
  and `build_team_state`'s XI is asserted identical to `build_likely_lineup`'s.

## Why this is safe
- The synthetic test squads (uniform `overall`, no `startingProbability`) fall back to
  `overall`, so their selection — and every deterministic match assertion — is unchanged.
- No fabricated data: this is a pure engine-consistency fix; it changes *which already-present,
  already-sourced* players are fielded, using the `startingProbability` values the rating
  pipeline already computes for every player (100% coverage).
