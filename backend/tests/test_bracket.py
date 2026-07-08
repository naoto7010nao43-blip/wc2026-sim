import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.engine.bracket import (
    R32_TEMPLATE,
    THIRD_PLACE_CANDIDATE_POOLS,
    THIRD_PLACE_SLOTS,
    assign_third_place_slots,
    next_round_pairs,
)

ALL_GROUPS = list("ABCDEFGHIJKL")


def test_every_possible_8_of_12_combination_has_a_valid_assignment():
    for combo in combinations(ALL_GROUPS, 8):
        assignment = assign_third_place_slots(list(combo))
        assert set(assignment.keys()) == set(THIRD_PLACE_SLOTS)
        assert set(assignment.values()) == set(combo)
        for slot, group in assignment.items():
            assert group in THIRD_PLACE_CANDIDATE_POOLS[slot]


def test_assignment_rejects_wrong_sized_input():
    with pytest.raises(ValueError):
        assign_third_place_slots(["A", "B", "C"])
    with pytest.raises(ValueError):
        assign_third_place_slots(["A", "A", "B", "C", "D", "E", "F", "G"])


def test_r32_template_has_16_matches_covering_each_slot_once():
    flat = [slot for pair in R32_TEMPLATE for slot in pair]
    winner_slots = [s for s in flat if not s.startswith("3RD:")]
    third_place_refs = [s for s in flat if s.startswith("3RD:")]

    fixed_pair_slots = [
        "C1", "F2", "F1", "C2", "H1", "J2", "J1", "H2",
        "A2", "B2", "E2", "I2", "D2", "G2", "K2", "L2",
    ]

    assert len(R32_TEMPLATE) == 16
    # Every slot referenced exactly once: no team plays two R32 matches.
    assert len(winner_slots) == len(set(winner_slots))
    assert sorted(winner_slots) == sorted(set(fixed_pair_slots) | set(THIRD_PLACE_SLOTS))
    assert sorted(s.removeprefix("3RD:") for s in third_place_refs) == sorted(THIRD_PLACE_SLOTS)


def test_next_round_pairs_builds_the_knockout_tree():
    r32_winners = list(range(16))
    r16 = next_round_pairs(r32_winners, "R16")
    assert r16 == [(2, 3), (1, 0), (9, 8), (10, 11), (5, 4), (7, 6), (12, 13), (14, 15)]

    qf = next_round_pairs([f"r16_winner_{i}" for i in range(8)], "QF")
    assert qf == [
        ("r16_winner_1", "r16_winner_0"),
        ("r16_winner_4", "r16_winner_5"),
        ("r16_winner_2", "r16_winner_3"),
        ("r16_winner_6", "r16_winner_7"),
    ]

    sf = next_round_pairs([f"qf_winner_{i}" for i in range(4)])
    assert len(sf) == 2

    final = next_round_pairs([f"sf_winner_{i}" for i in range(2)])
    assert final == [("sf_winner_0", "sf_winner_1")]


def test_next_round_pairs_rejects_odd_length():
    with pytest.raises(ValueError):
        next_round_pairs([1, 2, 3])
