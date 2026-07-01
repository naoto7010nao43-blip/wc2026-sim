# Phase 2e — formation / position-fit audit across all 48 teams (2026-07-01)

## What this checks
Now that the simulator fields the *displayed* XI (Phase 2d), a team's
`defaultFormation` directly determines who actually plays and *where*. This
audit joins `players.json` (positions) with `playerRatings2026_estimated.json`
(`startingProbability`, `overall`) and runs the shared
`select_starting_assignments()` for each team's `defaultFormation`, flagging:

- **OOP** — a slot filled by a player whose primary position (and secondary
  positions) don't include that slot. I.e. someone played out of position
  because the formation had no natural slot for the roster's actual specialists.
- **LOWPROB** — a *fielded* starter whose `startingProbability` < 40 (a weak
  or rotation-risk starter the model is nonetheless forced to start, usually
  because the roster is thin at that position).

Reproduce: `backend/reports/_phase2e_audit.py` (analysis only — no data writes).

## Reading the flags — two very different buckets

### Bucket A — benign positional flex (NO fix needed)
The formation simply lacks an exact slot, so a versatile player fills an
adjacent one. Correct player, correct that he starts, only the slot label
differs. Do **not** "fix" these — they reflect real usage.

- ARG 4-4-2: Enzo Fernández (CDM) → LM, Lo Celso (CAM) → RM
- COL 4-3-3: James Rodríguez (CAM) → CM  *(4-3-3 has no CAM slot)*
- GER 4-2-3-1: Havertz (ST) → LW, Rüdiger (CB) → RB
- CRO 3-4-2-1: Pašalić (CM) → CDM
- SEN 4-2-3-1: Pape Matar Sarr / Lamine Camara (CM) → CDM/CAM
- URU 4-2-3-1: Valverde (CM) → CDM
- SCO 4-3-3: Ryan Christie (CAM) → RW (rotation option; Doak is the sourced RW starter)
- MAR, EGY, QAT, TUN, KOR, KSA, NZL, SWE, PAN, CAN: single adjacent-slot flex

### Bucket B — possible wrong formation / missing specialist (needs a citable source before any change)
Multiple genuine specialists crammed out of position, which usually means the
`defaultFormation` doesn't match how the side actually lines up, **or** the
(thin, 12–15 man) roster is missing the central players the formation needs.
Both fixes require a citable real-lineup / formation source — deferred, not
guessed (per DATA_GOVERNANCE_POLICY.md).

| Team | Formation | Out-of-position crammed in | Likely issue |
|---|---|---|---|
| GHA | 4-4-2 | Kamaldeen (LW)→LM, Semenyo (RW)→CM, Partey (CDM)→CM, Issahaku (RW)→RM | 4 wide/DM players in a flat midfield 4 → real shape is almost certainly 4-2-3-1 / 4-3-3, or squad is missing 2 central mids |
| PAR | 4-4-2 | Villasanti (CDM)→LM, Almirón (RW)→CM, Enciso (CAM)→RM | wingers/CAM forced central |
| USA | 3-5-2 | A. Robinson (LB)→CB, Pulisic (RW)→LM, Tillman (CAM)→CDM | back-3 vs a squad built as a back-4; wide/attacking mids forced deep |
| BIH | 4-4-2 | Vranješ (CB)→RB, Hadžiahmetović (CDM)→LM, Alajbegović (CAM)→RM | thin roster, no natural wide mids |
| CZE | 3-5-2 | Coufal (RB)→CB, Jurečka (LB)→CDM | no natural 3rd CB / holding mid |
| COD | 3-5-2 | Wan-Bissaka (RB)→CB, Masuaku (LB)→CDM | full-backs into a back-3 + midfield |
| HAI | 3-4-2-1 | Isidor (ST)→CB, Jean Jacques (CM)→CAM, Etienne (RW)→CAM | very thin roster |
| JOR | 3-4-2-1 | Saadeh (CM)→CB, Abu Zrayq (ST)→CB | no 3rd/4th natural CB |
| UZB | 3-4-2-1 | Khamdamov (LM)→CB, Sergeev (ST)→CM | back-3 with no 3rd CB |
| RSA | 4-3-3 | Zwane (CAM)→CM, Rayners (ST)→LW | fine-ish; monitor |
| SUI | 4-4-2 | Ndoye (RW)→LM, Xhaka (CDM)→RM | wingers/DM into flat 4 |

## Recommendation / next unit
1. **Do not auto-change formations.** Each Bucket-B fix needs a citable
   real-lineup or a citable "usual formation" source (Tier-A per policy).
2. Priority order by severity (most players displaced): **GHA → PAR → USA →
   BIH → SUI**.
3. For roster-gap cases (JOR, UZB, HAI, CZE, COD), the fix may be *adding a
   missing sourced specialist* via `scripts/add_missing_starters.py` (the
   same path used for Doak/Nusa/Ordóñez), not a formation change — again only
   with a citable source and full pipeline rebuild.

Nothing in Bucket B was changed in this pass — this report is the sourced
work-list for the next iteration.
