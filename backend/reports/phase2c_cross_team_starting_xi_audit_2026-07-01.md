# Phase 2c — cross-team starting-XI accuracy audit (all 48 teams, 2026-07-01)

## Goal
User request: *"他に全ての国で先発情報を更新してシミュレーションサイトと違う点がないか確認して"*
— audit every team's **displayed likely XI** against its real, confirmed 2026 World Cup
lineup and fix the discrepancies, without fabricating any value (data-governance rule).

## Method
1. Ran a structural audit of all 48 `build_likely_lineup` outputs, classifying each of the
   11 slots as **exact** (player's primary position matches the slot), **alias** (a
   documented secondary/aliased position), or **FALLBACK** (a last-resort out-of-position
   fill because no eligible player existed).
2. For every FALLBACK team, cross-checked the displayed XI against the nation's
   **confirmed played 2026 WC lineup** (group stage / R32 have been played), which is the
   authoritative source-of-truth and avoids guessing.
3. Two fix types:
   - **A-type** — a real confirmed starter is entirely **missing** from the roster, so the
     slot is auto-filled wrong. Add the player with citable EA SPORTS FC 26 values
     (`dataConfidence="external"`, never "official") + a `startingProbability` override
     sourced from a played-match XI. Tool: `scripts/add_missing_starters.py` (idempotent).
   - **B-type** — the right player is present but mis-weighted/mis-positioned. Correct via a
     `startingProbability` override and/or a cited secondary-position addition.

## Root cause (applies to all 48 teams)
The seed rosters are **thin (12–19 players, not the full 23–26)**. With a partial squad the
builder's last-resort pass drops a wrong-position player into any slot the roster can't
cover — e.g. a striker at centre-back, or a left-back at right-wing. **18 of 48 teams** had
at least one FALLBACK slot; the rest were exact/alias-clean.

## Fixed & deployed this campaign (each confirmed from a real 2026 WC lineup)
| Team | Fix | Type | Player added / corrected | EA id / source |
|---|---|---|---|---|
| JPN | left shadow-striker | A | Keito Nakamura (LM) | EA 242914 (Phase 2b) |
| NOR | left wing | A | Antonio Nusa (LM) | EA 262863 |
| ECU | back-three CB | A | Joel Ordóñez (CB) | EA 268611 |
| URU | left wing | A | Maximiliano Araújo (LM) | EA 254817 |
| CRO | left wing-back | B | Ivan Perišić → LB secondary + override | existing player |
| SCO | right wing | A | **Ben Doak (RM)** | EA 266815, OVR 71 |

**Ben Doak (this batch):** confirmed Scotland starter — started on the right wing vs Brazil
(Group C) and created several chances vs Haiti. The roster had no natural right winger, so
the RW slot was wrongly filled by a left-back (Kieran Tierney). Added with exact EA FC 26
values (PAC 89 / SHO 61 / PAS 63 / DRI 75 / DEF 28 / PHY 60, AFC Bournemouth, age 20) and a
`startingProbability=78` override. After the fix, Scotland's front line is Doak + Christie +
Adams (both real wide players now start; the LB-at-RW fallback is eliminated).
- EA page: https://www.ea.com/games/ea-sports-fc/ratings/player-ratings/ben-doak/266815
- Confirmed starter: ESPN — Scotland vs Brazil line-ups (2026 WC Group C)

## Deferred — honest scope boundary (no fabrication)
These FALLBACK teams were **checked** but not fixed, because doing so responsibly would
require sourcing a specific missing player + their EA rating + a confirmed XI, and the
evidence bar could not be met without guessing:

- **GER** — the displayed LW (Havertz) is a fallback, but Germany **rotated heavily**: the
  confirmed R32 XI vs Paraguay *dropped Musiala* and started Nathaniel Brown & Felix Nmecha,
  neither of whom is in the roster. No single stable XI can be asserted, so forcing
  "Musiala on the left" would contradict the actual played match. Deferred.
- **USA** (3-5-2 forces Pulisic to LM) and **KOR** (3-4-2-1 forces winger Hwang Hee-chan to
  a back-three CB) are **formation-shape** issues rather than a single missing player;
  resolving them needs a sourced formation change, deferred pending single-source confirmation.
- **AUT, AUS, CZE, JOR, KSA, NZL, RSA, UZB, COD, HAI** — each needs a real defender or
  central midfielder who is absent from the thin roster (e.g. Jordan's & Haiti's third
  centre-back is currently a forward auto-filled into defence). Their confirmed XIs and/or EA
  ratings for the specific missing players could not be reliably sourced, so they are left
  as-is rather than fabricated. They remain candidates as sources become citable.

## Validation
- `scripts/rebuild_player_ratings_v2.py`: 676 ratings, 505 EA-sourced, 0 low-confidence,
  0 missing-critical-data (diff computed against the committed baseline).
- Legacy `players.json` regenerated as the canonical mirror (not hand-edited).
- Backend suite: **438 passed** (bumped the seed-count / external-count / override-count
  guardrails; the diff-report guardrail now asserts the risers/fallers *structure*, since a
  pure roster-addition + override batch legitimately produces no `overall` movement).

## Honesty notes
- Every added value carries a source URL; nothing was fabricated or marked "official".
- The no-guessing rule caught two would-be errors this campaign: Ecuador (Félix Torres was a
  *substitute*, real CB = Ordóñez) and Germany (Musiala was *benched* in the R32), both
  corrected by deferring to the confirmed played XI instead of an assumption.
