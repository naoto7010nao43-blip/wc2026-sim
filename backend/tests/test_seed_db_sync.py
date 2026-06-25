import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from scripts.seed_db import sync_reference_data


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestSession()
    yield db
    db.close()


def test_sync_reference_data_overwrites_stale_team_row(session):
    session.add(Team(
        id="URU", name="Uruguay (stale)", confederation="CONMEBOL",
        fifa_rank=999, default_formation="4-3-3",
    ))
    session.commit()

    sync_reference_data(session)

    uru = session.get(Team, "URU")
    assert uru is not None
    assert uru.name == "Uruguay"
    assert uru.fifa_rank != 999


def test_sync_reference_data_preserves_existing_match_rows(session):
    session.add(Team(
        id="URU", name="Uruguay (stale)", confederation="CONMEBOL",
        fifa_rank=999, default_formation="4-3-3",
    ))
    session.add(Team(
        id="BRA", name="Brazil (stale)", confederation="CONMEBOL",
        fifa_rank=999, default_formation="4-3-3",
    ))
    session.commit()

    match = Match(
        id="test-match-1", home_team_id="URU", away_team_id="BRA",
        home_formation="4-3-3", away_formation="4-3-3", is_real=False,
    )
    session.add(match)
    session.commit()
    match_id = match.id

    sync_reference_data(session)

    preserved = session.get(Match, match_id)
    assert preserved is not None
    assert preserved.home_team_id == "URU"
    assert preserved.away_team_id == "BRA"


def test_sync_reference_data_populates_full_team_and_player_set(session):
    sync_reference_data(session)

    assert session.query(Team).count() >= 48
    assert session.query(Player).count() > 0
