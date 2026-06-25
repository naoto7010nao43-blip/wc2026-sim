# Player Rating Accuracy: EA FC 26 External-Reference Injection

**Date:** 2026-06-26
**Author:** Claude Code (autonomous)
**Trigger:** User reported player abilities are poorly reflected on the site and accuracy is questionable; asked Claude to define the criteria, investigate EA Sports FC / sofifa as data sources, and judge which values to apply.

## Problem diagnosis (root cause)

The v2 player ratings in `playerRatings2026_estimated.json` are produced *from scratch*
by `app/rating_v2/player_rating_model.py::compute_player_rating_v2`, which runs a
per-90 career-stat + market-value-percentile + age pipeline (`app/rating/formulas.py`
Stage A/B/C -> `compute_overall`). That pipeline **severely compresses the top of the
scale**. Before this change, across all 669 players:

- pool mean overall **54.4**, max **82**, and **zero** players rated >= 85.
- Marquee players sat far below their real level: Bellingham 65, Salah 66, McTominay 57,
  Rodri 63, Odegaard 67, Haaland 76. EA FC 26 rates these same players 85-91.

So the site was faithfully showing numbers that the estimator had quietly crushed.

## Data source decision

- **EA SPORTS FC 26** (https://www.ea.com/games/ea-sports-fc/ratings) — usable. Per-player
  pages are publicly fetchable; each exposes an overall (OVR) plus the six face stats
  (PAC/SHO/PAS/DRI/DEF/PHY) that map **1:1** onto this engine's six legacy base attributes.
  GK cards expose DIV/HAN/KIC/REF/SPD/POS instead. Player page URL pattern:
  `.../player-ratings/{slug}/{eaPlayerId}` where `eaPlayerId` == the sofifa id.
- **sofifa** (https://sofifa.com) — **blocked** (HTTP 403 to automated fetches). Not used.

EA is treated as a citable Tier-A reference: every injected value records its
`sourceUrl`, and ratings sourced this way are marked `dataConfidence="external"`
(NOT `"official"` — these are a game publisher's ratings, not federation data).

## Mechanism

A new seed file `data/seed/externalPlayerRatings2026.json` holds, per player:
`playerId`, `source`, `sourceUrl`, `eaPlayerId`, `position`, `observedDate`, `overall`,
and the six face stats (or GK variants `gkReflexes`/`gkHandling`/`gkSpeed`).

`compute_player_rating_v2` gained an `external_reference` parameter. When present:

- the EA overall + six face stats are taken **verbatim** as the authoritative base/overall,
  bypassing the compressed Stage A/B/C estimation and `compute_overall`;
- **every derived sub-attribute is still produced by the existing formulas** off that base,
  so a sourced player remains internally consistent with the rest of the pool and needs no
  special-casing downstream (legacy bridge, micro-simulator, Poisson model);
- `dataConfidence` becomes `"external"` (or `"mixed"` if a manual override also applies),
  `uncertainty` drops to a small source/observation slack (0.05), and a new honest flag
  `RatingSourceBreakdown.external_reference_used` records it.

`rebuild_player_ratings_v2.py` loads the file and passes per-player references; the diff
report now lists `externallySourced` playerIds.

## Pilot result (11 marquee players, all values fetched live from EA on 2026-06-26)

| Player | est. before | EA / now |
|---|---|---|
| Mbappe | 82 | 91 |
| Salah | 66 | 91 |
| Haaland | 76 | 90 |
| Bellingham | 65 | 90 |
| Rodri | 63 | 90 |
| Kane | 70 | 89 |
| Vinicius Jr | 77 | 89 |
| Lamine Yamal | 75 | 89 |
| Caicedo | 62 | 87 |
| Odegaard | 67 | 87 |
| McTominay | 57 | 85 |

Pool max 82 -> 91; players >= 85: 0 -> 11. Engine-facing legacy attributes (via
`derive_legacy_attributes`) match EA on the headline figures; composite defensive stats
for attackers blend slightly by design (a winger's defensive contribution is not purely
his DEF face stat).

## Verification

- `pytest -q`: **406 passed** (was 401; +5 new tests covering the external path, incl. GK
  and external+override interaction).
- `audit_text_encoding.py`: passed.
- Manager-rating / metadata diffs are pre-existing `lastUpdated` timestamp churn only.

## Governance notes

- No values were fabricated or guessed. Two EA URLs initially 404'd on guessed slugs
  (`vinicius-junior`, `martin-odegaard`); the correct slugs (`vini-jr`, `martin-degaard`)
  were resolved by web search before fetching, rather than inventing numbers.
- EA ratings are marked `external`, never `official`.

## Next step / scaling decision (open)

This pilot covers 11 of 669 players. Extending to the full pool means resolving an EA
slug+id and fetching face stats for each remaining player (~658). That is a large,
billable data-collection effort whose approach (full multi-agent workflow vs. prioritized
batches by squad importance vs. incremental) is the user's call — see the conversation.
The infrastructure is complete and idempotent: scaling is purely a matter of adding rows
to `externalPlayerRatings2026.json` and re-running the rebuild.
