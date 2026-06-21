from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "BRA"
    name: Mapped[str] = mapped_column(String)
    confederation: Mapped[str] = mapped_column(String)
    fifa_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_formation: Mapped[str] = mapped_column(String)
    group_id: Mapped[str | None] = mapped_column(String, nullable=True)  # "A".."L"
    # {"manager_name": str, "press_intensity": 0-100, "possession_style": 0-100, "defensive_line_height": 0-100}
    tactical_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    players: Mapped[list["Player"]] = relationship(back_populates="team")
