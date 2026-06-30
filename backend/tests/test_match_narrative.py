import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.prediction.match_narrative import build_predicted_narrative


def _squad(team_id: str, base_overall: int) -> list[dict]:
    """A 15-man squad spanning every position the XI selector needs."""
    positions = [
        "GK", "LB", "CB", "CB", "RB", "CDM", "CM", "CM",
        "LW", "RW", "ST", "ST", "CB", "CM", "GK",
    ]
    return [
        {
            "id": f"{team_id}_{i}",
            "name": f"{team_id} Player {i}",
            "name_ja": None,
            "primary_position": pos,
            "secondary_positions": [],
            "overall": base_overall + (i % 5),
            "attributes": {},
            "stamina_max": 100,
        }
        for i, pos in enumerate(positions)
    ]


def _build(home_score, away_score, seed=7):
    return build_predicted_narrative(
        "HOME", "AWAY",
        _squad("HOME", 82), _squad("AWAY", 74),
        "4-3-3", "4-3-3",
        {"possession_style": 60.0, "press_intensity": 55.0}, None,
        home_score, away_score,
        lambda_home=1.8, lambda_away=0.9,
        rng=random.Random(seed),
    )


def test_goal_events_match_scoreline():
    n = _build(2, 1)
    goals = [e for e in n["events"] if e["event_type"] == "goal"]
    assert len(goals) == 3
    home_goals = [e for e in goals if e["team_id"] == "HOME"]
    away_goals = [e for e in goals if e["team_id"] == "AWAY"]
    assert len(home_goals) == 2 and len(away_goals) == 1
    # Every scorer is attributed to a real starting-XI player.
    xi_ids = {p["player_id"] for p in n["home_lineup"]} | {p["player_id"] for p in n["away_lineup"]}
    assert all(e["player_id"] in xi_ids for e in goals)


def test_events_are_time_ordered_and_bracketed():
    n = _build(3, 2)
    assert n["events"][0]["event_type"] == "kickoff"
    minutes = [e["minute"] for e in n["events"]]
    assert minutes == sorted(minutes)


def test_possession_sums_to_100_and_favours_stronger_side():
    n = _build(1, 0)
    assert n["home_possession_pct"] + n["away_possession_pct"] == 100
    # HOME is the stronger, higher-possession-style side.
    assert n["home_possession_pct"] > n["away_possession_pct"]
    assert 35 <= n["home_possession_pct"] <= 65


def test_shots_consistent_with_goals():
    n = _build(2, 0)
    assert n["home_shots"] >= n["home_shots_on_target"] >= 2  # >= goals scored
    assert n["away_shots"] >= n["away_shots_on_target"] >= 0
    assert n["home_shots_on_target"] >= 2


def test_lineups_are_full_elevens():
    n = _build(0, 0)
    assert len(n["home_lineup"]) == 11
    assert len(n["away_lineup"]) == 11
    assert len(n["home_roster"]) == 11
    # A 0-0 has no goal events, only the kickoff.
    assert [e["event_type"] for e in n["events"]] == ["kickoff"]


def test_deterministic_for_same_seed():
    a = _build(2, 1, seed=99)
    b = _build(2, 1, seed=99)
    assert [e["description"] for e in a["events"]] == [e["description"] for e in b["events"]]
    assert a["home_possession_pct"] == b["home_possession_pct"]
    assert a["home_shots"] == b["home_shots"]
