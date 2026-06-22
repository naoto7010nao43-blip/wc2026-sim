"""WhoScored/Sofascore-style 0-10 per-player match ratings, computed purely
from the persisted MatchEvent rows (no engine/schema changes needed beyond
the roster name lookup already returned by simulate_match). Real-world
matches have far sparser events (often just goals), so ratings are only
computed for simulated matches with a populated roster.
"""

BASE_RATING = 6.0
MIN_RATING = 3.0
MAX_RATING = 10.0

EVENT_DELTAS = {
    "goal": 1.4,
    "key_pass": 0.25,
    "yellow_card": -0.4,
}


def _clamp(value: float) -> float:
    return max(MIN_RATING, min(MAX_RATING, value))


def compute_player_ratings(
    events: list[dict],
    home_roster: dict[str, str],
    away_roster: dict[str, str],
    home_team_id: str,
    away_team_id: str,
) -> list[dict]:
    """Returns a list of {player_id, name, team_id, rating, is_mom} for every
    player who appeared (starters + substitutes), sorted by rating
    descending. Empty if there's no roster to attribute events to (e.g. a
    real-world result with no simulated lineup)."""
    if not home_roster and not away_roster:
        return []

    team_by_player: dict[str, str] = {}
    for pid in home_roster:
        team_by_player[pid] = home_team_id
    for pid in away_roster:
        team_by_player[pid] = away_team_id

    deltas: dict[str, float] = {pid: 0.0 for pid in team_by_player}
    goals: dict[str, int] = {pid: 0 for pid in team_by_player}

    def add(pid: str | None, amount: float) -> None:
        if pid in deltas:
            deltas[pid] += amount

    for e in events:
        event_type = e["event_type"]
        pid = e.get("player_id")
        secondary = e.get("secondary_player_id")

        if event_type in EVENT_DELTAS:
            add(pid, EVENT_DELTAS[event_type])
            if event_type == "goal" and pid in goals:
                goals[pid] += 1
        elif event_type == "tackle":
            # Tackle events: team_id is the defending side; player_id is the
            # tackler (credit), secondary_player_id is the dispossessed
            # attacker (small penalty). This engine logs a tackle event for
            # nearly every failed pass/dribble, so per-event weight must stay
            # small -- a busy defender easily racks up 5-10 of these.
            add(pid, 0.08)
            add(secondary, -0.08)
        elif event_type == "shot":
            outcome = (e.get("event_metadata") or {}).get("outcome")
            add(pid, 0.03 if outcome == "saved" else -0.03)
            if outcome == "saved" and secondary in deltas:
                add(secondary, 0.15)  # goalkeeper credit for the save
        elif event_type == "penalty_kick":
            scored = (e.get("event_metadata") or {}).get("scored")
            if scored:
                add(pid, EVENT_DELTAS["goal"])
                if pid in goals:
                    goals[pid] += 1
            else:
                add(pid, -0.2)  # missed a big chance
                if secondary in deltas:
                    add(secondary, 0.15)  # goalkeeper credit for the save

    ratings = [
        {
            "player_id": pid,
            "name": home_roster.get(pid) or away_roster.get(pid) or pid,
            "team_id": team_by_player[pid],
            "rating": round(_clamp(BASE_RATING + delta), 1),
            "goals": goals.get(pid, 0),
        }
        for pid, delta in deltas.items()
    ]
    ratings.sort(key=lambda r: (-r["rating"], -r["goals"]))

    for i, r in enumerate(ratings):
        r["is_mom"] = i == 0
        del r["goals"]

    return ratings


def estimate_real_match_ratings(events: list[dict]) -> list[dict]:
    """Real-world matches have no full lineup data (see real_results.py), so
    a full-squad rating like compute_player_ratings would be fabricated. This
    instead rates only the confirmed goal scorers from the persisted events,
    clearly flagged is_estimated, using the same baseline+bonus shape as the
    simulated formula. Own goals are excluded since the scoring event's
    player belongs to the *other* team and can't be cleanly credited."""
    goal_counts: dict[tuple[str, str], int] = {}
    for e in events:
        if e["event_type"] != "goal":
            continue
        name = e["description"]
        if name.endswith(" がゴール!"):
            name = name[: -len(" がゴール!")]
        if "own goal" in name.lower() or "オウンゴール" in name:
            continue
        key = (e["team_id"], name)
        goal_counts[key] = goal_counts.get(key, 0) + 1

    if not goal_counts:
        return []

    ratings = [
        {
            "player_id": f"real:{team_id}:{name}",
            "name": name,
            "team_id": team_id,
            "rating": round(min(9.5, BASE_RATING + 1.0 + 0.6 * (goals - 1)), 1),
            "goals": goals,
            "is_estimated": True,
        }
        for (team_id, name), goals in goal_counts.items()
    ]
    ratings.sort(key=lambda r: (-r["rating"], -r["goals"]))
    for i, r in enumerate(ratings):
        r["is_mom"] = i == 0
        del r["goals"]
    return ratings
