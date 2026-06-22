import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rating_v2.lineup_builder import build_likely_lineup


def _squad_for_442() -> list[dict]:
    """22 distinct players covering every slot of 4-4-2 twice over, so the
    builder has to actually choose between candidates rather than fill by
    default. Ids carry an occurrence index (e.g. CB1_0, CB2_0) so the two
    players sharing a role within the same "copy" are still distinguishable."""
    roles = ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "ST", "ST"]
    squad = []
    for copy in range(2):
        role_counts: dict[str, int] = {}
        for role in roles:
            role_counts[role] = role_counts.get(role, 0) + 1
            pid = f"{role}{role_counts[role]}_{copy}"
            squad.append({
                "id": pid,
                "name": pid,
                "name_ja": None,
                "primary_position": role,
                "secondary_positions": [],
                "overall": 70,
                "attributes": {"startingProbability": 80 if copy == 0 else 40},
                "stamina_max": 90,
            })
    return squad


def test_likely_lineup_fills_all_11_slots_for_a_full_squad():
    lineup = build_likely_lineup(_squad_for_442(), "4-4-2")
    assert len(lineup) == 11
    assert {slot["slot_position"] for slot in lineup} == {"GK", "LB", "CB", "RB", "LM", "CM", "RM", "ST"}


def test_likely_lineup_prefers_higher_starting_probability_over_raw_overall():
    lineup = build_likely_lineup(_squad_for_442(), "4-4-2")
    chosen_ids = {slot["player_id"] for slot in lineup}
    # Every "copy 0" player has startingProbability 80 vs copy 1's 40, despite
    # identical `overall` -- the higher-probability copy should be chosen
    # everywhere there's a direct choice between the two.
    assert all(pid.endswith("_0") for pid in chosen_ids)


def test_likely_lineup_never_double_books_a_player():
    lineup = build_likely_lineup(_squad_for_442(), "4-4-2")
    player_ids = [slot["player_id"] for slot in lineup]
    assert len(player_ids) == len(set(player_ids))


def test_likely_lineup_falls_back_to_overall_when_starting_probability_missing():
    squad = _squad_for_442()
    for p in squad:
        p["attributes"] = {}  # no startingProbability anywhere
        p["overall"] = 70
    squad[0]["overall"] = 95  # GK1_0 should now win purely on overall
    lineup = build_likely_lineup(squad, "4-4-2")
    gk_slot = next(slot for slot in lineup if slot["slot_position"] == "GK")
    assert gk_slot["player_id"] == "GK1_0"


def test_likely_lineup_skips_slots_with_no_eligible_player_left():
    # Exactly the 10 non-GK roles 4-4-2 needs, with no GK and no spare
    # outfield players to fall back to -- the GK slot should simply be
    # absent from the output rather than fielding a leftover outfielder.
    roles = ["LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "ST", "ST"]
    role_counts: dict[str, int] = {}
    squad = []
    for role in roles:
        role_counts[role] = role_counts.get(role, 0) + 1
        pid = f"{role}{role_counts[role]}"
        squad.append({
            "id": pid, "name": pid, "name_ja": None, "primary_position": role,
            "secondary_positions": [], "overall": 70, "attributes": {"startingProbability": 80},
            "stamina_max": 90,
        })
    lineup = build_likely_lineup(squad, "4-4-2")
    assert "GK" not in {slot["slot_position"] for slot in lineup}
    assert len(lineup) == 10
