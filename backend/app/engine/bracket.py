"""Round of 32 bracket construction for the 48-team / 12-group format.

Structural facts below (the fixed winner-vs-runner-up cross pairs, the 8
group winners who face a third-placed team, each of those 8 slots'
candidate pool of groups, and the full R32->Final bracket tree) come
directly from FIFA's official Round of 32 bracket diagram.

The exact 495-row "Annex C" table that pins down precisely which
third-placed team fills which slot for every one of the C(12,8)=495
possible combinations of 8 qualifying groups was NOT reproduced verbatim:
the source table images were too small to transcribe reliably (an attempt
produced an internally-contradictory row - the same group appearing
twice). Instead, `assign_third_place_slots` finds, for the actual 8
qualifying groups, a deterministic assignment that satisfies every slot's
confirmed candidate pool. This is structurally faithful to the official
rules (it can never produce an impossible pairing) but is not guaranteed
to reproduce FIFA's literal pick for every one of the 495 combinations.
"""

from itertools import permutations
from typing import TypeVar

FIXED_CROSS_PAIRS: list[tuple[str, str]] = [
    ("C1", "F2"),
    ("F1", "C2"),
    ("H1", "J2"),
    ("J1", "H2"),
    ("A2", "B2"),
    ("E2", "I2"),
    ("D2", "G2"),
    ("K2", "L2"),
]

THIRD_PLACE_SLOTS: list[str] = ["A1", "B1", "D1", "E1", "G1", "I1", "K1", "L1"]

THIRD_PLACE_CANDIDATE_POOLS: dict[str, set[str]] = {
    "A1": {"C", "E", "F", "H", "I"},
    "B1": {"E", "F", "G", "I", "J"},
    "D1": {"B", "E", "F", "I", "J"},
    "E1": {"A", "B", "C", "D", "F"},
    "G1": {"A", "E", "H", "I", "J"},
    "I1": {"C", "D", "F", "G", "H"},
    "K1": {"D", "E", "I", "J", "L"},
    "L1": {"E", "H", "I", "J", "K"},
}

# R32 match order (left half, then right half), matching the official
# bracket diagram. Each tuple is (slot_a, slot_b); a slot of the form
# "3RD:<winner_slot>" means "whichever group's 3rd place team was
# assigned to that winner_slot".
R32_TEMPLATE: list[tuple[str, str]] = [
    ("E1", "3RD:E1"),
    ("I1", "3RD:I1"),
    ("A2", "B2"),
    ("F1", "C2"),
    ("K2", "L2"),
    ("H1", "J2"),
    ("D1", "3RD:D1"),
    ("G1", "3RD:G1"),
    ("C1", "F2"),
    ("E2", "I2"),
    ("A1", "3RD:A1"),
    ("L1", "3RD:L1"),
    ("J1", "H2"),
    ("D2", "G2"),
    ("B1", "3RD:B1"),
    ("K1", "3RD:K1"),
]

T = TypeVar("T")

# Curated rows of FIFA's Annex C table for combinations whose real-world
# assignment has been confirmed against the published bracket. Keyed by the
# sorted tuple of the 8 qualifying group letters. The generic candidate-pool
# search below can pick a *different* valid permutation than FIFA's literal
# table, so for combinations that have actually occurred we pin the real one
# to reproduce the genuine bracket. Each row is verified to satisfy every
# slot's THIRD_PLACE_CANDIDATE_POOLS entry.
#
# ("B","D","E","F","I","J","K","L") is the real 2026 World Cup qualifying
# third-place set; this row reproduces the actual Round of 32 (GER-PAR,
# USA-BIH, BEL-SEN, MEX-ECU, FRA-SWE, SUI-ALG, ENG-COD, COL-GHA), confirmed
# against the Wikipedia 2026 FIFA World Cup knockout-stage bracket.
FIFA_THIRD_PLACE_TABLE: dict[tuple[str, ...], dict[str, str]] = {
    ("B", "D", "E", "F", "I", "J", "K", "L"): {
        "A1": "E", "B1": "J", "D1": "B", "E1": "D",
        "G1": "I", "I1": "F", "K1": "L", "L1": "K",
    },
}


def assign_third_place_slots(qualifying_groups: list[str]) -> dict[str, str]:
    """Given exactly 8 distinct qualifying group letters, return a mapping
    from each of the 8 THIRD_PLACE_SLOTS to one qualifying group, such that
    every slot's confirmed candidate pool is respected.

    If the combination appears in FIFA_THIRD_PLACE_TABLE, that confirmed
    real-world assignment is returned. Otherwise falls back to a
    deterministic search: the qualifying groups are sorted first, and the
    lexicographically-first valid permutation is returned.
    """
    groups = sorted(qualifying_groups)
    if len(groups) != 8 or len(set(groups)) != 8:
        raise ValueError(f"Expected exactly 8 distinct qualifying groups, got {qualifying_groups}")

    pinned = FIFA_THIRD_PLACE_TABLE.get(tuple(groups))
    if pinned is not None:
        return dict(pinned)

    for perm in permutations(groups):
        assignment = dict(zip(THIRD_PLACE_SLOTS, perm))
        if all(assignment[slot] in THIRD_PLACE_CANDIDATE_POOLS[slot] for slot in THIRD_PLACE_SLOTS):
            return assignment

    raise ValueError(f"No valid third-place slot assignment exists for groups {groups}")


def next_round_pairs(prev_round_results: list[T]) -> list[tuple[T, T]]:
    """Pair up consecutive results from one round to form the next round's
    matchups (R32->R16, R16->QF, QF->SF, SF->Final), per the bracket tree."""
    if len(prev_round_results) % 2 != 0:
        raise ValueError("Expected an even number of results to pair up")
    return [(prev_round_results[i], prev_round_results[i + 1]) for i in range(0, len(prev_round_results), 2)]
