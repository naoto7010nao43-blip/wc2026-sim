"""Derives a small, read-only "analysis" summary purely from data a
detailed-simulation match already produces (events, player ratings,
formations, tactical profiles). Never invents new facts -- if a signal
isn't cleanly derivable from existing fields (e.g. true shot-quality xG),
it is left out rather than approximated into something that looks more
precise than it is.
"""

ATTACKING_EVENT_TYPES = {"shot", "goal"}
SEGMENT_LENGTH_MINUTES = 15
MAX_MATCH_MINUTE = 120  # covers extra time; stoppage-time events still fall in the last bucket


def _scoring_events(events: list[dict]) -> list[dict]:
    scoring = []
    for e in events:
        if e["event_type"] == "goal":
            scoring.append(e)
        elif e["event_type"] == "penalty_kick" and (e.get("event_metadata") or {}).get("scored"):
            scoring.append(e)
    return sorted(scoring, key=lambda e: e["minute"])


def compute_turning_point(events: list[dict], home_team_id: str, away_team_id: str) -> dict | None:
    """The goal that most recently changed who's leading (or tied the
    match) -- i.e. the last lead-change goal. Falls back to the only goal
    in a 1-goal match. None if the match has no goals at all."""
    scoring = _scoring_events(events)
    if not scoring:
        return None

    home_score = away_score = 0
    leader = None
    last_change = None
    for e in scoring:
        if e["team_id"] == home_team_id:
            home_score += 1
        elif e["team_id"] == away_team_id:
            away_score += 1
        new_leader = home_team_id if home_score > away_score else away_team_id if away_score > home_score else "tie"
        if new_leader != leader:
            last_change = e
            leader = new_leader

    chosen = last_change or scoring[-1]
    return {
        "minute": chosen["minute"],
        "team_id": chosen["team_id"],
        "description": chosen.get("description") or f"{chosen['minute']}分の得点",
    }


def compute_momentum_segments(
    events: list[dict],
    home_team_id: str,
    away_team_id: str,
    segment_length: int = SEGMENT_LENGTH_MINUTES,
    max_minute: int = MAX_MATCH_MINUTE,
) -> list[dict]:
    """Buckets attacking actions (shots + goals) into fixed time windows so
    the dominant side per phase of the match is visible without claiming
    any shot-quality (xG) precision the data doesn't support."""
    attacking = [e for e in events if e["event_type"] in ATTACKING_EVENT_TYPES]
    if not attacking:
        return []

    last_minute = max(e["minute"] for e in attacking)
    last_minute = min(last_minute, max_minute)
    segments = []
    start = 0
    while start <= last_minute:
        end = start + segment_length
        home_actions = sum(1 for e in attacking if e["team_id"] == home_team_id and start <= e["minute"] < end)
        away_actions = sum(1 for e in attacking if e["team_id"] == away_team_id and start <= e["minute"] < end)
        if home_actions or away_actions:
            dominant = home_team_id if home_actions > away_actions else away_team_id if away_actions > home_actions else None
            segments.append({
                "start_minute": start,
                "end_minute": end,
                "home_actions": home_actions,
                "away_actions": away_actions,
                "dominant_team_id": dominant,
            })
        start = end
    return segments


def top_key_players(player_ratings: list, n: int = 3) -> list[dict]:
    """Top-n already-computed player ratings -- no new scoring logic, just
    a read of player_ratings sorted by rating descending."""
    sortable = [
        {
            "player_id": r["player_id"] if isinstance(r, dict) else r.player_id,
            "name": r["name"] if isinstance(r, dict) else r.name,
            "team_id": r["team_id"] if isinstance(r, dict) else r.team_id,
            "rating": r["rating"] if isinstance(r, dict) else r.rating,
            "is_mom": r["is_mom"] if isinstance(r, dict) else r.is_mom,
        }
        for r in player_ratings
    ]
    return sorted(sortable, key=lambda r: -r["rating"])[:n]


def build_tactical_note(
    home_team_id: str,
    away_team_id: str,
    home_formation: str,
    away_formation: str,
    home_tactical_profile: dict | None,
    away_tactical_profile: dict | None,
) -> str:
    """A short templated sentence from already-existing formation/manager/
    tactical-profile fields -- no new attribute or claim is introduced."""

    def _describe(team_id: str, formation: str, profile: dict | None) -> str:
        if not profile:
            return f"{team_id}は{formation}を採用。"
        manager = profile.get("manager_name")
        press = profile.get("press_intensity")
        possession = profile.get("possession_style")
        manager_part = f"{manager}監督の" if manager else ""
        style_parts = []
        if press is not None:
            style_parts.append(f"プレス強度{press}")
        if possession is not None:
            style_parts.append(f"ポゼッション志向{possession}")
        style_part = ("・" + "・".join(style_parts)) if style_parts else ""
        return f"{manager_part}{team_id}は{formation}{style_part}。"

    return _describe(home_team_id, home_formation, home_tactical_profile) + _describe(
        away_team_id, away_formation, away_tactical_profile
    )


def build_match_analysis(
    events: list[dict],
    player_ratings: list,
    home_team_id: str,
    away_team_id: str,
    home_formation: str,
    away_formation: str,
    home_tactical_profile: dict | None,
    away_tactical_profile: dict | None,
) -> dict | None:
    """Returns None when there's nothing meaningful to derive (no events) --
    callers should show a calm limited-data state instead of an empty
    analysis panel."""
    if not events:
        return None

    return {
        "turning_point": compute_turning_point(events, home_team_id, away_team_id),
        "momentum_segments": compute_momentum_segments(events, home_team_id, away_team_id),
        "key_players": top_key_players(player_ratings),
        "tactical_note": build_tactical_note(
            home_team_id, away_team_id, home_formation, away_formation, home_tactical_profile, away_tactical_profile
        ),
    }
