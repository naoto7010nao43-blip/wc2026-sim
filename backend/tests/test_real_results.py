import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.match import Match, MatchEvent
from app.models.player import Player
from app.models.team import Team
from app.services.real_results import persist_real_match


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Team(id="HOME", name="Home Land", confederation="X", default_formation="4-3-3"))
    session.add(Team(id="AWAY", name="Away Land", confederation="X", default_formation="4-4-2"))
    session.add(Player(
        id="HOME_STAR", team_id="HOME", name="Star Player", name_ja="スター・プレイヤー",
        age=25, primary_position="ST", overall=80, attributes={},
    ))
    session.commit()
    yield session
    session.close()


def test_persist_legacy_goals_only_schema(db):
    result = {
        "home_score": 2, "away_score": 0, "date": "2026-06-11",
        "goals": [
            {"minute": 9, "team_id": "HOME", "scorer_name": "Star Player"},
            {"minute": 67, "team_id": "HOME", "scorer_name": "Some Other Guy", "scorer_name_ja": "サム・アザー"},
        ],
    }
    match = persist_real_match(db, "HOME", "AWAY", result, group_id="A")
    assert match.data_source == "Wikipedia (2026 FIFA World Cup Group pages)"
    assert match.home_lineup == []
    assert match.player_ratings == []
    events = db.query(MatchEvent).filter_by(match_id=match.id).order_by(MatchEvent.id).all()
    descriptions = [e.description for e in events]
    assert "スター・プレイヤー がゴール!" in descriptions
    assert "サム・アザー がゴール!" in descriptions


def test_persist_api_football_schema_with_lineup_and_ratings(db):
    result = {
        "home_score": 1, "away_score": 0, "date": "2026-06-11", "source": "api-football",
        "stats": {"home_possession_pct": 60, "away_possession_pct": 40},
        "lineups": {
            "home": {
                "formation": "1-1", "coach": "Test Coach",
                "players": [
                    {"name": "Keeper Guy", "position": "GK", "grid": "1:1"},
                    {"name": "Star Player", "position": "FW", "grid": "2:1"},
                ],
            },
            "away": {"formation": "1-1", "coach": "Other Coach", "players": [
                {"name": "Defender Guy", "position": "DF", "grid": "1:1"},
            ]},
        },
        "events": [
            {"minute": 30, "type": "Goal", "team_id": "HOME", "player_name": "Star Player", "assist_name": None},
            {"minute": 60, "type": "subst", "team_id": "HOME", "player_name": "Sub Guy", "assist_name": "Star Player"},
            {"minute": 75, "type": "Card", "detail": "Yellow Card", "team_id": "AWAY", "player_name": "Defender Guy"},
        ],
        "player_ratings": [
            {"name": "Star Player", "team_id": "HOME", "rating": 8.2},
            {"name": "Defender Guy", "team_id": "AWAY", "rating": 6.1},
        ],
    }
    match = persist_real_match(db, "HOME", "AWAY", result, group_id="A")

    assert match.data_source == "API-Football"
    assert match.home_formation == "1-1"

    assert len(match.home_lineup) == 2
    keeper = next(p for p in match.home_lineup if p["name"] == "Keeper Guy")
    striker = next(p for p in match.home_lineup if p["player_id"] == "HOME_STAR")
    assert keeper["x"] == 5.0  # row 1 of 2 -> deepest
    assert striker["x"] == 90.0  # row 2 of 2 -> most advanced
    assert striker["name"] == "スター・プレイヤー"  # resolved against roster's name_ja

    events = db.query(MatchEvent).filter_by(match_id=match.id).order_by(MatchEvent.id).all()
    types = [e.event_type for e in events]
    assert "goal" in types
    assert "substitution" in types
    assert "yellow_card" in types

    assert len(match.player_ratings) == 2
    by_name = {r["name"]: r for r in match.player_ratings}
    assert by_name["スター・プレイヤー"]["is_mom"] is True
    assert by_name["スター・プレイヤー"]["is_estimated"] is False
    assert by_name["Defender Guy"]["is_mom"] is False


def test_persist_knockout_match_with_penalties(db):
    """A drawn R32 fixture decided on penalties: round/bracket_slot are set,
    penalty fields persist, and a penalty_shootout event is emitted."""
    result = {
        "round": "R32", "home_score": 1, "away_score": 1,
        "went_to_penalties": True, "penalty_home_score": 3, "penalty_away_score": 4,
        "date": "2026-06-29",
        "goals": [
            {"minute": 54, "team_id": "HOME", "scorer_name": "Star Player"},
        ],
    }
    match = persist_real_match(db, "HOME", "AWAY", result, round="R32", bracket_slot="R32_1")

    assert match.round == "R32"
    assert match.bracket_slot == "R32_1"
    assert match.group_id is None
    assert match.went_to_penalties is True
    assert match.penalty_home_score == 3
    assert match.penalty_away_score == 4
    assert match.data_source == "Wikipedia (2026 FIFA World Cup knockout stage)"

    events = db.query(MatchEvent).filter_by(match_id=match.id).order_by(MatchEvent.id).all()
    types = [e.event_type for e in events]
    assert "penalty_shootout" in types
    shootout = next(e for e in events if e.event_type == "penalty_shootout")
    assert "3-4" in shootout.description
    assert shootout.event_metadata["penalty_away_score"] == 4
