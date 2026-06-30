# Phase 3 (①) — Group-stage real results completed (2026-06-30)

## Goal
Reflect finished 2026 World Cup matches in the simulator. The real-results
pipeline (`app/services/real_results.py`) already existed but the data was
stale: Groups A–H had only matchdays 1–2, Groups I–L only matchday 1.

## What was done
Added the **32 missing group-stage matches** so all 12 groups now hold the
full 6 fixtures (72 total real matches). Every score, scorer and minute was
sourced from the Wikipedia 2026 FIFA World Cup group pages (the source the
existing data already cited), cross-checked against FIFA.com / ESPN / NPR for
the contested USA–Türkiye result.

- Groups A–H: matchday 3 (2 matches each)
- Groups I–L: matchdays 2 & 3 (4 matches each)

Minimal code change: `_build_events_legacy` now renders own goals
(`(オウンゴール)`, not linked to a roster player) and penalties (`(PK)`),
matching the API-sourced path. Several added matches contain own goals
(Bounou, Skhiri, Abunada, Nematov) and penalties (Lautaro, Wissa).

## Validation
- Computed group standings (pts, then GD, then GF) reproduce the real
  Wikipedia 1st/2nd placings for **all 12 groups** exactly.
- Goal events sum to the final score for every added match.
- Full suite: 411 passed; text-encoding audit clean.

## Notable real outcomes now reflected
- Japan 1–1 Sweden (Maeda 56'); Japan finishes 2nd in Group F behind NED.
- USA lose 2–3 to Türkiye but still win Group D.
- Cape Verde advance 2nd in Group H drawing all three matches.
- Germany edge Ivory Coast on head-to-head atop Group E.

## Next increment (not in this change)
Round-of-32 real results (RSA 0–1 CAN, BRA 2–1 JPN, GER–PAR & NED–MAR pens,
etc.). The current knockout bracket is simulated from the now-real group
standings; reflecting real knockout results needs a new knockout
real-results loader hooked into the bracket — deliberately deferred to keep
this unit focused and deployable.
