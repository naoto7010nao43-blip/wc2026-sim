from pydantic import BaseModel


class StandingsRow(BaseModel):
    team_id: str
    team_name: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    conduct_score: int
    fifa_rank: int | None
    tiebreak_reason: str
