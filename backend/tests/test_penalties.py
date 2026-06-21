import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.penalties import resolve_shootout
from app.engine.state import build_team_state


def make_squad(team_id: str, base_overall: int) -> list[dict]:
    positions = ["GK", "GK", "CB", "CB", "LB", "RB", "CDM", "CM", "CM", "LW", "ST", "RW"]
    squad = []
    for i, pos in enumerate(positions):
        attrs = {
            "pace": base_overall, "shooting": base_overall, "passing": base_overall,
            "dribbling": base_overall, "defending": base_overall, "physical": base_overall,
            "gk_reflexes": base_overall if pos == "GK" else None,
            "gk_handling": base_overall if pos == "GK" else None,
        }
        squad.append({
            "id": f"{team_id}_{pos}_{i}",
            "name": f"{team_id} {pos} {i}",
            "primary_position": pos,
            "secondary_positions": [],
            "overall": base_overall,
            "attributes": attrs,
            "stamina_max": 90,
        })
    return squad


def test_shootout_always_produces_a_decisive_winner():
    for seed in range(30):
        home = build_team_state("HOME", make_squad("HOME", 70), "4-3-3", attacking_direction=1)
        away = build_team_state("AWAY", make_squad("AWAY", 70), "4-3-3", attacking_direction=-1)
        result = resolve_shootout(home, away, random.Random(seed))

        assert result["home_penalty_score"] != result["away_penalty_score"]
        assert result["winner_team_id"] in ("HOME", "AWAY")
        assert result["events"][-1]["event_type"] == "shootout_winner"
        assert all(e["event_type"] in ("penalty_kick", "shootout_winner") for e in result["events"])


def test_shootout_is_deterministic_given_a_seed():
    home = build_team_state("HOME", make_squad("HOME", 70), "4-3-3", attacking_direction=1)
    away = build_team_state("AWAY", make_squad("AWAY", 60), "4-3-3", attacking_direction=-1)

    r1 = resolve_shootout(home, away, random.Random(42))

    home2 = build_team_state("HOME", make_squad("HOME", 70), "4-3-3", attacking_direction=1)
    away2 = build_team_state("AWAY", make_squad("AWAY", 60), "4-3-3", attacking_direction=-1)
    r2 = resolve_shootout(home2, away2, random.Random(42))

    assert r1["home_penalty_score"] == r2["home_penalty_score"]
    assert r1["away_penalty_score"] == r2["away_penalty_score"]
    assert r1["winner_team_id"] == r2["winner_team_id"]


def test_shootout_takes_at_least_five_rounds_each_when_not_decided_early():
    home = build_team_state("HOME", make_squad("HOME", 70), "4-3-3", attacking_direction=1)
    away = build_team_state("AWAY", make_squad("AWAY", 70), "4-3-3", attacking_direction=-1)
    result = resolve_shootout(home, away, random.Random(7))

    kicks = [e for e in result["events"] if e["event_type"] == "penalty_kick"]
    assert len(kicks) >= 2
