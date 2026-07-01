# Phase 2b (①/starting-XI accuracy) — add missing real starter Keito Nakamura (2026-07-01)

## Goal
Improve the accuracy of the **displayed outfield starting XI**. Phase 2a fixed the
No.1 goalkeepers via `startingProbability` overrides, but that mechanism can only
re-weight players **already in the roster** — it cannot add a starter who is
missing entirely. Japan's roster had 16 outfielders and was **missing Keito
Nakamura (中村敬斗)**, a genuine 2026 World Cup starter, so his left
shadow-striker slot in the 3-4-2-1 was being auto-filled by the wrong player.

## What was done — one sourced, unambiguous addition
Added **Keito Nakamura** to the dataset with values taken verbatim from citable
sources (no guessing):

| Field | Value | Source |
|---|---|---|
| Overall / position | 76, LM | EA SPORTS FC 26 official ratings, player **242914** |
| Club / age / height | Stade de Reims, 25, 180cm | same EA page |
| PAC/SHO/PAS/DRI/DEF/PHY | 79 / 74 / 71 / 77 / 41 / 74 | same EA page |
| Date of birth | 28/07/2000 | Wikipedia |
| Starter status | started & scored Japan's WC opener vs Netherlands; assisted vs Tunisia | Wikipedia + match reports |

- EA page: https://www.ea.com/en/games/ea-sports-fc/ratings/player-ratings/keito-nakamura/242914
- Wikipedia: https://en.wikipedia.org/wiki/Keito_Nakamura

Files touched (the full v2 pipeline, then legacy mirror regenerated canonically):
- `players2026_official.json` — new profile, `dataConfidence: "external"`, three sourceCitations.
- `externalPlayerRatings2026.json` — EA reference row (`eaPlayerId: "242914"`, sourceUrl, six stats).
- `manualPlayerOverrides2026.json` — `startingProbability: 78` with cited reason (confirmed starter).
- `players.json` — regenerated as the canonical mirror via `regenerate_legacy_players_json` (not hand-edited).
- `playerRatings2026_estimated.json` — regenerated via `scripts/rebuild_player_ratings_v2.py`.

`secondaryPositions` includes `CAM` — annotated (and cited in the profile) as his
**shadow-striker role in Moriyasu's 3-4-2-1**, not a fabricated natural position.

## Result (verified locally)
`GET /api/teams/JPN/likely-lineup` now returns Nakamura in the XI:

```
GK  Zion Suzuki 92 | CB Itakura 78 | CB Seko 75 | CB H.Ito 69
LB  Nagatomo 21 | RB Tomiyasu 63 | CDM Endo 72 | CM Tanaka 61
CAM Kamada 51 | CAM Keito Nakamura 78 | ST Ueda 20
```

He takes the left CAM (shadow-striker) slot alongside Kamada — matching his real
tournament role. His generated rating is **76**, sourced from EA (marked external,
never "official").

## Validation
- `scripts/rebuild_player_ratings_v2.py`: 672 ratings, 501 EA-sourced, 0 low-confidence, 0 missing-critical-data.
- Backend suite: **433 passed** (updated the two guardrail tests that hard-code the seed player count / legacy mirror).

## Honesty notes & scope boundary (data governance)
- Every value is sourced with a URL; nothing was fabricated or marked "official".
- **A full 48-team, slot-by-slot XI audit is deliberately NOT claimed.** Public
  lineup sources disagree on several of Japan's contested slots (e.g. wing-back
  vs. shadow-striker roles for Doan / J.Ito), and resolving all 48 squads that
  way would require fabricating contested picks — barred by the no-fabrication
  rule. This phase instead corrects the one **unambiguous, sourced** gap: a
  confirmed scorer-starter who was entirely absent from the roster. Further
  additions will follow the same evidence bar as sources become citable.
