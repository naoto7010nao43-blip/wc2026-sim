"""Converts a v2 PlayerRatingV2 back into the original 6+2-attribute shape
(pace/shooting/passing/dribbling/defending/physical + gk_reflexes/
gk_handling) that app/engine/* and app/rating/formulas.compute_overall
expect -- so the live micro-simulator keeps running completely unmodified
on top of the new rating pipeline.

Exact (not approximate) for defense/passing/dribbling/physical/gk_*,
since player_rating_model.py derives those v2 fields as direct copies of
the legacy base values. shooting and pace are inverted from finishing and
speed respectively, using the same linear weights player_rating_model.py
used going forward, so round-tripping introduces no meaningful drift.
"""

from app.rating_v2.normalization import clamp
from app.rating_v2.types import PlayerRatingV2


def derive_legacy_attributes(rating: PlayerRatingV2) -> dict:
    is_gk = rating.goalkeeper_reflexes is not None

    physical = rating.physical
    defending = rating.defense
    passing = rating.passing
    dribbling = rating.dribbling

    # finishing = 0.75*shooting + 0.25*dribbling  =>  invert for shooting.
    shooting = clamp((rating.finishing - 0.25 * dribbling) / 0.75)
    # speed = 0.75*pace + 0.25*physical  =>  invert for pace.
    pace = clamp((rating.speed - 0.25 * physical) / 0.75)

    attributes = {
        "pace": pace,
        "shooting": shooting,
        "passing": passing,
        "dribbling": dribbling,
        "defending": defending,
        "physical": physical,
        "gk_reflexes": rating.goalkeeper_reflexes if is_gk else None,
        "gk_handling": rating.goalkeeper_handling if is_gk else None,
    }
    return attributes


def v2_skill_attributes(rating: PlayerRatingV2) -> dict:
    """The finer-grained v2 attributes (beyond the 6+2 legacy set) that
    app/prediction/ratings.py reads for its team-strength signals. Merged
    alongside derive_legacy_attributes()'s output into Player.attributes
    so the micro-simulator engine and the Poisson prediction model can
    both read from the same JSON column without either depending on the
    other's attribute ontology."""
    return {
        "attack": rating.attack,
        "finishing": rating.finishing,
        "shotPower": rating.shot_power,
        "chanceCreation": rating.chance_creation,
        "ballCarrying": rating.ball_carrying,
        "crossing": rating.crossing,
        "setPiece": rating.set_piece,
        "defense": rating.defense,
        "tackling": rating.tackling,
        "interception": rating.interception,
        "aerialDefense": rating.aerial_defense,
        "speed": rating.speed,
        "acceleration": rating.acceleration,
        "stamina": rating.stamina,
        "strength": rating.strength,
        "mentality": rating.mentality,
        "composure": rating.composure,
        "workRate": rating.work_rate,
        "pressing": rating.pressing,
        "decisionMaking": rating.decision_making,
        "positioning": rating.positioning,
        "goalkeeperHandling": rating.goalkeeper_handling,
        "goalkeeperReflexes": rating.goalkeeper_reflexes,
        "goalkeeperDistribution": rating.goalkeeper_distribution,
        "currentForm": rating.current_form,
        "availability": rating.availability,
        "startingProbability": rating.starting_probability,
    }


def rating_trust_metadata(rating: PlayerRatingV2) -> dict:
    """Confidence/provenance metadata (not a gameplay attribute) merged
    into Player.attributes alongside the skill values above, so the API
    can explain *why* a rating looks the way it does -- see spec 006."""
    return {
        "dataConfidence": rating.data_confidence,
        "uncertainty": rating.uncertainty,
        "sourceBreakdown": {
            "officialRoster": rating.source_breakdown.official_roster,
            "marketValueUsed": rating.source_breakdown.market_value_used,
            "clubMinutesUsed": rating.source_breakdown.club_minutes_used,
            "nationalTeamMinutesUsed": rating.source_breakdown.national_team_minutes_used,
            "injuryDataUsed": rating.source_breakdown.injury_data_used,
            "manualOverrideUsed": rating.source_breakdown.manual_override_used,
            "externalReferenceUsed": rating.source_breakdown.external_reference_used,
            "calibrationApplied": rating.source_breakdown.calibration_applied,
        },
        "lowConfidenceAttributes": rating.low_confidence_attributes,
        "lastUpdated": rating.last_updated,
    }
