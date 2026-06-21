import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.player_ratings import compute_player_ratings


def test_empty_roster_returns_no_ratings():
    assert compute_player_ratings([], {}, {}, "HOME", "AWAY") == []


def test_goal_scorer_rated_above_baseline_and_is_mom():
    home_roster = {"H1": "Striker", "H2": "Defender"}
    away_roster = {"A1": "Keeper"}
    events = [
        {"event_type": "kickoff", "player_id": None, "secondary_player_id": None, "event_metadata": None},
        {"event_type": "goal", "player_id": "H1", "secondary_player_id": None, "event_metadata": {"xg": 0.3}},
    ]
    ratings = compute_player_ratings(events, home_roster, away_roster, "HOME", "AWAY")
    by_id = {r["player_id"]: r for r in ratings}

    assert by_id["H1"]["rating"] > 6.0
    assert by_id["H1"]["is_mom"] is True
    assert by_id["H2"]["rating"] == 6.0
    assert by_id["A1"]["rating"] == 6.0
    assert sum(1 for r in ratings if r["is_mom"]) == 1


def test_yellow_card_lowers_rating():
    home_roster = {"H1": "Defender"}
    events = [{"event_type": "yellow_card", "player_id": "H1", "secondary_player_id": None, "event_metadata": None}]
    ratings = compute_player_ratings(events, home_roster, {}, "HOME", "AWAY")
    assert ratings[0]["rating"] < 6.0


def test_tackler_gains_and_dispossessed_player_loses():
    home_roster = {"H1": "Defender"}
    away_roster = {"A1": "Attacker"}
    events = [{"event_type": "tackle", "player_id": "H1", "secondary_player_id": "A1", "event_metadata": None}]
    ratings = compute_player_ratings(events, home_roster, away_roster, "HOME", "AWAY")
    by_id = {r["player_id"]: r for r in ratings}
    assert by_id["H1"]["rating"] > 6.0
    assert by_id["A1"]["rating"] < 6.0


def test_ratings_are_clamped_to_valid_range():
    home_roster = {"H1": "Striker"}
    events = [{"event_type": "goal", "player_id": "H1", "secondary_player_id": None, "event_metadata": {}} for _ in range(20)]
    ratings = compute_player_ratings(events, home_roster, {}, "HOME", "AWAY")
    assert ratings[0]["rating"] <= 10.0
