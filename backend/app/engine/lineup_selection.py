"""Single source of truth for *who starts*: assigns a roster to formation
slots scored by real-world starting likelihood.

Both the match simulator (app.engine.state.build_team_state) and the display
lineup builder (app.rating_v2.lineup_builder.build_likely_lineup) call this,
so the XI the site *shows* is always exactly the XI it *simulates*. They used
to diverge -- the simulator picked by raw `overall` while the display picked by
`startingProbability` -- which meant sourced real starters (e.g. a confirmed
No.1 goalkeeper, or an added winger) appeared in the shown lineup but were
silently benched in the actual simulation. Scoring both off the same
`startingProbability` (falling back to `overall`) keeps them consistent.
"""

from app.engine.formations import FORMATIONS, SLOT_POSITION_ALIASES


def lineup_score(player: dict) -> float:
    """Real-world starting likelihood for slot assignment: the player's
    `attributes.startingProbability` if present, else their `overall`."""
    starting_probability = (player.get("attributes") or {}).get("startingProbability")
    return starting_probability if starting_probability is not None else player.get("overall", 50)


def select_starting_assignments(players: list[dict], formation_name: str) -> dict[int, dict]:
    """Assign up to 11 players from `players` to the slots of the named
    formation, returning {slot_index: player_dict}. Players are the dict shape
    app.api.matches.team_players_as_dicts() produces (id/name/primary_position/
    secondary_positions/overall/attributes/...). Highest `lineup_score` wins
    each slot, over three passes: exact primary-position match, then aliased
    (primary or secondary) match, then a last-resort fallback. Goalkeepers and
    outfielders are kept in strictly separate pools so a backup keeper can
    never fill an outfield slot (nor an outfielder the GK slot) even with a
    thin roster."""
    formation = FORMATIONS[formation_name]
    available = list(players)
    used_ids: set[str] = set()
    assignments: dict[int, dict] = {}

    def _is_gk(p: dict) -> bool:
        return p["primary_position"] == "GK"

    def _slot_pool(slot_position: str) -> list[dict]:
        want_gk = slot_position == "GK"
        return [p for p in available if _is_gk(p) == want_gk]

    def pick(slot_idx: int, candidates: list[dict]) -> None:
        candidates = [p for p in candidates if p["id"] not in used_ids]
        if not candidates:
            return
        best = max(candidates, key=lineup_score)
        assignments[slot_idx] = best
        used_ids.add(best["id"])

    # Pass 1: exact primary-position match.
    for idx, slot in enumerate(formation.slots):
        exact = [p for p in _slot_pool(slot.position) if p["primary_position"] == slot.position]
        pick(idx, exact)

    # Pass 2: alias positions (primary or secondary).
    for idx, slot in enumerate(formation.slots):
        if idx in assignments:
            continue
        aliases = SLOT_POSITION_ALIASES.get(slot.position, [slot.position])
        candidates = [
            p for p in _slot_pool(slot.position)
            if p["primary_position"] in aliases or any(sp in aliases for sp in p.get("secondary_positions", []))
        ]
        pick(idx, candidates)

    # Pass 3: fallback -- any remaining unused player of the right kind.
    for idx, slot in enumerate(formation.slots):
        if idx in assignments:
            continue
        pick(idx, _slot_pool(slot.position))

    return assignments
