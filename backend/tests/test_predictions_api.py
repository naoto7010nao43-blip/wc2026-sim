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


def test_match_prediction_endpoint_returns_disclaimer_and_probabilities(client):
    resp = client.get("/api/predictions/BRA/ARG")
    assert resp.status_code == 200
    body = resp.json()
    assert body["home_team_id"] == "BRA"
    assert body["away_team_id"] == "ARG"
    assert "予測" in body["disclaimer"]
    total = body["home_win_pct"] + body["draw_pct"] + body["away_win_pct"]
    assert abs(total - 100.0) < 0.5
    assert len(body["most_likely_scores"]) == 3


def test_match_prediction_endpoint_404s_for_unknown_team(client):
    resp = client.get("/api/predictions/BRA/NOPE")
    assert resp.status_code == 404


def test_monte_carlo_endpoint_returns_stage_percentages(client):
    resp = client.post("/api/tournament/simulate-monte-carlo", json={"iterations": 100, "seed": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["iterations"] == 100
    assert "予測" in body["disclaimer"]
    assert sum(body["champion_pct"].values()) > 0


def test_monte_carlo_endpoint_rejects_out_of_range_iterations(client):
    resp = client.post("/api/tournament/simulate-monte-carlo", json={"iterations": 50000, "seed": 0})
    assert resp.status_code == 422
