from app.services.match_analysis import (
    build_match_analysis,
    build_tactical_note,
    compute_momentum_segments,
    compute_turning_point,
    top_key_players,
)


def _goal(minute, team_id, description="goal"):
    return {"minute": minute, "event_type": "goal", "team_id": team_id, "description": description, "event_metadata": None}


def test_turning_point_is_none_when_no_goals():
    assert compute_turning_point([], "BRA", "ARG") is None


def test_turning_point_is_the_only_goal_in_a_one_goal_match():
    events = [_goal(34, "BRA", "34分の得点")]
    tp = compute_turning_point(events, "BRA", "ARG")
    assert tp == {"minute": 34, "team_id": "BRA", "description": "34分の得点"}


def test_turning_point_is_the_last_lead_change_not_the_final_goal():
    # BRA scores (BRA leads), ARG equalizes (tie), ARG scores again (ARG
    # leads), ARG scores a third time -- ARG still leads, no change, so the
    # 55' goal (the actual lead change to ARG) stays the turning point, not
    # the later goal that merely extends an already-decided lead.
    events = [_goal(10, "BRA"), _goal(40, "ARG"), _goal(55, "ARG"), _goal(80, "ARG")]
    tp = compute_turning_point(events, "BRA", "ARG")
    assert tp["minute"] == 55
    assert tp["team_id"] == "ARG"


def test_turning_point_handles_penalty_kick_goals():
    events = [{"minute": 70, "event_type": "penalty_kick", "team_id": "BRA", "description": "PK決定", "event_metadata": {"scored": True}}]
    tp = compute_turning_point(events, "BRA", "ARG")
    assert tp["minute"] == 70
    missed = [{"minute": 71, "event_type": "penalty_kick", "team_id": "ARG", "description": "PK失敗", "event_metadata": {"scored": False}}]
    assert compute_turning_point(missed, "BRA", "ARG") is None


def test_momentum_segments_groups_attacking_events_by_window():
    events = [
        {"minute": 5, "event_type": "shot", "team_id": "BRA"},
        {"minute": 10, "event_type": "shot", "team_id": "BRA"},
        {"minute": 20, "event_type": "shot", "team_id": "ARG"},
        {"minute": 50, "event_type": "tackle", "team_id": "ARG"},  # not an attacking event type, ignored
    ]
    segments = compute_momentum_segments(events, "BRA", "ARG")
    assert segments[0] == {"start_minute": 0, "end_minute": 15, "home_actions": 2, "away_actions": 0, "dominant_team_id": "BRA"}
    assert segments[1]["dominant_team_id"] == "ARG"
    assert len(segments) == 2  # the 50-minute tackle doesn't create a segment


def test_momentum_segments_empty_when_no_attacking_events():
    assert compute_momentum_segments([{"minute": 5, "event_type": "tackle", "team_id": "BRA"}], "BRA", "ARG") == []


def test_top_key_players_sorted_descending_and_limited():
    ratings = [
        {"player_id": "a", "name": "A", "team_id": "BRA", "rating": 6.5, "is_mom": False},
        {"player_id": "b", "name": "B", "team_id": "BRA", "rating": 8.5, "is_mom": True},
        {"player_id": "c", "name": "C", "team_id": "ARG", "rating": 7.0, "is_mom": False},
        {"player_id": "d", "name": "D", "team_id": "ARG", "rating": 5.0, "is_mom": False},
    ]
    top = top_key_players(ratings, n=3)
    assert [p["player_id"] for p in top] == ["b", "c", "a"]


def test_tactical_note_includes_manager_and_press_when_present():
    note = build_tactical_note(
        "BRA", "ARG", "4-3-3", "4-4-2",
        {"manager_name": "Carlo Ancelotti", "press_intensity": 70, "possession_style": 60},
        None,
    )
    assert "Carlo Ancelotti" in note
    assert "4-3-3" in note
    assert "ARGは4-4-2を採用" in note


def test_build_match_analysis_returns_none_without_events():
    assert build_match_analysis([], [], "BRA", "ARG", "4-3-3", "4-4-2", None, None) is None


def test_build_match_analysis_full_shape():
    events = [_goal(10, "BRA")]
    ratings = [{"player_id": "a", "name": "A", "team_id": "BRA", "rating": 7.0, "is_mom": True}]
    analysis = build_match_analysis(events, ratings, "BRA", "ARG", "4-3-3", "4-4-2", None, None)
    assert analysis["turning_point"]["team_id"] == "BRA"
    assert analysis["key_players"][0]["player_id"] == "a"
    assert isinstance(analysis["tactical_note"], str)
