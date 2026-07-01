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


def test_tournament_group_difficulty_returns_ranked_groups(client):
    resp = client.get("/api/tournament/group-difficulty")
    assert resp.status_code == 200
    body = resp.json()
    assert body["group_count"] == 12
    assert len(body["groups"]) == 12
    assert body["model_version"].startswith("poisson-v")
    assert "保証" in body["disclaimer"]
    scores = [row["difficulty_score"] for row in body["groups"]]
    assert scores == sorted(scores, reverse=True)
    bands = {row["difficulty_band"] for row in body["groups"]}
    assert "high" in bands
    assert "medium" in bands
    for row in body["groups"]:
        assert row["group_id"] in "ABCDEFGHIJKL"
        assert row["difficulty_band"] in {"high", "medium", "low"}
        assert len(row["teams"]) == 4
        assert row["top_team_id"] == row["teams"][0]["team_id"]
        assert row["average_strength"] > 0
        assert row["average_favorite_gap_pct"] >= 0
        assert row["average_draw_pct"] >= 0
        assert row["upset_pressure"] >= 0
        assert row["reason_ja"]
        _assert_no_mojibake(row["reason_ja"])


def test_tournament_path_projection_returns_stage_opponent_distribution(client):
    resp = client.get("/api/tournament/path-projection?team_id=JPN&iterations=100")
    assert resp.status_code == 200
    body = resp.json()
    assert body["team_id"] == "JPN"
    assert body["iterations"] == 100
    assert body["model_version"].startswith("poisson-v")
    assert 0 <= body["champion_pct"] <= 100
    assert "想定ルート" in body["note_ja"]
    assert "保証" in body["disclaimer"]
    _assert_no_mojibake(body["note_ja"])
    _assert_no_mojibake(body["disclaimer"])

    stages = body["stages"]
    assert [stage["stage_key"] for stage in stages] == ["R32", "R16", "QF", "SF", "FINAL"]
    for stage in stages:
        assert 0 <= stage["reach_pct"] <= 100
        assert stage["stage_label_ja"]
        _assert_no_mojibake(stage["stage_label_ja"])
        opponent_pcts = [row["probability_pct"] for row in stage["opponent_options"]]
        assert opponent_pcts == sorted(opponent_pcts, reverse=True)
        for opponent in stage["opponent_options"]:
            assert opponent["team_id"] != "JPN"
            assert opponent["team_name"]
            assert 0 <= opponent["probability_pct"] <= 100


def test_tournament_path_projection_unknown_team_returns_404(client):
    resp = client.get("/api/tournament/path-projection?team_id=XXX&iterations=100")
    assert resp.status_code == 404


def test_tournament_final_matchups_returns_ranked_candidate_pairs(client):
    resp = client.get("/api/tournament/final-matchups?iterations=100&limit=6")
    assert resp.status_code == 200
    body = resp.json()
    assert body["iterations"] == 100
    assert body["matchup_count"] >= len(body["candidates"]) > 0
    assert len(body["candidates"]) <= 6
    assert body["model_version"].startswith("poisson-v")
    assert "決勝" in body["note_ja"]
    assert "保証" in body["disclaimer"]
    _assert_no_mojibake(body["note_ja"])
    _assert_no_mojibake(body["disclaimer"])

    pcts = [row["matchup_pct"] for row in body["candidates"]]
    assert pcts == sorted(pcts, reverse=True)
    for row in body["candidates"]:
        assert row["team_a_id"] != row["team_b_id"]
        assert row["team_a_name"]
        assert row["team_b_name"]
        assert row["champion_favorite_team_id"] in {row["team_a_id"], row["team_b_id"]}
        assert row["matchup_pct"] > 0
        assert 99.0 <= row["team_a_win_given_matchup_pct"] + row["team_b_win_given_matchup_pct"] <= 101.0
