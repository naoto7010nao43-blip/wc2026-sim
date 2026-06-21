from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.team import Team
from app.schemas.standings import StandingsRow


def compute_standings(db: Session, group_id: str) -> list[StandingsRow]:
    matches = db.scalars(
        select(Match).where(Match.group_id == group_id, Match.status == "completed")
    ).all()

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

    team_names = {
        t.id: t.name
        for t in db.scalars(select(Team).where(Team.id.in_(team_ids))).all()
    }

    rows = []
    for tid, s in stats.items():
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
        ))

    rows.sort(key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, r.team_id))
    return rows
