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

MOJIBAKE_MARKERS = ("邵ｺ", "郢・", "闔", "陷・", "陞・", "驍・", "隰・")


def _assert_no_mojibake(text: str) -> None:
    for marker in MOJIBAKE_MARKERS:
        assert marker not in text


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


def test_adhoc_single_match_is_not_treated_as_tournament_state(client):
    # Mode 2 (試合シミュレーター) calls /api/matches/simulate directly, with no
    # group_id/bracket_slot -- this must not make /api/tournament/state think
    # a tournament is in progress.
    resp = client.post("/api/matches/simulate", json={"home_team_id": "BRA", "away_team_id": "ARG", "seed": 1})
    assert resp.status_code == 200

    state = client.get("/api/tournament/state")
    assert state.status_code == 200
    assert state.json() is None


def test_running_tournament_does_not_delete_adhoc_match(client):
    adhoc = client.post("/api/matches/simulate", json={"home_team_id": "BRA", "away_team_id": "ARG", "seed": 1})
    adhoc_id = adhoc.json()["id"]

    run = client.post("/api/tournament/run", json={"seed": 0})
    assert run.status_code == 200

    # The ad-hoc match's shareable link must still resolve after a tournament run.
    fetched = client.get(f"/api/matches/{adhoc_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == adhoc_id


def test_tournament_state_reflects_a_real_run(client):
    run = client.post("/api/tournament/run", json={"seed": 0})
    assert run.status_code == 200

    state = client.get("/api/tournament/state")
    assert state.status_code == 200
    body = state.json()
    assert body is not None
    assert len(body["matches"]["group"]) == 72


def test_tournament_upset_watch_returns_ranked_group_candidates(client):
    resp = client.get("/api/tournament/upset-watch")
    assert resp.status_code == 200
    body = resp.json()
    assert body["match_count"] == 72
    assert len(body["candidates"]) == 12
    assert body["model_version"].startswith("poisson-v")
    assert "予測" in body["disclaimer"]
    _assert_no_mojibake(body["disclaimer"])
    scores = [row["upset_score"] for row in body["candidates"]]
    assert scores == sorted(scores, reverse=True)
    for row in body["candidates"]:
        assert row["group_id"] in "ABCDEFGHIJKL"
        assert row["favorite_team_id"] in {row["home_team_id"], row["away_team_id"]}
        assert row["underdog_team_id"] in {row["home_team_id"], row["away_team_id"]}
        assert row["favorite_team_id"] != row["underdog_team_id"]
        assert row["favorite_win_pct"] >= row["underdog_win_pct"]
        assert row["upset_score"] >= row["underdog_win_pct"]
        assert row["reason_ja"]
        _assert_no_mojibake(row["reason_ja"])


def test_tournament_upset_watch_respects_limit(client):
    resp = client.get("/api/tournament/upset-watch?limit=5")
    assert resp.status_code == 200
    assert len(resp.json()["candidates"]) == 5
