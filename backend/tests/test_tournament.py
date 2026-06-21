import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.match import Match  # noqa: F401  (ensures table is registered with Base.metadata)
from app.models.player import Player
from app.models.team import Team
from app.rating.seed_pipeline import build_player_rows, load_seed_data
from app.services.tournament import run_full_tournament


def _make_seeded_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    teams_raw, players_raw = load_seed_data()
    player_rows = build_player_rows(players_raw)

    for t in teams_raw:
        session.add(Team(
            id=t["id"],
            name=t["name"],
            confederation=t["confederation"],
            fifa_rank=t.get("fifa_rank"),
            default_formation=t["default_formation"],
            group_id=t.get("group_id"),
            tactical_profile=t.get("tactical_profile"),
        ))
    session.flush()
    for p in player_rows:
        session.add(Player(**p))
    session.commit()
    return session


@pytest.fixture()
def db_session():
    session = _make_seeded_session()
    try:
        yield session
    finally:
        session.close()


def test_full_tournament_produces_104_matches_and_one_champion(db_session):
    result = run_full_tournament(db_session, base_seed=0)

    matches = result["matches"]
    assert len(matches["group"]) == 72
    assert len(matches["R32"]) == 16
    assert len(matches["R16"]) == 8
    assert len(matches["QF"]) == 4
    assert len(matches["SF"]) == 2
    assert len(matches["THIRD_PLACE"]) == 1
    assert len(matches["FINAL"]) == 1
    total = sum(len(ms) for ms in matches.values())
    assert total == 104

    assert isinstance(result["champion_team_id"], str)
    assert len(result["qualifying_third_groups"]) == 8

    # Every knockout match must have a real winner (no unresolved ties).
    for round_name in ("R32", "R16", "QF", "SF", "THIRD_PLACE", "FINAL"):
        for m in matches[round_name]:
            assert m.home_score != m.away_score or m.went_to_penalties


def test_tournament_is_deterministic_given_the_same_base_seed(db_session):
    result1 = run_full_tournament(db_session, base_seed=42)
    champion1 = result1["champion_team_id"]

    # Re-run against a freshly-seeded DB with the same base_seed.
    session2 = _make_seeded_session()
    try:
        result2 = run_full_tournament(session2, base_seed=42)
        assert result2["champion_team_id"] == champion1
    finally:
        session2.close()
