"""Reads data/seed/*.json, runs the rating pipeline, and (re)populates the
SQLite database. Safe to re-run after editing seed JSON or rating formulas.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models.player import Player
from app.models.team import Team
from app.rating.seed_pipeline import build_player_rows, load_seed_data


def main():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    teams_raw, players_raw = load_seed_data()
    player_rows = build_player_rows(players_raw)

    db = SessionLocal()
    try:
        for t in teams_raw:
            db.add(Team(
                id=t["id"],
                name=t["name"],
                confederation=t["confederation"],
                fifa_rank=t.get("fifa_rank"),
                default_formation=t["default_formation"],
                group_id=t.get("group_id"),
                tactical_profile=t.get("tactical_profile"),
            ))
        db.flush()

        for p in player_rows:
            db.add(Player(**p))

        db.commit()
        print(f"Seeded {len(teams_raw)} teams and {len(player_rows)} players.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
