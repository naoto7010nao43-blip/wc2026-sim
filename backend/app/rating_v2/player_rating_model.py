"""v2 player rating model: expands the existing, already-tuned Stage A/B/C
6+2-attribute pipeline (app/rating/formulas.py) into the richer ~25-
attribute set the user specified, using only inputs that genuinely exist
in this project's data (career_stats, market_value_eur, age, stamina_max,
qualitative_adjustments). No new attribute is invented from data we don't
have -- attributes with no real statistical backing (mentality, composure,
workRate, pressing, decisionMaking, positioning, setPiece, crossing,
goalkeeperDistribution) are derived from coarse, documented heuristics and
always listed in `low_confidence_attributes`, never presented as
equivalent in reliability to the stats-backed ones.

Reuses app.rating.formulas directly (StageAInputs, stage_a_raw_attributes,
stage_a_gk_attributes, stage_b_market_modifier, apply_pipeline,
compute_overall, POSITION_GROUPS) rather than re-deriving per-90
normalization from scratch -- that pipeline is already calibrated and
covered by existing tests.
"""

from app.rating.formulas import (
    POSITION_GROUPS,
    StageAInputs,
    apply_pipeline,
    compute_overall,
    percentile_rank,
    stage_a_gk_attributes,
    stage_a_raw_attributes,
)
from app.rating_v2.normalization import age_curve_score, clamp, market_value_score
from app.rating_v2.types import PlayerRatingV2, RatingSourceBreakdown

# Always heuristically derived (no direct per-90/market signal behind
# them) regardless of how complete the player's other data is.
LOW_CONFIDENCE_ATTRIBUTES = [
    "mentality", "composure", "workRate", "pressing", "decisionMaking",
    "positioning", "setPiece", "crossing", "goalkeeperDistribution", "currentForm",
]

# A fixed floor reflecting data we systematically don't have *at all* yet
# for any player (caps, recent national-team minutes, club name/league,
# injury status) -- see project roadmap. Not a per-player penalty; a
# baseline honesty signal that the whole rating set has this gap.
BASELINE_UNCERTAINTY_NO_NATIONAL_TEAM_DATA = 0.20

GK_OUTFIELD_PLACEHOLDER_BASE = {
    "pace": 50, "shooting": 15, "passing": 55, "dribbling": 35, "defending": 40, "physical": 60,
}

# When an EA Sports FC 26 (or comparably sourced) reference rating is supplied
# for a player, we use its published overall + six face stats verbatim as the
# authoritative base instead of the from-scratch per-90 estimation, which was
# found to compress the top of the scale badly (e.g. Haaland estimated 76 vs
# EA's 90). The six EA face stats map 1:1 onto this engine's six legacy base
# attributes; every richer v2 sub-attribute is still derived from them by the
# SAME formulas the estimated path uses, so an external player stays internally
# consistent and the micro-simulator/Poisson model need no special-casing.
EXTERNAL_REFERENCE_UNCERTAINTY = 0.05


def _external_base_and_overall(ext: dict, position_group: str) -> tuple[dict, int]:
    overall = int(ext["overall"])
    if position_group == "GK":
        # EA goalkeeper cards expose DIV/HAN/KIC/REF/SPD/POS rather than the
        # outfield six. Only reflexes/handling drive this engine's GK model;
        # the outfield placeholder base is kept (optionally letting EA's GK
        # speed inform `pace`) so derived outfield-flavoured attributes stay
        # sane for a keeper.
        base = dict(GK_OUTFIELD_PLACEHOLDER_BASE)
        base["gk_reflexes"] = int(ext.get("gkReflexes", overall))
        base["gk_handling"] = int(ext.get("gkHandling", overall))
        if ext.get("gkSpeed") is not None:
            base["pace"] = int(ext["gkSpeed"])
        return base, overall
    base = {
        "pace": int(ext["pace"]),
        "shooting": int(ext["shooting"]),
        "passing": int(ext["passing"]),
        "dribbling": int(ext["dribbling"]),
        "defending": int(ext["defending"]),
        "physical": int(ext["physical"]),
        "gk_reflexes": None,
        "gk_handling": None,
    }
    return base, overall


def _stage_a_inputs(player: dict) -> tuple[StageAInputs, bool]:
    stats = player.get("careerStats") or {}
    appearances = max(stats.get("appearances", 0), 0)
    known = appearances > 0
    appearances_safe = max(appearances, 1)
    minutes = stats.get("minutesPlayed", appearances_safe * 70)
    position_group = POSITION_GROUPS.get(player["primaryPosition"], "MID")
    return StageAInputs(
        position_group=position_group,
        age=player.get("age") or 27,
        goals_per90=stats.get("goals", 0) / appearances_safe,
        assists_per90=stats.get("assists", 0) / appearances_safe,
        key_passes_per90=stats.get("keyPassesPer90", 0.0),
        successful_dribbles_per90=stats.get("successfulDribblesPer90", 0.0),
        tackles_per90=stats.get("tacklesPer90", 0.0),
        interceptions_per90=stats.get("interceptionsPer90", 0.0),
        aerial_duels_won_pct=stats.get("aerialDuelsWonPct", 40.0),
        pass_completion_pct=stats.get("passCompletionPct", 78.0),
        minutes_per_appearance=minutes / appearances_safe,
        save_pct=stats.get("savePct"),
        goals_conceded_per90=stats.get("goalsConcededPer90"),
    ), known


