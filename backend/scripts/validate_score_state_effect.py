"""One-off validation: does a team that's trailing late in the match
actually generate more attacking output (shots) than one that's level or
leading, the way a real team chasing the game does? management.py's
update_score_state_tactics() computes a tactical shift for this, but
computing a number is not the same as it changing on-pitch behavior --
this measures the actual event log to check the mechanism is really
wired through choose_action/compute_shot_xg, not just inert.

Methodology: for evenly-matched real matchups, run many seeds, and for
every minute in the last quarter (75'-90'), classify each team's score
state at that minute (trailing/level/leading) and count shot-attempt
events (shot/goal/penalty_kick) attributed to that team in that minute.
Normalizing shots by team-minutes spent in each state (not just raw
counts) avoids bias from one state being rarer than another.

Read-only -- does not touch the database.
Usage: ./venv/Scripts/python.exe scripts/validate_score_state_effect.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.engine.simulator import simulate_match
from app.models.player import Player
from app.models.team import Team

N_SEEDS = 150
LATE_WINDOW = (75, 90)  # minutes considered "chasing the game" territory

MATCHUPS = [
    ("JPN", "KOR"),
    ("MEX", "USA"),
    ("NED", "BEL"),
]

SHOT_EVENT_TYPES = {"shot", "goal", "penalty_kick"}


def team_players_as_dicts(db, team_id: str) -> list[dict]:
    players = db.scalars(select(Player).where(Player.team_id == team_id)).all()
    return [
        {
            "id": p.id, "name": p.name, "name_ja": p.name_ja,
            "primary_position": p.primary_position,
            "secondary_positions": p.secondary_positions,
            "overall": p.overall, "attributes": p.attributes,
            "stamina_max": p.stamina_max,
        }
        for p in players
    ]


def _is_goal(e: dict) -> bool:
    if e["event_type"] == "goal":
        return True
    return e["event_type"] == "penalty_kick" and (e.get("event_metadata") or {}).get("scored") is True


def classify_match(result: dict, home_id: str, away_id: str, counts: dict, team_minutes: dict) -> None:
    """Walks the event log chronologically, tracking the running score so
    each shot-attempt event is classified by the attacking team's score
    state *at that moment* (events are minute-stamped but not perfectly
    ordered within a minute, which is fine -- we only need the score as of
    the start of that minute, computed from all strictly-earlier goals)."""
    events = sorted(result["events"], key=lambda e: e["minute"])
    home_score_at = {}
    away_score_at = {}
    hs = asc = 0
    for minute in range(0, 121):
        for e in events:
            if e["minute"] == minute and _is_goal(e):
                if e["team_id"] == home_id:
                    hs += 1
                else:
                    asc += 1
        home_score_at[minute] = hs
        away_score_at[minute] = asc

    def state_for(team_id: str, minute: int) -> str:
        h, a = home_score_at.get(minute, hs), away_score_at.get(minute, asc)
        diff = (h - a) if team_id == home_id else (a - h)
        if diff < 0:
            return "trailing"
        if diff > 0:
            return "leading"
        return "level"

    for minute in range(LATE_WINDOW[0], LATE_WINDOW[1]):
        if minute > max(home_score_at.keys(), default=0):
            break  # match ended before this minute (e.g. no extra time)
        for team_id in (home_id, away_id):
            team_minutes[state_for(team_id, minute)] += 1

    for e in events:
        if not (LATE_WINDOW[0] <= e["minute"] < LATE_WINDOW[1]):
            continue
        if e["event_type"] not in SHOT_EVENT_TYPES:
            continue
        state = state_for(e["team_id"], e["minute"])
        counts[state] += 1


def main():
    db = SessionLocal()
    counts = {"trailing": 0, "level": 0, "leading": 0}
    team_minutes = {"trailing": 0, "level": 0, "leading": 0}

    for home_id, away_id in MATCHUPS:
        home_team = db.get(Team, home_id)
        away_team = db.get(Team, away_id)
        home_players = team_players_as_dicts(db, home_id)
        away_players = team_players_as_dicts(db, away_id)

        for seed in range(N_SEEDS):
            result = simulate_match(
                home_team_id=home_id, away_team_id=away_id,
                home_players=home_players, away_players=away_players,
                home_formation=home_team.default_formation,
                away_formation=away_team.default_formation,
                seed=seed, allow_draw=True,
                home_tactical_profile=home_team.tactical_profile,
                away_tactical_profile=away_team.tactical_profile,
            )
            classify_match(result, home_id, away_id, counts, team_minutes)

    db.close()

    print(f"Matchups: {MATCHUPS}, {N_SEEDS} seeds each, late window {LATE_WINDOW}")
    print(f"{'state':10s} {'shot-events':>12s} {'team-minutes':>13s} {'shots/team-min':>15s}")
    rates = {}
    for state in ("trailing", "level", "leading"):
        tm = team_minutes[state]
        rate = counts[state] / tm if tm > 0 else 0.0
        rates[state] = rate
        print(f"{state:10s} {counts[state]:12d} {tm:13d} {rate:15.3f}")

    print()
    # The intended check is trailing vs. *level* (the neutral, unshifted
    # baseline) -- that isolates the score-state tactical push itself.
    # leading vs. trailing is a separate, expected confound: a team that's
    # leading late is disproportionately the side that was already playing
    # better that match (not just "sitting back" tactically), so it isn't
    # evidence against the chasing mechanic working.
    if rates["level"] > 0 and rates["trailing"] > rates["level"]:
        lift_vs_level = (rates["trailing"] / rates["level"] - 1) * 100
        print(f"PASS: trailing teams generate more shots/team-minute than level teams ({lift_vs_level:+.0f}%).")
        print(f"(leading={rates['leading']:.3f} vs trailing={rates['trailing']:.3f} is a separate confound -- "
              f"see script docstring -- not evidence the chasing mechanic itself is broken.)")
    else:
        print("FAIL: trailing-team attacking boost is not clearly showing up in shot output vs. the level baseline.")


if __name__ == "__main__":
    main()
