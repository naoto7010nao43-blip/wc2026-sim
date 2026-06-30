"""Orchestrates a full 48-team World Cup tournament end to end: 12-group
round robin, third-place ranking, Round of 32 bracket construction (via
app.engine.bracket), and the R32->Final knockout tree.

Fixtures with no real-world result yet are resolved via the Poisson
statistical prediction model (app.prediction.poisson_model), not the old
minute-by-minute micro-simulator -- see app.services.predicted_match.
"""

import itertools

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.bracket import R32_TEMPLATE, assign_third_place_slots, next_round_pairs
from app.models.match import Match
from app.models.team import Team
from app.schemas.match import SimulateMatchRequest
from app.schemas.standings import StandingsRow
from app.services.predicted_match import run_and_persist_predicted_match
from app.services.real_results import (
    load_real_knockout_results,
    load_real_results,
    persist_real_match,
)
from app.services.standings import compute_standings
from app.services.third_place import rank_third_place_teams

GROUP_LETTERS = list("ABCDEFGHIJKL")


def _group_team_ids(db: Session, group_id: str) -> list[str]:
    teams = db.scalars(select(Team).where(Team.group_id == group_id)).all()
    return [t.id for t in teams]


def _resolve_slot(
    slot: str,
    group_standings: dict[str, list[StandingsRow]],
    third_place_team_by_group: dict[str, str],
    third_place_assignment: dict[str, str],
) -> str:
    if slot.startswith("3RD:"):
        winner_slot = slot.removeprefix("3RD:")
        source_group = third_place_assignment[winner_slot]
        return third_place_team_by_group[source_group]
    group_letter, position = slot[0], int(slot[1])
    return group_standings[group_letter][position - 1].team_id


def match_winner(match: Match) -> str:
    if match.home_score != match.away_score:
        return match.home_team_id if match.home_score > match.away_score else match.away_team_id
    return match.home_team_id if match.penalty_home_score > match.penalty_away_score else match.away_team_id


def match_loser(match: Match) -> str:
    winner = match_winner(match)
    return match.away_team_id if winner == match.home_team_id else match.home_team_id


def run_full_tournament(db: Session, base_seed: int = 0) -> dict:
    seed_counter = itertools.count(base_seed)

    def play(home_team_id: str, away_team_id: str, *, group_id: str | None = None, round: str, bracket_slot: str | None = None, allow_draw: bool = True) -> Match:
        req = SimulateMatchRequest(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            seed=next(seed_counter),
            group_id=group_id,
            round=round,
            bracket_slot=bracket_slot,
            allow_draw=allow_draw,
        )
        return run_and_persist_predicted_match(db, req)

    # Already-played knockout fixtures (R32 onward) use their researched real
    # result; everything else is predicted. Keyed by team-pair frozenset.
    real_knockout = load_real_knockout_results()

    def play_knockout(home_id: str, away_id: str, *, round: str, bracket_slot: str) -> Match:
        real = real_knockout.get(frozenset({home_id, away_id}))
        if real is not None and real.get("round") == round:
            return persist_real_match(
                db, real["home_team_id"], real["away_team_id"], real,
                round=round, bracket_slot=bracket_slot,
            )
        return play(home_id, away_id, round=round, bracket_slot=bracket_slot, allow_draw=False)

    # 1. Group stage: round robin within each of the 12 groups. Fixtures
    # that have already been played in the real 2026 World Cup use the
    # researched real result instead of the simulator (see real_results.py).
    real_results_by_group = load_real_results()
    group_matches: dict[str, list[Match]] = {}
    for letter in GROUP_LETTERS:
        team_ids = _group_team_ids(db, letter)
        if len(team_ids) != 4:
            raise ValueError(f"Group {letter} does not have exactly 4 teams (found {len(team_ids)})")
        real_results = real_results_by_group.get(letter, {})
        matches = []
        for home_id, away_id in itertools.combinations(team_ids, 2):
            real_result = real_results.get(frozenset({home_id, away_id}))
            if real_result is not None:
                matches.append(persist_real_match(db, real_result["home_team_id"], real_result["away_team_id"], real_result, group_id=letter))
            else:
                matches.append(play(home_id, away_id, group_id=letter, round="group"))
        group_matches[letter] = matches

    group_standings: dict[str, list[StandingsRow]] = {letter: compute_standings(db, letter) for letter in GROUP_LETTERS}

    # 2. Best 8 third-placed teams across all 12 groups, per FIFA's official
    # third-place ranking cascade (points -> GD -> GF -> conduct -> FIFA rank).
    third_place_rows = {letter: standings[2] for letter, standings in group_standings.items()}
    third_place_rankings = rank_third_place_teams(third_place_rows)
    qualifying_rankings = [r for r in third_place_rankings if r.qualified]
    qualifying_third_groups = [r.group_id for r in qualifying_rankings]
    third_place_team_by_group = {r.group_id: r.team_id for r in qualifying_rankings}
    third_place_assignment = assign_third_place_slots(qualifying_third_groups)

    # 3. Round of 32.
    r32_matches = []
    for i, (slot_a, slot_b) in enumerate(R32_TEMPLATE):
        home_id = _resolve_slot(slot_a, group_standings, third_place_team_by_group, third_place_assignment)
        away_id = _resolve_slot(slot_b, group_standings, third_place_team_by_group, third_place_assignment)
        r32_matches.append(play_knockout(home_id, away_id, round="R32", bracket_slot=f"R32_{i + 1}"))

    def play_next_round(prev_matches: list[Match], round_name: str) -> list[Match]:
        winners = [match_winner(m) for m in prev_matches]
        pairs = next_round_pairs(winners)
        return [
            play_knockout(home_id, away_id, round=round_name, bracket_slot=f"{round_name}_{i + 1}")
            for i, (home_id, away_id) in enumerate(pairs)
        ]

    # 4. R16 -> QF -> SF.
    r16_matches = play_next_round(r32_matches, "R16")
    qf_matches = play_next_round(r16_matches, "QF")
    sf_matches = play_next_round(qf_matches, "SF")

    # 5. Third place match + Final.
    sf_winners = [match_winner(m) for m in sf_matches]
    sf_losers = [match_loser(m) for m in sf_matches]
    third_place_match = play_knockout(sf_losers[0], sf_losers[1], round="THIRD_PLACE", bracket_slot="THIRD_PLACE")
    final_match = play_knockout(sf_winners[0], sf_winners[1], round="FINAL", bracket_slot="FINAL")

    return {
        "champion_team_id": match_winner(final_match),
        "qualifying_third_groups": qualifying_third_groups,
        "third_place_assignment": third_place_assignment,
        "group_standings": group_standings,
        "matches": {
            "group": [m for ms in group_matches.values() for m in ms],
            "R32": r32_matches,
            "R16": r16_matches,
            "QF": qf_matches,
            "SF": sf_matches,
            "THIRD_PLACE": [third_place_match],
            "FINAL": [final_match],
        },
    }
