from sqlalchemy import String, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "BRA_NEYMAR"
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    name: Mapped[str] = mapped_column(String)
    name_ja: Mapped[str | None] = mapped_column(String, nullable=True)  # katakana, e.g. "ネイマール"
    age: Mapped[int] = mapped_column(Integer)
    primary_position: Mapped[str] = mapped_column(String)
    secondary_positions: Mapped[list[str]] = mapped_column(JSON, default=list)
    overall: Mapped[int] = mapped_column(Integer)
    attributes: Mapped[dict] = mapped_column(JSON)
    stamina_max: Mapped[int] = mapped_column(Integer, default=100)
    source_notes: Mapped[str | None] = mapped_column(String, nullable=True)

    team: Mapped["Team"] = relationship(back_populates="players")
