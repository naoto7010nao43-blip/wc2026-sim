import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.standings import StandingsRow
from app.services.third_place import rank_third_place_teams


def _row(team_id: str, points: int, goal_diff: int, goals_for: int, conduct_score: int = 0, fifa_rank: int | None = None) -> StandingsRow:
    return StandingsRow(
        team_id=team_id,
        team_name=team_id,
        played=3,
        won=0,
        drawn=0,
        lost=0,
        goals_for=goals_for,
        goals_against=goals_for - goal_diff,
        goal_diff=goal_diff,
        points=points,
        conduct_score=conduct_score,
        fifa_rank=fifa_rank,
        tiebreak_reason="points",
    )


def _twelve_groups(overrides: dict[str, StandingsRow]) -> dict[str, StandingsRow]:
    letters = list("ABCDEFGHIJKL")
    rows = {letter: _row(f"team_{letter}", 1, 0, 1) for letter in letters}
    rows.update(overrides)
    return rows


def test_top_8_of_12_qualify_by_points():
    rows = _twelve_groups({
        "A": _row("team_A", 7, 5, 6),
        "B": _row("team_B", 6, 4, 5),
        "C": _row("team_C", 5, 3, 4),
        "D": _row("team_D", 4, 2, 3),
        "E": _row("team_E", 4, 1, 3),
        "F": _row("team_F", 4, 0, 3),
        "G": _row("team_G", 4, -1, 2),
        "H": _row("team_H", 4, -2, 2),
        # I, J, K, L stay at the default points=1 (clearly eliminated)
    })
    ranking = rank_third_place_teams(rows)
    qualified = [r.group_id for r in ranking if r.qualified]
    assert qualified == ["A", "B", "C", "D", "E", "F", "G", "H"]
    assert len(ranking) == 12
    assert all(not r.qualified for r in ranking if r.group_id not in qualified)


def test_third_place_ties_resolved_by_overall_goal_diff_not_head_to_head():
    # Two third-placed teams from different groups never played each
    # other, so even though their group_id "labels" might look comparable,
    # there is no head-to-head step -- ties go straight to overall GD.
    rows = _twelve_groups({
        "A": _row("team_A", 5, 3, 5),
        "B": _row("team_B", 5, 1, 5),
    })
    ranking = rank_third_place_teams(rows)
    a = next(r for r in ranking if r.group_id == "A")
    b = next(r for r in ranking if r.group_id == "B")
    assert ranking.index(a) < ranking.index(b)
    assert a.tiebreak_reason == "overall_goal_diff"


def test_third_place_tie_resolved_by_conduct_then_fifa_rank():
    rows = _twelve_groups({
        "A": _row("team_A", 5, 2, 4, conduct_score=2, fifa_rank=20),
        "B": _row("team_B", 5, 2, 4, conduct_score=2, fifa_rank=5),
    })
    ranking = rank_third_place_teams(rows)
    a = next(r for r in ranking if r.group_id == "A")
    b = next(r for r in ranking if r.group_id == "B")
    # Conduct ties (2 == 2), so FIFA rank (lower is better) decides: B first.
    assert ranking.index(b) < ranking.index(a)
    assert b.tiebreak_reason == "fifa_rank"
