# Player Rating Methodology

This project computes a 6-attribute player rating (pace, shooting, passing,
dribbling, defending, physical — plus GK-specific reflexes/handling) for
each player. **It does not copy, scrape, or reproduce any commercial video
game's proprietary player rating database (e.g. EA Sports FC).** Those
games' rating systems are independently developed, copyrighted compilations
and are not used as a data source.

Instead, ratings are derived through an original three-stage pipeline from
public information:

## Stage A — Statistical base score

For each attribute, a transparent formula (see `backend/app/rating/formulas.py`)
converts a player's public per-90 career statistics (goals, assists, key
passes, successful dribbles, tackles, interceptions, aerial duel win %, pass
completion %) into a 0-99 raw score. Formulas are position-aware (e.g.
`defending` weighs tackles/interceptions/aerial duels; `shooting` weighs
goals per 90).

## Stage B — Market value correction

A player's transfer market value (e.g. as reported by public sources like
Transfermarkt) is converted into a percentile rank within their position
group, and applied as a bounded ±10 point shift across all attributes
(widened from an initial ±4 — see "Tuning history" below). This captures
market consensus (big-game pedigree, perceived ceiling, injury risk, and
critically, the strength of the league a player actually plays in) that
raw per-90 stats alone miss, without letting it dominate the score.

## Stage C — Qualitative scouting adjustment (human-curated, capped)

A small, explicit, human-entered adjustment of at most ±6 points per
attribute (widened from an initial ±3), recorded per player in
`data/seed/players.json` under `qualitative_adjustments`. This is the only
place general footballing judgment (the kind of intuition that might also
inform a video game's ratings) enters the pipeline — and only as a bounded
nudge on top of the statistically-derived base, never as the source of the
number itself.

For the full 48-team dataset, published headline ratings from EA Sports FC
26 and/or eFootball 2026 were allowed as one *input signal* researchers
could consider when setting a player's Stage C nudge (recorded in that
player's `source_citations`, e.g. "EA FC 26 rating ~82 used as Stage C
calibration signal"). This is a calibration reference only: the ±6 cap
still applies on top of the independently-computed Stage A/B score, so a
game's rating can influence the adjustment but can never become the
attribute value itself.

### Tuning history

Initial caps of ±4 (Stage B) / ±3 (Stage C) were too small relative to
Stage A's raw per-90 formulas, which have no notion of league/competition
strength — a domestic-league regular in a footballing minnow can post
per-90 stats in the same range as a Champions-League-level player, so the
two corrective signals couldn't fully close a real quality gap. Raised to
±10 / ±6 after observing unrealistic group-stage upsets in full-tournament
runs. This keeps the non-derivation principle intact (market value and
human qualitative judgment are legitimate independent signals, not a copy
of any game's database) while giving them enough room to actually correct
Stage A's blind spot.

## Manager tactical profiles

Each team also has a `tactical_profile` (`press_intensity`,
`possession_style`, `defensive_line_height`, each 0-99, plus the
manager's name) based on that manager's real-world tactical reputation and
the team's actual playing style. These feed directly into the simulation
engine's action-selection and duel formulas (see
`backend/app/engine/actions.py`) rather than into the player rating
pipeline above.

## Overall rating

The single "overall" number is a position-weighted average of the 6 final
attributes (weights differ by position group: GK/DEF/MID/FWD — see
`OVERALL_WEIGHTS` in `formulas.py`).

## Re-deriving ratings

Because raw research data lives in `data/seed/*.json` and the pipeline is
pure functions, re-running `scripts/seed_db.py` after editing the source
JSON (e.g. updated season stats, revised qualitative notes) regenerates all
ratings deterministically — there is no manual rating entry to keep in
sync.

## Sources

Per-player `source_citations` fields record where each player's input
stats/market value were sourced from (e.g. Transfermarkt profile pages,
FBref season stats), for auditability.

## Round of 32 bracket: a noted simplification

The 48-team knockout bracket's fixed cross-pairs and the 8 third-place
candidate pools (see `backend/app/engine/bracket.py`) are taken from
FIFA's official Round of 32 bracket diagram. The exact 495-row lookup
table ("Annex C") that pins down precisely which third-placed team fills
which slot for every one of the 495 possible 8-of-12 group combinations
was not reproduced verbatim — the only available source images were too
small to transcribe reliably. Instead, the actual assignment is computed
by a deterministic constraint-satisfaction search that always respects
every slot's confirmed candidate pool. This can never produce an
impossible pairing, but for a given combination of qualifying groups it
is not guaranteed to match FIFA's literal published pick.