def compute_player_rating_v2(
    player: dict,
    peer_market_values_eur: list[float],
    manual_override: dict | None = None,
    external_reference: dict | None = None,
) -> PlayerRatingV2:
    """`player` is one entry from players2026_official.json (camelCase
    keys). `peer_market_values_eur` should be every same-position-group
    teammate-or-opponent's marketValueEur across the full player pool, for
    percentile normalization (mirrors the existing Stage B percentile
    approach).

    `external_reference`, when given, is a sourced EA-FC-26-style rating
    (overall + six face stats, see _external_base_and_overall); it replaces
    the estimated base/overall for this player while every derived
    sub-attribute is still produced by the formulas below, so a sourced
    player remains internally consistent with the rest of the pool."""
    position_group = POSITION_GROUPS.get(player["primaryPosition"], "MID")
    inp, career_known = _stage_a_inputs(player)

    market_eur = player.get("marketValueEur")
    market_score, market_known = market_value_score(market_eur, peer_market_values_eur)
    age_score, age_known = age_curve_score(player.get("age"))

    is_external = external_reference is not None
    if is_external:
        base, overall = _external_base_and_overall(external_reference, position_group)
    elif position_group == "GK":
        stage_a = stage_a_gk_attributes(inp)
        gk_final = apply_pipeline(stage_a, market_score / 100.0, player.get("qualitativeAdjustments", {}), inp.age)
        base = {**GK_OUTFIELD_PLACEHOLDER_BASE, **gk_final}
        overall = compute_overall(base, player["primaryPosition"])
    else:
        stage_a = stage_a_raw_attributes(inp)
        final = apply_pipeline(stage_a, market_score / 100.0, player.get("qualitativeAdjustments", {}), inp.age)
        base = {**final, "gk_reflexes": None, "gk_handling": None}
        overall = compute_overall(base, player["primaryPosition"])

    stamina_max = player.get("staminaMax") or 85

    pace, shooting, passing, dribbling, defending, physical = (
        base["pace"], base["shooting"], base["passing"], base["dribbling"], base["defending"], base["physical"],
    )
    is_gk = position_group == "GK"
    gk_reflexes, gk_handling = base.get("gk_reflexes"), base.get("gk_handling")

    rating = PlayerRatingV2(
        player_id=player["playerId"],
        team_id=player["teamId"],
        overall=overall,
        position_overall=overall,  # no formation/role context yet -- see roadmap (startingProbability/lineupBuilder)
        attack=clamp(0.5 * shooting + 0.3 * dribbling + 0.2 * passing),
        finishing=clamp(0.75 * shooting + 0.25 * dribbling),
        shot_power=clamp(0.6 * shooting + 0.4 * physical),
        passing=clamp(passing),
        chance_creation=clamp(0.55 * passing + 0.30 * dribbling + 0.15 * shooting),
        dribbling=clamp(dribbling),
        ball_carrying=clamp(0.55 * dribbling + 0.30 * pace + 0.15 * physical),
        crossing=clamp(0.45 * passing + 0.30 * dribbling + 0.25 * pace),
        set_piece=clamp(0.55 * shooting + 0.30 * passing + 0.15 * physical),
        defense=clamp(defending),
        tackling=clamp(0.7 * defending + 0.3 * physical),
        interception=clamp(0.65 * defending + 0.20 * passing + 0.15 * pace),
        aerial_defense=clamp(0.55 * defending + 0.45 * physical),
        physical=clamp(physical),
        speed=clamp(0.75 * pace + 0.25 * physical),
        acceleration=clamp(0.85 * pace + 0.15 * dribbling),
        stamina=clamp(stamina_max, lo=35, hi=99),
        strength=clamp(0.8 * physical + 0.2 * defending),
        mentality=clamp(0.5 * age_score + 0.5 * overall),
        composure=clamp(0.4 * age_score + 0.3 * market_score + 0.3 * overall),
        work_rate=clamp(0.5 * physical + 0.3 * pace + 0.2 * defending),
        pressing=clamp(0.4 * defending + 0.3 * physical + 0.3 * pace),
        decision_making=clamp(0.5 * passing + 0.3 * age_score + 0.2 * overall),
        positioning=clamp(0.4 * defending + 0.3 * passing + 0.3 * age_score),
        goalkeeper_handling=clamp(gk_handling) if is_gk and gk_handling is not None else None,
        goalkeeper_reflexes=clamp(gk_reflexes) if is_gk and gk_reflexes is not None else None,
        goalkeeper_distribution=(
            clamp(0.6 * gk_handling + 0.4 * passing) if is_gk and gk_handling is not None else None
        ),
        current_form=overall,  # no recent-form signal distinct from season aggregates yet -- see roadmap
        availability=100,  # no injury/suspension data wired in this pass -- see roadmap
        starting_probability=50,  # placeholder -- needs team-roster context, set by compute_starting_probabilities()
        uncertainty=0.0,  # placeholder, set below
        data_confidence="estimated",  # placeholder, set below
        source_breakdown=RatingSourceBreakdown(
            official_roster=True,
            market_value_used=market_known,
            club_minutes_used=career_known,
            national_team_minutes_used=False,
            injury_data_used=False,
            manual_override_used=manual_override is not None,
            external_reference_used=is_external,
        ),
        low_confidence_attributes=list(LOW_CONFIDENCE_ATTRIBUTES),
    )

    if is_external:
        # A sourced EA-FC-26 reference replaces the estimated base/overall,
        # so the headline values no longer depend on the missing-data
        # penalties below; the only residual uncertainty is the small
        # source/observation slack. Sub-attributes are still derived, but
        # they hang off authoritative face stats, so this stays low.
        uncertainty = EXTERNAL_REFERENCE_UNCERTAINTY
        data_confidence = "external"
        if manual_override:
            uncertainty *= 0.5
            data_confidence = "mixed"
    else:
        uncertainty = BASELINE_UNCERTAINTY_NO_NATIONAL_TEAM_DATA
        if not market_known:
            uncertainty += 0.15
        if not age_known:
            uncertainty += 0.10
        if not career_known:
            uncertainty += 0.15

        if manual_override:
            uncertainty *= 0.5
            data_confidence = "mixed"
        elif not market_known and not career_known:
            data_confidence = "missing"
        else:
            data_confidence = "estimated"

    uncertainty = max(0.0, min(1.0, uncertainty))

    # dataclasses are frozen (immutable) -- rebuild with the final fields
    # rather than mutate, and apply manual overrides verbatim on top.
    final_fields = {
        k: getattr(rating, k) for k in rating.__dataclass_fields__ if k not in ("uncertainty", "data_confidence")
    }
    final_fields["uncertainty"] = uncertainty
    final_fields["data_confidence"] = data_confidence
    if manual_override:
        for key, value in manual_override.get("overrides", {}).items():
            snake_key = _camel_to_snake(key)
            if snake_key in final_fields:
                final_fields[snake_key] = value
    return PlayerRatingV2(**final_fields)


