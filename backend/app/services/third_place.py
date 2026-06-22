"""Ranks the 12 third-placed group teams to determine which 8 advance to
the Round of 32, using FIFA's official third-place ranking cascade: points
-> overall goal difference -> overall goals scored -> team conduct ->
FIFA World Ranking. Unlike the in-group standings, head-to-head does not
apply here since these teams never played each other.
"""

from dataclasses import dataclass

from app.schemas.standings import StandingsRow
from app.services.tiebreakers import TeamAggregate, break_third_place_ties


@dataclass(frozen=True)
class ThirdPlaceStanding:
    group_id: str
    team_id: str
    team_name: str
    points: int
    goal_diff: int
    goals_for: int
    tiebreak_reason: str
    qualified: bool


def rank_third_place_teams(rows_by_group: dict[str, StandingsRow]) -> list[ThirdPlaceStanding]:
    """`rows_by_group` maps group letter -> that group's third-placed
    team's StandingsRow. Returns all 12 groups ranked best-to-worst, with
    the top 8 flagged qualified=True."""
    group_ids = sorted(rows_by_group.keys())
    aggregates = {
        gid: TeamAggregate(
            gid,
            rows_by_group[gid].points,
            rows_by_group[gid].goal_diff,
            rows_by_group[gid].goals_for,
        )
        for gid in group_ids
    }
    conduct_scores = {gid: rows_by_group[gid].conduct_score for gid in group_ids}
    fifa_ranks = {gid: rows_by_group[gid].fifa_rank for gid in group_ids}

    ordered = break_third_place_ties(group_ids, aggregates, conduct_scores, fifa_ranks)

    standings = []
    for rank, (gid, reason) in enumerate(ordered):
        row = rows_by_group[gid]
        standings.append(ThirdPlaceStanding(
            group_id=gid,
            team_id=row.team_id,
            team_name=row.team_name,
            points=row.points,
            goal_diff=row.goal_diff,
            goals_for=row.goals_for,
            tiebreak_reason=reason,
            qualified=rank < 8,
        ))
    return standings
