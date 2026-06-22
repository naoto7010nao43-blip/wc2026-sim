import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.match import Match
from app.services.tiebreakers import (
    TeamAggregate,
    break_ties,
    compute_conduct_scores,
)


def _match(home: str, away: str, home_score: int, away_score: int, *, hy=0, ay=0, hr=0, ar=0) -> Match:
    return Match(
        home_team_id=home,
        away_team_id=away,
        home_score=home_score,
        away_score=away_score,
        home_yellow_cards=hy,
        away_yellow_cards=ay,
        home_red_cards=hr,
        away_red_cards=ar,
    )


def _agg(points: int, goal_diff: int, goals_for: int, team_id: str = "") -> TeamAggregate:
    return TeamAggregate(team_id, points, goal_diff, goals_for)


def test_no_tie_resolved_purely_by_points():
    matches = [_match("A", "B", 3, 0), _match("A", "C", 2, 0), _match("B", "C", 1, 1)]
    aggregates = {"A": _agg(6, 5, 5), "B": _agg(1, -2, 1), "C": _agg(1, -3, 1)}
    # B and C are tied on points (1 each) -- separated below by GD via h2h.
    result = break_ties(["A", "B", "C"], matches, aggregates, {}, {})
    assert [tid for tid, _ in result][0] == "A"
    assert result[0][1] == "points"


def test_two_team_tie_resolved_by_head_to_head_points():
    # A and B tied on overall points (3 each), but A beat B head-to-head.
    matches = [_match("A", "B", 2, 1), _match("A", "C", 0, 3), _match("B", "C", 0, 3)]
    aggregates = {"A": _agg(3, -1, 2), "B": _agg(3, -2, 1), "C": _agg(6, 3, 6)}
    result = break_ties(["A", "B", "C"], matches, aggregates, {}, {})
    assert result == [("C", "points"), ("A", "head_to_head_points"), ("B", "head_to_head_points")]


def test_two_team_tie_falls_through_to_overall_goal_diff_when_head_to_head_drawn():
    # A and B drew their head-to-head match, so h2h can't separate them;
    # overall goal difference (from their other matches) must decide.
    matches = [_match("A", "B", 1, 1)]
    aggregates = {"A": _agg(4, 3, 5), "B": _agg(4, 1, 4)}
    result = break_ties(["A", "B"], matches, aggregates, {}, {})
    assert result == [("A", "overall_goal_diff"), ("B", "overall_goal_diff")]


def test_falls_through_to_overall_goals_for_when_goal_diff_also_tied():
    matches = [_match("A", "B", 1, 1)]
    aggregates = {"A": _agg(4, 2, 5), "B": _agg(4, 2, 3)}
    result = break_ties(["A", "B"], matches, aggregates, {}, {})
    assert result == [("A", "overall_goals_for"), ("B", "overall_goals_for")]


def test_falls_through_to_conduct_score_when_goals_also_tied():
    matches = [_match("A", "B", 1, 1)]
    aggregates = {"A": _agg(4, 2, 5), "B": _agg(4, 2, 5)}
    conduct = {"A": 1, "B": 3}  # fewer disciplinary points wins
    result = break_ties(["A", "B"], matches, aggregates, conduct, {})
    assert result == [("A", "conduct_score"), ("B", "conduct_score")]


def test_falls_through_to_fifa_rank_when_conduct_also_tied():
    matches = [_match("A", "B", 1, 1)]
    aggregates = {"A": _agg(4, 2, 5), "B": _agg(4, 2, 5)}
    conduct = {"A": 2, "B": 2}
    fifa_ranks = {"A": 12, "B": 3}  # lower (better) rank wins
    result = break_ties(["A", "B"], matches, aggregates, conduct, fifa_ranks)
    assert result == [("B", "fifa_rank"), ("A", "fifa_rank")]


def test_unresolved_when_every_criterion_is_exhausted():
    matches = [_match("A", "B", 1, 1)]
    aggregates = {"A": _agg(4, 2, 5), "B": _agg(4, 2, 5)}
    result = break_ties(["A", "B"], matches, aggregates, {"A": 2, "B": 2}, {"A": None, "B": None})
    assert result == [("A", "unresolved"), ("B", "unresolved")]


def test_four_team_partial_head_to_head_resolution_recurses_on_remaining_pair():
    # Full round robin among A, B, C, D. B beat C 2-0 head-to-head, but B
    # and C still end up with identical overall points/GD/GF (4/0/2 each)
    # because their results against A and D exactly offset that match --
    # so the *first* head-to-head pass (scoped to all 4 teams) cannot
    # separate them either; only recursing into just {B, C}'s own match
    # resolves it. D and A are already cleanly separated by overall
    # points and don't need head-to-head at all.
    matches = [
        _match("B", "C", 2, 0),
        _match("B", "A", 0, 0),
        _match("D", "B", 2, 0),
        _match("C", "A", 2, 0),
        _match("C", "D", 0, 0),
        _match("A", "D", 0, 0),
    ]
    aggregates = {
        "D": _agg(5, 2, 2),
        "B": _agg(4, 0, 2),
        "C": _agg(4, 0, 2),
        "A": _agg(2, -2, 0),
    }
    result = break_ties(["A", "B", "C", "D"], matches, aggregates, {}, {})
    assert result == [
        ("D", "points"),
        ("B", "head_to_head_points"),
        ("C", "head_to_head_points"),
        ("A", "points"),
    ]


def test_break_ties_is_order_independent():
    matches = [_match("A", "B", 2, 1), _match("A", "C", 0, 3), _match("B", "C", 0, 3)]
    aggregates = {"A": _agg(3, -1, 2), "B": _agg(3, -2, 1), "C": _agg(6, 3, 6)}
    forward = break_ties(["A", "B", "C"], matches, aggregates, {}, {})
    backward = break_ties(["C", "B", "A"], matches, aggregates, {}, {})
    assert forward == backward


def test_compute_conduct_scores_weights_red_cards_higher_than_yellow():
    matches = [
        _match("A", "B", 1, 0, hy=2, ay=1, hr=0, ar=1),
        _match("A", "C", 1, 1, hy=1, ay=0),
    ]
    scores = compute_conduct_scores(matches)
    assert scores["A"] == 2 * 1 + 1 * 1  # 2 yellows in game 1, 1 yellow in game 2
    assert scores["B"] == 1 * 1 + 1 * 4  # 1 yellow + 1 red
    assert scores["C"] == 0
