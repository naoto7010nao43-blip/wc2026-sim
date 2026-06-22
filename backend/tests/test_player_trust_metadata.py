import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.player import Player
from app.models.team import Team


def _make_player(**overrides) -> Player:
    base = dict(
        id="TST_PLAYER", team_id="TST", name="Test Player", name_ja=None, age=26,
        primary_position="ST", secondary_positions=[], overall=70,
        attributes={"pace": 70, "shooting": 70, "passing": 70, "dribbling": 70, "defending": 70, "physical": 70},
        stamina_max=90,
    )
    base.update(overrides)
    return Player(**base)


def test_trust_properties_return_values_when_attributes_contain_them():
    player = _make_player(attributes={
        "pace": 70, "shooting": 70, "passing": 70, "dribbling": 70, "defending": 70, "physical": 70,
        "startingProbability": 73, "dataConfidence": "estimated", "uncertainty": 0.25,
        "sourceBreakdown": {"officialRoster": True, "marketValueUsed": True, "clubMinutesUsed": True,
                             "nationalTeamMinutesUsed": False, "injuryDataUsed": False, "manualOverrideUsed": False},
        "lowConfidenceAttributes": ["mentality", "composure"],
        "lastUpdated": "2026-06-22T00:00:00+00:00",
        "dateOfBirth": "02/10/1992",
        "heightCm": 193,
        "clubName": "Liverpool FC (ENG)",
        "caps": 80,
        "nationalTeamGoals": 0,
    })
    assert player.starting_probability == 73
    assert player.data_confidence == "estimated"
    assert player.uncertainty == 0.25
    assert player.source_breakdown == {
        "officialRoster": True, "marketValueUsed": True, "clubMinutesUsed": True,
        "nationalTeamMinutesUsed": False, "injuryDataUsed": False, "manualOverrideUsed": False,
    }
    assert player.low_confidence_attributes == ["mentality", "composure"]
    assert player.rating_last_updated == "2026-06-22T00:00:00+00:00"
    assert player.date_of_birth == "02/10/1992"
    assert player.height_cm == 193
    assert player.club_name == "Liverpool FC (ENG)"
    assert player.caps == 80
    assert player.national_team_goals == 0


def test_trust_properties_return_safe_defaults_for_legacy_data_without_crashing():
    # Legacy/pre-v2 seed data never had these keys at all.
    player = _make_player(attributes={
        "pace": 70, "shooting": 70, "passing": 70, "dribbling": 70, "defending": 70, "physical": 70,
    })
    assert player.starting_probability is None
    assert player.data_confidence is None
    assert player.uncertainty is None
    assert player.source_breakdown is None
    assert player.low_confidence_attributes == []
    assert player.rating_last_updated is None
    assert player.date_of_birth is None
    assert player.height_cm is None
    assert player.club_name is None
    assert player.caps is None
    assert player.national_team_goals is None


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    seed_session = TestSession()
    seed_session.add(Team(
        id="TST", name="Test Team", confederation="UEFA", fifa_rank=10,
        default_formation="4-4-2", group_id="A", tactical_profile=None,
    ))
    seed_session.flush()
    seed_session.add(_make_player(attributes={
        "pace": 70, "shooting": 70, "passing": 70, "dribbling": 70, "defending": 70, "physical": 70,
        "startingProbability": 73, "dataConfidence": "estimated", "uncertainty": 0.25,
        "sourceBreakdown": {"officialRoster": True, "marketValueUsed": True, "clubMinutesUsed": True,
                             "nationalTeamMinutesUsed": False, "injuryDataUsed": False, "manualOverrideUsed": False},
        "lowConfidenceAttributes": ["mentality"], "lastUpdated": "2026-06-22T00:00:00+00:00",
        "dateOfBirth": "02/10/1992", "heightCm": 193, "clubName": "Liverpool FC (ENG)",
        "caps": 80, "nationalTeamGoals": 0,
    }))
    seed_session.add(_make_player(id="TST_LEGACY", attributes={
        "pace": 60, "shooting": 60, "passing": 60, "dribbling": 60, "defending": 60, "physical": 60,
    }))
    seed_session.commit()
    seed_session.close()

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_player_endpoint_exposes_trust_metadata_when_present(client):
    resp = client.get("/api/players/TST_PLAYER")
    assert resp.status_code == 200
    body = resp.json()
    assert body["starting_probability"] == 73
    assert body["data_confidence"] == "estimated"
    assert body["uncertainty"] == 0.25
    assert body["source_breakdown"]["officialRoster"] is True
    assert body["low_confidence_attributes"] == ["mentality"]
    assert body["rating_last_updated"] == "2026-06-22T00:00:00+00:00"
    assert body["date_of_birth"] == "02/10/1992"
    assert body["height_cm"] == 193
    assert body["club_name"] == "Liverpool FC (ENG)"
    assert body["caps"] == 80
    assert body["national_team_goals"] == 0


def test_player_endpoint_serializes_legacy_player_without_crashing(client):
    resp = client.get("/api/players/TST_LEGACY")
    assert resp.status_code == 200
    body = resp.json()
    assert body["starting_probability"] is None
    assert body["data_confidence"] is None
    assert body["source_breakdown"] is None
    assert body["low_confidence_attributes"] == []
    assert body["date_of_birth"] is None
    assert body["height_cm"] is None
    assert body["club_name"] is None
    assert body["caps"] is None
    assert body["national_team_goals"] is None


def test_team_endpoint_players_include_trust_metadata(client):
    resp = client.get("/api/teams/TST")
    assert resp.status_code == 200
    body = resp.json()
    by_id = {p["id"]: p for p in body["players"]}
    assert by_id["TST_PLAYER"]["data_confidence"] == "estimated"
    assert by_id["TST_PLAYER"]["club_name"] == "Liverpool FC (ENG)"
    assert by_id["TST_PLAYER"]["caps"] == 80
    assert by_id["TST_LEGACY"]["data_confidence"] is None
    assert by_id["TST_LEGACY"]["club_name"] is None
