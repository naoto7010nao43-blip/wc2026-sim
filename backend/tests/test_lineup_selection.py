"""Guards the invariant that the simulated XI equals the displayed likely XI.

Both app.engine.state.build_team_state (simulator) and
app.rating_v2.lineup_builder.build_likely_lineup (display) must assign players
via the shared app.engine.lineup_selection selector, scored by real-world
starting likelihood (startingProbability, falling back to overall). These once
diverged -- the simulator picked by raw overall -- so sourced real starters
(e.g. a confirmed No.1 goalkeeper) showed in the lineup yet were benched in the
actual simulation. Keep them consistent.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.state import build_team_state
from app.rating_v2.lineup_builder import build_likely_lineup


def _player(pid, pos, overall, starting_probability=None, secondary=None):
    attrs = {}
    if starting_probability is not None:
        attrs["startingProbability"] = starting_probability
    return {
        "id": pid,
        "name": pid,
        "name_ja": None,
        "primary_position": pos,
        "secondary_positions": secondary or [],
        "overall": overall,
        "attributes": attrs,
        "stamina_max": 90,
    }


def _roster():
    """A full 4-3-3 with a couple of deliberate overall-vs-startingProbability
    conflicts (a lower-overall No.1 keeper, and a lower-overall real winger)."""
    return [
        _player("GK_NO1", "GK", overall=70, starting_probability=85),
        _player("GK_BACKUP", "GK", overall=78, starting_probability=20),  # stronger but a backup
        _player("CB1", "CB", 75, 80),
        _player("CB2", "CB", 74, 78),
        _player("LB1", "LB", 73, 80),
        _player("RB1", "RB", 72, 80),
        _player("CM1", "CM", 76, 82),
        _player("CM2", "CM", 75, 80),
        _player("CM3", "CM", 74, 78),
        _player("LW_REAL", "LW", overall=71, starting_probability=82),
        _player("LW_STRONGER_SUB", "LW", overall=79, starting_probability=25),  # stronger but benched
        _player("ST1", "ST", 77, 82),
        _player("RW1", "RW", 73, 80),
    ]


def test_simulator_fields_the_real_number_one_keeper_not_the_highest_overall():
    team = build_team_state("T", _roster(), "4-3-3", attacking_direction=1)
    assert team.goalkeeper().player_id == "GK_NO1"
    assert "GK_BACKUP" in {p["id"] for p in team.bench}


def test_simulator_prefers_the_real_starter_winger_over_a_stronger_substitute():
    team = build_team_state("T", _roster(), "4-3-3", attacking_direction=1)
    fielded = {p.player_id for p in team.lineup}
    assert "LW_REAL" in fielded
    assert "LW_STRONGER_SUB" not in fielded


def test_simulated_xi_is_identical_to_the_displayed_likely_xi():
    roster = _roster()
    displayed = [d["player_id"] for d in build_likely_lineup(roster, "4-3-3")]
    simulated = [p.player_id for p in build_team_state("T", roster, "4-3-3", 1).lineup]
    assert simulated == displayed
    assert len(simulated) == 11


def test_falls_back_to_overall_when_no_starting_probability_is_present():
    # Uniform overall, no startingProbability -> still fields a full XI (the
    # pre-existing overall-only behaviour is preserved as the fallback).
    roster = [_player(f"P{i}", pos, overall=70) for i, pos in enumerate(
        ["GK", "GK", "CB", "CB", "LB", "RB", "CM", "CM", "CM", "LW", "ST", "RW"])]
    team = build_team_state("T", roster, "4-3-3", attacking_direction=1)
    assert len(team.lineup) == 11
    assert team.goalkeeper().primary_position == "GK"
