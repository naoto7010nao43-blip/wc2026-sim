"""Data types for the v2 player/manager rating system.

Field names use snake_case in Python (project convention); the on-disk
JSON files (backend/data/seed/*2026_official.json,
*2026_estimated.json) use the camelCase names the user specified, with
translation happening at the JSON read/write boundary (see
migrate_to_player_data_v2.py / rebuild_player_ratings_v2.py).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

DataConfidence = Literal["official", "external", "estimated", "manual", "mixed", "missing"]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RatingSourceBreakdown:
    """Which real inputs actually fed a rating -- lets a consumer judge
    *why* a number looks the way it does, not just trust a single overall
    figure. Every flag here reflects what's genuinely available in this
    project's data today; national_team_minutes_used and
    injury_data_used are currently always False because that data simply
    doesn't exist yet (see project roadmap), not because it was ignored.
    """
    official_roster: bool = True
    market_value_used: bool = False
    club_minutes_used: bool = False
    national_team_minutes_used: bool = False
    injury_data_used: bool = False
    manual_override_used: bool = False
    external_reference_used: bool = False


@dataclass(frozen=True)
class PlayerRatingV2:
    player_id: str
    team_id: str
    overall: int
    position_overall: int

    attack: int
    finishing: int
    shot_power: int
    passing: int
    chance_creation: int
    dribbling: int
    ball_carrying: int
    crossing: int
    set_piece: int

    defense: int
    tackling: int
    interception: int
    aerial_defense: int

    physical: int
    speed: int
    acceleration: int
    stamina: int
    strength: int

    mentality: int
    composure: int
    work_rate: int
    pressing: int
    decision_making: int
    positioning: int

    goalkeeper_handling: int | None
    goalkeeper_reflexes: int | None
    goalkeeper_distribution: int | None

    current_form: int
    availability: int

    # 0-100: likelihood of starting the next match, estimated from this
    # player's club minutes/appearances/market value *relative to other
    # players in the same position group on the same team* (see
    # compute_starting_probabilities in player_rating_model.py). Not a
    # formation-slot assignment by itself -- see lineup_builder.py for that.
    starting_probability: int

    uncertainty: float  # 0 (well-supported) - 1 (almost entirely guessed)
    data_confidence: DataConfidence
    source_breakdown: RatingSourceBreakdown
    low_confidence_attributes: list[str]  # attribute names derived from weak/no real signal
    last_updated: str = field(default_factory=utcnow_iso)

    @classmethod
    def from_json_dict(cls, d: dict) -> "PlayerRatingV2":
        sb = d.get("sourceBreakdown", {})
        return cls(
            player_id=d["playerId"], team_id=d["teamId"], overall=d["overall"], position_overall=d["positionOverall"],
            attack=d["attack"], finishing=d["finishing"], shot_power=d["shotPower"], passing=d["passing"],
            chance_creation=d["chanceCreation"], dribbling=d["dribbling"], ball_carrying=d["ballCarrying"],
            crossing=d["crossing"], set_piece=d["setPiece"], defense=d["defense"], tackling=d["tackling"],
            interception=d["interception"], aerial_defense=d["aerialDefense"], physical=d["physical"],
            speed=d["speed"], acceleration=d["acceleration"], stamina=d["stamina"], strength=d["strength"],
            mentality=d["mentality"], composure=d["composure"], work_rate=d["workRate"], pressing=d["pressing"],
            decision_making=d["decisionMaking"], positioning=d["positioning"],
            goalkeeper_handling=d["goalkeeperHandling"], goalkeeper_reflexes=d["goalkeeperReflexes"],
            goalkeeper_distribution=d["goalkeeperDistribution"], current_form=d["currentForm"],
            availability=d["availability"], starting_probability=d.get("startingProbability", 50),
            uncertainty=d["uncertainty"], data_confidence=d["dataConfidence"],
            source_breakdown=RatingSourceBreakdown(
                official_roster=sb.get("officialRoster", True),
                market_value_used=sb.get("marketValueUsed", False),
                club_minutes_used=sb.get("clubMinutesUsed", False),
                national_team_minutes_used=sb.get("nationalTeamMinutesUsed", False),
                injury_data_used=sb.get("injuryDataUsed", False),
                manual_override_used=sb.get("manualOverrideUsed", False),
                external_reference_used=sb.get("externalReferenceUsed", False),
            ),
            low_confidence_attributes=d.get("lowConfidenceAttributes", []),
            last_updated=d.get("lastUpdated", utcnow_iso()),
        )

    def to_json_dict(self) -> dict:
        return {
            "playerId": self.player_id,
            "teamId": self.team_id,
            "overall": self.overall,
            "positionOverall": self.position_overall,
            "attack": self.attack,
            "finishing": self.finishing,
            "shotPower": self.shot_power,
            "passing": self.passing,
            "chanceCreation": self.chance_creation,
            "dribbling": self.dribbling,
            "ballCarrying": self.ball_carrying,
            "crossing": self.crossing,
            "setPiece": self.set_piece,
            "defense": self.defense,
            "tackling": self.tackling,
            "interception": self.interception,
            "aerialDefense": self.aerial_defense,
            "physical": self.physical,
            "speed": self.speed,
            "acceleration": self.acceleration,
            "stamina": self.stamina,
            "strength": self.strength,
            "mentality": self.mentality,
            "composure": self.composure,
            "workRate": self.work_rate,
            "pressing": self.pressing,
            "decisionMaking": self.decision_making,
            "positioning": self.positioning,
            "goalkeeperHandling": self.goalkeeper_handling,
            "goalkeeperReflexes": self.goalkeeper_reflexes,
            "goalkeeperDistribution": self.goalkeeper_distribution,
            "currentForm": self.current_form,
            "availability": self.availability,
            "startingProbability": self.starting_probability,
            "uncertainty": round(self.uncertainty, 3),
            "dataConfidence": self.data_confidence,
            "sourceBreakdown": {
                "officialRoster": self.source_breakdown.official_roster,
                "marketValueUsed": self.source_breakdown.market_value_used,
                "clubMinutesUsed": self.source_breakdown.club_minutes_used,
                "nationalTeamMinutesUsed": self.source_breakdown.national_team_minutes_used,
                "injuryDataUsed": self.source_breakdown.injury_data_used,
                "manualOverrideUsed": self.source_breakdown.manual_override_used,
                "externalReferenceUsed": self.source_breakdown.external_reference_used,
            },
            "lowConfidenceAttributes": self.low_confidence_attributes,
            "lastUpdated": self.last_updated,
        }


@dataclass(frozen=True)
class ManagerRatingV2:
    manager_id: str
    team_code: str
    press_intensity: int
    possession_style: int
    defensive_line_height: int
    data_confidence: DataConfidence
    last_updated: str = field(default_factory=utcnow_iso)

    def to_json_dict(self) -> dict:
        return {
            "managerId": self.manager_id,
            "teamCode": self.team_code,
            "pressIntensity": self.press_intensity,
            "possessionStyle": self.possession_style,
            "defensiveLineHeight": self.defensive_line_height,
            "dataConfidence": self.data_confidence,
            "lastUpdated": self.last_updated,
        }
