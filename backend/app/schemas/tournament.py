from pydantic import BaseModel

from app.schemas.match import MatchSummary
from app.schemas.standings import StandingsRow

ROUND_NAMES = ["group", "R32", "R16", "QF", "SF", "THIRD_PLACE", "FINAL"]


class RunTournamentRequest(BaseModel):
    seed: int | None = None


class TournamentResult(BaseModel):
    champion_team_id: str | None
    qualifying_third_groups: list[str] | None = None
    matches: dict[str, list[MatchSummary]]
    group_standings: dict[str, list[StandingsRow]]
