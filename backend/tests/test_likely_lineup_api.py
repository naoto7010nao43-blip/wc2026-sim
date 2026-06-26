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
from app.rating.seed_pipeline import build_player_rows, load_seed_data


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    teams_raw, players_raw = load_seed_data()
    player_rows = build_player_rows(players_raw)
    seed_session = TestSession()
    for t in teams_raw:
        seed_session.add(Team(
            id=t["id"], name=t["name"], confederation=t["confederation"],
            fifa_rank=t.get("fifa_rank"), default_formation=t["default_formation"],
            group_id=t.get("group_id"), tactical_profile=t.get("tactical_profile"),
        ))
    seed_session.flush()
    for p in player_rows:
        seed_session.add(Player(**p))
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


def test_likely_lineup_endpoint_returns_11_slots_with_disclaimer(client):
    resp = client.get("/api/teams/BRA/likely-lineup")
    assert resp.status_code == 200
    body = resp.json()
    assert body["team_id"] == "BRA"
    assert len(body["lineup"]) == 11
    assert "公式発表" in body["disclaimer"]
    assert "推定" in body["disclaimer"]
    player_ids = [slot["player_id"] for slot in body["lineup"]]
    assert len(player_ids) == len(set(player_ids))


def test_likely_lineup_never_places_a_goalkeeper_outfield(client):
    # Partial rosters previously let the last-resort fallback drop a backup
    # keeper into an outfield slot (e.g. Japan's 3rd centre-back). A GK must
    # only ever occupy the GK slot. Check every team to lock the invariant.
    teams = client.get("/api/teams").json()
    for team in teams:
        body = client.get(f"/api/teams/{team['id']}/likely-lineup").json()
        for slot in body["lineup"]:
            if slot["slot_position"] != "GK":
                assert slot["primary_position"] != "GK", (
                    f"{team['id']}: {slot['name']} (GK) placed at {slot['slot_position']}"
                )


def test_likely_lineup_endpoint_404s_for_unknown_team(client):
    resp = client.get("/api/teams/ZZZ/likely-lineup")
    assert resp.status_code == 404
