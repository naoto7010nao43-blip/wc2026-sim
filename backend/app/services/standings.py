from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.team import Team
from app.schemas.standings import StandingsRow
from app.services.tiebreakers import TeamAggregate, break_ties, compute_conduct_scores


def calculate_standings(
    matches: list[Match],
    team_names: dict[str, str],
    fifa_ranks: dict[str, int | None],
) -> list[StandingsRow]:
    """Pure: computes group standings (played/won/drawn/lost/gf/ga/points)
    plus FIFA's official tiebreaker cascade (see tiebreakers.py), without
    touching the database. `matches` must include every completed match in
    the group; `team_names`/`fifa_ranks` must have an entry for every team
    that appears in `matches`."""
    team_ids: set[str] = set()
    for m in matches:
        team_ids.add(m.home_team_id)
        team_ids.add(m.away_team_id)

    stats = {
        tid: {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0}
        for tid in team_ids
    }

    for m in matches:
        h, a = stats[m.home_team_id], stats[m.away_team_id]
        h["played"] += 1
        a["played"] += 1
        h["gf"] += m.home_score
        h["ga"] += m.away_score
        a["gf"] += m.away_score
        a["ga"] += m.home_score

        if m.home_score > m.away_score:
            h["won"] += 1
            a["lost"] += 1
        elif m.home_score < m.away_score:
            a["won"] += 1
            h["lost"] += 1
        else:
            h["drawn"] += 1
            a["drawn"] += 1

    aggregates = {
        tid: TeamAggregate(tid, s["won"] * 3 + s["drawn"], s["gf"] - s["ga"], s["gf"])
        for tid, s in stats.items()
    }
    conduct_scores = compute_conduct_scores(matches)
    ordered = break_ties(sorted(team_ids), matches, aggregates, conduct_scores, fifa_ranks)

    rows = []
    for tid, reason in ordered:
        s = stats[tid]
        points = s["won"] * 3 + s["drawn"]
        rows.append(StandingsRow(
            team_id=tid,
            team_name=team_names.get(tid, tid),
            played=s["played"],
            won=s["won"],
            drawn=s["drawn"],
            lost=s["lost"],
            goals_for=s["gf"],
            goals_against=s["ga"],
            goal_diff=s["gf"] - s["ga"],
            points=points,
            conduct_score=conduct_scores.get(tid, 0),
            fifa_rank=fifa_ranks.get(tid),
            tiebreak_reason=reason,
        ))
    return rows


def compute_standings(db: Session, group_id: str) -> list[StandingsRow]:
    matches = db.scalars(
        select(Match).where(Match.group_id == group_id, Match.status == "completed")
    ).all()

    team_ids: set[str] = set()
    for m in matches:
        team_ids.add(m.home_team_id)
        team_ids.add(m.away_team_id)

    teams = db.scalars(select(Team).where(Team.id.in_(team_ids))).all()
    team_names = {t.id: t.name for t in teams}
    fifa_ranks = {t.id: t.fifa_rank for t in teams}

    return calculate_standings(list(matches), team_names, fifa_ranks)
