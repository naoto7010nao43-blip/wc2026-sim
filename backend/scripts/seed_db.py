"""Reads data/seed/*.json, runs the rating pipeline, and (re)populates the
SQLite database. Safe to re-run after editing seed JSON or rating formulas.

Prefers the v2 official/estimated data layer (players2026_official.json +
playerRatings2026_estimated.json, see app/rating_v2/) when present, falling
back to the original Stage A/B/C pipeline (app/rating/) otherwise -- the
v2 files are produced by scripts/migrate_to_player_data_v2.py +
scripts/rebuild_player_ratings_v2.py, which must be run first.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models.player import Player
from app.models.team import Team
from app.rating.seed_pipeline import build_player_rows, load_seed_data
from app.rating_v2.seed_pipeline_v2 import load_v2_seed_data, v2_files_present


def _load_teams_and_players():
    if v2_files_present():
        teams_raw, player_rows = load_v2_seed_data()
    else:
        teams_raw, players_raw = load_seed_data()
        player_rows = build_player_rows(players_raw)
    return teams_raw, player_rows


def main():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    teams_raw, player_rows = _load_teams_and_players()
    if v2_files_present():
        print("Seeding from v2 official/estimated data layer.")

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


def sync_reference_data(db):
    """Re-syncs Team/Player rows in place from the current seed JSON, without
    touching Match/MatchEvent/Prediction/TournamentResult rows.

    Team/Player are pure reference data -- nothing in the app mutates them at
    runtime (only Match/MatchEvent/Prediction/TournamentResult rows are
    written after seeding, see app/api/matches.py, app/services/predicted_match.py,
    app/api/tournament.py). So it is always safe to overwrite them in place,
    even against a database that already has match/tournament history,
    making this safe to run unconditionally on every startup rather than
    only when the database happens to be empty.
    """
    teams_raw, player_rows = _load_teams_and_players()

    db.query(Player).delete()
    db.query(Team).delete()
    db.flush()

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
    print(f"Synced {len(teams_raw)} teams and {len(player_rows)} players (reference-data resync).")


if __name__ == "__main__":
    main()
