"""Predicted starting-XI builder for display purposes (e.g. a squad/lineup API
endpoint). Slot assignment is delegated to
app.engine.lineup_selection.select_starting_assignments(), the *same* selector
the match simulator uses, so the displayed likely XI is always identical to the
XI that gets simulated. (This module then just formats the assignment as
display dicts.)
"""

from app.engine.formations import FORMATIONS
from app.engine.lineup_selection import lineup_score, select_starting_assignments


def build_likely_lineup(players: list[dict], formation_name: str) -> list[dict]:
    """`players` is a team's full roster in the same dict shape
    app.api.matches.team_players_as_dicts() produces (snake_case: id/name/
    name_ja/primary_position/secondary_positions/overall/attributes), where
    attributes may hold "startingProbability"; falls back to `overall` if
    absent. Returns one entry per formation slot, in formation order,
    skipped if the squad has fewer than 11 fielders for that slot."""
    formation = FORMATIONS[formation_name]
    assignments = select_starting_assignments(players, formation_name)

    lineup = []
    for idx, slot in enumerate(formation.slots):
        p = assignments.get(idx)
        if p is None:
            continue
        lineup.append({
            "slot_position": slot.position,
            "player_id": p["id"],
            "name": p["name"],
            "name_ja": p.get("name_ja"),
            "primary_position": p["primary_position"],
            "starting_probability": lineup_score(p),
        })
    return lineup