def compute_starting_probabilities(
    players: list[dict], ratings_by_id: dict[str, PlayerRatingV2]
) -> dict[str, int]:
    """0-100 per player: how likely they are to start, relative only to
    *their own team's other players in the same coarse position group*
    (GK/DEF/MID/FWD) -- not a league-wide or formation-slot estimate.
    Blends three signals already present in the data, each compared
    within that team+group cohort: club minutes (heaviest weight --
    actual playing time is the strongest real signal of being a starter),
    market value, and the computed overall rating. A cohort of size 1
    (e.g. a team's only specialist at a position) gets the neutral 50
    every percentile_rank gives a singleton population, rather than a
    misleadingly confident 100.
    """
    cohorts: dict[tuple[str, str], list[dict]] = {}
    for p in players:
        group = POSITION_GROUPS.get(p["primaryPosition"], "MID")
        cohorts.setdefault((p["teamId"], group), []).append(p)

    result: dict[str, int] = {}
    for cohort_players in cohorts.values():
        minutes_pool = [
            (p.get("careerStats") or {}).get("minutesPlayed", 0.0) for p in cohort_players
        ]
        market_pool = [p.get("marketValueEur") or 0.0 for p in cohort_players]
        overall_pool = [ratings_by_id[p["playerId"]].overall for p in cohort_players]

        for p in cohort_players:
            minutes = (p.get("careerStats") or {}).get("minutesPlayed", 0.0)
            market = p.get("marketValueEur") or 0.0
            overall = ratings_by_id[p["playerId"]].overall

            score = (
                0.45 * percentile_rank(minutes, minutes_pool)
                + 0.30 * percentile_rank(market, market_pool)
                + 0.25 * percentile_rank(overall, overall_pool)
            )
            result[p["playerId"]] = int(round(max(1.0, min(99.0, score * 100.0))))
    return result


def _camel_to_snake(name: str) -> str:
    out = []
    for ch in name:
        if ch.isupper():
            out.append("_")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)
