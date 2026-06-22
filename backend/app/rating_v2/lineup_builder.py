"""Predicted starting-XI builder for display purposes (e.g. a squad/
lineup API endpoint) -- NOT used by the match simulator engine. Deliberately
kept separate from app/engine/state.py's build_team_state(), which already
does live, in-match slot assignment scored by `overall`; this module reuses
only the *static* formation data from app.engine.formations (read-only) and
scores candidates by `startingProbability` instead, so the two stay
independent and changes here can't affect simulated match outcomes.
"""

from app.engine.formations import FORMATIONS, SLOT_POSITION_ALIASES


def build_likely_lineup(players: list[dict], formation_name: str) -> list[dict]:
    """`players` is a team's full roster in the same dict shape
    app.api.matches.team_players_as_dicts() produces (snake_case: id/name/
    name_ja/primary_position/secondary_positions/overall/attributes), where
    attributes may hold "startingProbability"; falls back to `overall` if
    absent. Returns one entry per formation slot, in formation order,
    skipped if the squad has fewer than 11 fielders for that slot."""
    formation = FORMATIONS[formation_name]
    available = list(players)
    used_ids: set[str] = set()
    assignments: dict[int, dict] = {}

    def _score(p: dict) -> float:
        starting_probability = (p.get("attributes") or {}).get("startingProbability")
        return starting_probability if starting_probability is not None else p.get("overall", 50)

    def pick(slot_idx: int, candidates: list[dict]) -> None:
        candidates = [p for p in candidates if p["id"] not in used_ids]
        if not candidates:
            return
        best = max(candidates, key=_score)
        assignments[slot_idx] = best
        used_ids.add(best["id"])

    for idx, slot in enumerate(formation.slots):
        exact = [p for p in available if p["primary_position"] == slot.position]
        pick(idx, exact)

    for idx, slot in enumerate(formation.slots):
        if idx in assignments:
            continue
        aliases = SLOT_POSITION_ALIASES.get(slot.position, [slot.position])
        candidates = [
            p for p in available
            if p["primary_position"] in aliases or any(sp in aliases for sp in p.get("secondary_positions", []))
        ]
        pick(idx, candidates)

    for idx, slot in enumerate(formation.slots):
        if idx in assignments:
            continue
        pick(idx, available)

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
            "starting_probability": _score(p),
        })
    return lineup
