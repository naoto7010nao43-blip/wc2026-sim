"""Loads researched real-world 2026 FIFA World Cup group-stage results
(data/seed/real_results/{letter}.json) and persists them as completed
Match rows, bypassing the simulator entirely. Used by tournament.py so
that already-played fixtures show their actual outcome and only
not-yet-played fixtures are predicted by the engine.

Source data is refreshed manually by re-running the per-group research
agents as the tournament progresses (see README for the refresh cadence).
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.events import make_event
from app.models.match import Match, MatchEvent
from app.models.player import Player
from app.models.team import Team

REAL_RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "seed" / "real_results"
GROUP_LETTERS = list("ABCDEFGHIJKL")
DATA_SOURCE = "Wikipedia (2026 FIFA World Cup Group pages)"


def load_real_results() -> dict[str, dict[frozenset, dict]]:
    """Returns {group_letter: {frozenset({home_id, away_id}): result_dict}}."""
    by_group: dict[str, dict[frozenset, dict]] = {}
    for letter in GROUP_LETTERS:
        path = REAL_RESULTS_DIR / f"{letter}.json"
        if not path.exists():
            by_group[letter] = {}
            continue
        entries = json.loads(path.read_text(encoding="utf-8"))
        by_group[letter] = {
            frozenset({e["home_team_id"], e["away_team_id"]}): e
            for e in entries
        }
    return by_group


def _find_scorer_id(db: Session, team_id: str, scorer_name: str) -> tuple[str | None, str | None]:
    """Best-effort match of a researched scorer name to a roster Player.
    Returns (player_id, display_name); falls back to (None, scorer_name)."""
    players = db.scalars(select(Player).where(Player.team_id == team_id)).all()
    needle = scorer_name.lower().replace("-", " ")
    for p in players:
        haystack = p.name.lower().replace("-", " ")
        if needle == haystack or needle in haystack or haystack.split()[-1] in needle:
            return p.id, (p.name_ja or p.name)
    return None, scorer_name


def persist_real_match(
    db: Session,
    home_team_id: str,
    away_team_id: str,
    group_id: str,
    result: dict,
) -> Match:
    """Builds a minimal real-data event timeline (kickoff/goals/fulltime)
    from a researched result dict and persists it as a completed Match,
    skipping the simulator entirely."""
    home_team = db.get(Team, home_team_id)
    away_team = db.get(Team, away_team_id)
    home_score = result["home_score"]
    away_score = result["away_score"]

    events: list[dict] = [make_event(0, "kickoff", home_team_id, "キックオフ。", x=50, y=50)]
    for goal in result.get("goals", []):
        scorer_team_id = goal["team_id"]
        player_id, display_name = _find_scorer_id(db, scorer_team_id, goal["scorer_name"])
        events.append(make_event(
            min(goal["minute"], 90), "goal", scorer_team_id,
            f"{display_name} がゴール!",
            player_id=player_id,
        ))
    events.append(make_event(90, "fulltime", home_team_id, "試合終了。", event_metadata={
        "home_score": home_score, "away_score": away_score,
    }))

    played_at = datetime.fromisoformat(result["date"]) if result.get("date") else datetime.utcnow()

    match = Match(
        id=str(uuid.uuid4()),
        group_id=group_id,
        round="group",
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_formation=home_team.default_formation,
        away_formation=away_team.default_formation,
        home_score=home_score,
        away_score=away_score,
        went_to_penalties=False,
        status="completed",
        played_at=played_at,
        is_real=True,
        data_source=DATA_SOURCE,
    )
    db.add(match)
    for e in events:
        db.add(MatchEvent(match_id=match.id, **e))
    db.commit()
    db.refresh(match)
    return match
