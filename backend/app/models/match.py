from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    group_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # "group" | "R32" | "R16" | "QF" | "SF" | "THIRD_PLACE" | "FINAL"
    round: Mapped[str] = mapped_column(String, default="group")
    bracket_slot: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. "R32_1"
    home_team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    home_formation: Mapped[str] = mapped_column(String)
    away_formation: Mapped[str] = mapped_column(String)
    # Starting XI positions: list of {player_id, name, slot_position, x, y}.
    home_lineup: Mapped[list | None] = mapped_column(JSON, nullable=True)
    away_lineup: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # player_id -> display name, for every player who appeared (starters +
    # substitutes) -- used for post-match rating/MOM name lookup.
    home_roster: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    away_roster: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    home_score: Mapped[int] = mapped_column(Integer, default=0)
    away_score: Mapped[int] = mapped_column(Integer, default=0)
    went_to_penalties: Mapped[bool] = mapped_column(default=False)
    penalty_home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    penalty_away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="scheduled")
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    played_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    is_real: Mapped[bool] = mapped_column(default=False)
    data_source: Mapped[str | None] = mapped_column(String, nullable=True)
    home_possession_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_possession_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MatchEvent(Base):
    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"))
    minute: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String)
    team_id: Mapped[str] = mapped_column(String)
    player_id: Mapped[str | None] = mapped_column(String, nullable=True)
    secondary_player_id: Mapped[str | None] = mapped_column(String, nullable=True)
    x: Mapped[float | None] = mapped_column(Float, nullable=True)
    y: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(String)
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
