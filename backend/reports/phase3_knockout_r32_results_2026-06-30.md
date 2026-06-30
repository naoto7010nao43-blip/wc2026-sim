# Phase 3 (①) — Round-of-32 real results reflected (2026-06-30)

## Goal
Continue reflecting finished 2026 World Cup matches in the simulator. The
group stage (72 matches) was already done; this increment adds the **real
Round-of-32 knockout results** that have been played so far.

## What was done

### 1. Pinned FIFA's real third-place assignment (`app/engine/bracket.py`)
Our generated R32 bracket already matched reality on 11/16 matchups; the 5
differences were all in *which* third-placed group filled which winner's
slot. The qualifying third-place set `{B,D,E,F,I,J,K,L}` was already correct,
but the generic candidate-pool search picks *a* valid permutation, not
necessarily FIFA's literal one.

Added `FIFA_THIRD_PLACE_TABLE`, a curated row keyed by the sorted qualifying
combination. For the real 2026 set it pins:
`A1→E, B1→J, D1→B, E1→D, G1→I, I1→F, K1→L, L1→K`
(verified to satisfy every slot's candidate pool). This reproduces the genuine
R32: GER-PAR, USA-BIH, BEL-SEN, MEX-ECU, FRA-SWE, SUI-ALG, ENG-COD, COL-GHA.
Other (hypothetical) combinations still fall back to the deterministic search.

### 2. Knockout real-results infrastructure (`app/services/real_results.py`)
- `load_real_knockout_results()` — loads a new `knockout.json`, keyed by
  team-pair frozenset (a knockout pairing is unique across the bracket).
- `persist_real_match()` generalised: `group_id`/`round`/`bracket_slot` are now
  keyword args (default `round="group"`), and it reads penalty fields
  (`went_to_penalties`, `penalty_home_score`, `penalty_away_score`). Drawn
  knockout matches emit a `penalty_shootout` event and a round-aware data
  source label (`Wikipedia (2026 FIFA World Cup knockout stage)`).

### 3. Wired into the bracket (`app/services/tournament.py`)
A `play_knockout(...)` helper checks `knockout.json` first (matching team-pair
*and* round) and falls back to the Poisson prediction. Used for R32, R16, QF,
SF, third-place and final — so future rounds only need data, no code.

### 4. Data (`data/seed/real_results/knockout.json`) — 4 finished R32 matches
Sourced from the Wikipedia 2026 FIFA World Cup knockout-stage page:
- **South Africa 0–1 Canada** (Jun 28): Eustáquio 90+2'. Canada advance.
- **Brazil 2–1 Japan** (Jun 29): Casemiro 56', Martinelli 90+5'; Sano 29'
  (佐野海舟). Japan eliminated.
- **Germany 1–1 Paraguay**, Paraguay win 4–3 on pens (Jun 29): Havertz 54';
  Enciso 42'. Paraguay advance.
- **Netherlands 1–1 Morocco**, Morocco win 3–2 on pens (Jun 29): Gakpo 72';
  Issa Diop 90+1'. Morocco advance.

## Validation
- `assign_third_place_slots(['B','D','E','F','I','J','K','L'])` returns exactly
  FIFA's real assignment.
- Full tournament run: all 4 R32 fixtures persist as `is_real` with correct
  scores, penalty scores and winners; CAN/BRA/PAR/MAR advance to R16,
  JPN/RSA/GER/NED are out.
- New `test_persist_knockout_match_with_penalties`; full suite 412 passed.

## Not in this change
- June 30 R32 matches (FRA-SWE, CIV-NOR, MEX-ECU) had not kicked off at deploy
  time — append to `knockout.json` once results are published.
- R16 onward remain simulated until played.
