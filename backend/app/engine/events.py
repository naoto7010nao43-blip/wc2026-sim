"""Event factory helpers. Events are plain dicts matching MatchEvent columns,
collected by the simulator and persisted by the API layer."""


def make_event(
    minute: int,
    event_type: str,
    team_id: str,
    description: str,
    player_id: str | None = None,
    secondary_player_id: str | None = None,
    x: float | None = None,
    y: float | None = None,
    event_metadata: dict | None = None,
) -> dict:
    return {
        "minute": minute,
        "event_type": event_type,
        "team_id": team_id,
        "player_id": player_id,
        "secondary_player_id": secondary_player_id,
        "x": x,
        "y": y,
        "description": description,
        "event_metadata": event_metadata,
    }
