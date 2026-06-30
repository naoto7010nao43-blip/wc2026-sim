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


def test_security_headers_present_on_every_response(client):
    resp = client.get("/api/teams")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "permissions-policy" in resp.headers


def test_local_preview_origin_is_allowed_for_browser_smoke(client):
    origin = "http://127.0.0.1:4173"
    resp = client.options(
        "/api/teams",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == origin


def test_tournament_run_is_rate_limited_per_ip(client):
    # Limit is 6/min -- the first 6 should succeed (200), the 7th must be
    # rejected with 429 rather than silently letting an unbounded number of
    # full-tournament resimulations run for one client in a tight loop.
    statuses = [client.post("/api/tournament/run", json={"seed": i}).status_code for i in range(7)]
    assert statuses[:6] == [200] * 6
    assert statuses[6] == 429


def test_round_robin_rejects_oversized_team_list(client):
    team_ids = ["BRA", "ARG", "FRA", "ENG", "GER", "USA", "MEX", "ESP", "NED"]  # 9 > max 8
    resp = client.post("/api/groups/X/simulate-round-robin", json={"team_ids": team_ids})
    assert resp.status_code == 422


def test_round_robin_accepts_normal_group_size(client):
    resp = client.post("/api/groups/X/simulate-round-robin", json={"team_ids": ["BRA", "ARG", "FRA", "ENG"]})
    assert resp.status_code == 200
