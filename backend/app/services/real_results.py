"""Loads real-world 2026 FIFA World Cup group-stage results
(data/seed/real_results/{letter}.json) and persists them as completed
Match rows, bypassing the simulator entirely. Used by tournament.py so
that already-played fixtures show their actual outcome and only
not-yet-played fixtures are predicted by the engine.

Source data is researched via cross-checked WebSearch/WebFetch against
multiple outlets (kept to scores, scorers, and team-level stats -- granular
data like full lineups and per-player ratings turned out to have real
fabrication risk even with strict verification, so those are deliberately
NOT collected this way; see player_ratings.estimate_real_match_ratings for
the conservative goal-scorer-only stand-in). A real structured provider
(e.g. API-Football) would remove that risk entirely but the free tier
doesn't cover the current World Cup season and the paid tier wasn't
adopted -- so this module also accepts a richer schema (lineups, granular
events, real player_ratings) for whichever entries do end up curated to
that standard, without requiring all of them to be.
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
LEGACY_DATA_SOURCE = "Wikipedia (2026 FIFA World Cup Group pages)"
API_DATA_SOURCE = "API-Football"

CARD_EVENT_TYPES = {"Yellow Card": "yellow_card", "Red Card": "red_card"}


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


def _find_player(
    db: Session, team_id: str, name: str, name_ja: str | None
) -> tuple[str | None, str]:
    """Best-effort match of a real player name to a roster Player. Many
    real-world players aren't in our trimmed ~15-man squads, so falls back
    to a researched name_ja (if supplied) and finally to the raw name."""
    players = db.scalars(select(Player).where(Player.team_id == team_id)).all()
    needle = name.lower().replace("-", " ")
    for p in players:
        haystack = p.name.lower().replace("-", " ")
        if needle == haystack or needle in haystack or haystack.split()[-1] in needle:
            return p.id, (p.name_ja or p.name)
    return None, (name_ja or name)


def _build_lineup_side(db: Session, team_id: str, side: dict) -> list[dict]:
    """Converts an API-Football lineup side ({formation, coach, players:
    [{name, position, grid}]}) into the LineupPlayer-shaped dicts the
    pitch view already knows how to render. The "grid" field (API-Football's
    "row:column" pitch position) is mapped onto our 0-100 x/y system --
    row determines how advanced the player is (x), column determines
    left-right spread within that row (y)."""
    players = side.get("players") or []
    rows: dict[int, list[dict]] = {}
    for p in players:
        grid = p.get("grid")
        if not grid:
            continue
        row, _, col = grid.partition(":")
        rows.setdefault(int(row), []).append({**p, "_col": int(col)})

    if not rows:
        return []

    max_row = max(rows)
    lineup = []
    for row, row_players in rows.items():
        row_players.sort(key=lambda p: p["_col"])
        x = 5.0 if max_row == 1 else 5.0 + (row - 1) / (max_row - 1) * 85.0
        count = len(row_players)
        for i, p in enumerate(row_players):
            y = (i + 0.5) / count * 100.0
            player_id, display_name = _find_player(db, team_id, p["name"], p.get("name_ja"))
            lineup.append({
                "player_id": player_id or f"real:{team_id}:{p['name']}",
                "name": display_name,
                "slot_position": p.get("position") or "",
                "x": round(x, 1),
                "y": round(y, 1),
            })
    return lineup


def _build_lineups(db: Session, home_team_id: str, away_team_id: str, lineups: dict) -> tuple[list[dict], list[dict]]:
    home_lineup = _build_lineup_side(db, home_team_id, lineups.get("home") or {})
    away_lineup = _build_lineup_side(db, away_team_id, lineups.get("away") or {})
    return home_lineup, away_lineup


def _build_events_from_api(db: Session, raw_events: list[dict]) -> list[dict]:
    out = []
    for e in raw_events:
        minute = min(e["minute"], 90)
        team_id = e["team_id"]
        etype = e["type"]
        player_name = e.get("player_name")

        if etype == "Goal":
            player_id, display_name = _find_player(db, team_id, player_name, e.get("player_name_ja")) if player_name else (None, "")
            detail = (e.get("detail") or "").lower()
            suffix = "(オウンゴール)" if "own goal" in detail else "(PK)" if "penalty" in detail else ""
            out.append(make_event(minute, "goal", team_id, f"{display_name}{suffix} がゴール!", player_id=player_id))
        elif etype == "subst":
            on_name = player_name or ""
            off_name = e.get("assist_name") or ""
            _, on_ja = _find_player(db, team_id, on_name, e.get("player_name_ja")) if on_name else (None, on_name)
            out.append(make_event(
                minute, "substitution", team_id,
                f"選手交代: {off_name} に代わって {on_ja} が入る。",
            ))
        elif etype == "Card" and player_name:
            event_type = CARD_EVENT_TYPES.get(e.get("detail") or "", "yellow_card")
            player_id, display_name = _find_player(db, team_id, player_name, e.get("player_name_ja"))
            label = "イエローカード" if event_type == "yellow_card" else "レッドカード"
            out.append(make_event(minute, event_type, team_id, f"{display_name} に{label}。", player_id=player_id))
    return out


def _build_events_legacy(db: Session, goals: list[dict]) -> list[dict]:
    out = []
    for goal in goals:
        scorer_team_id = goal["team_id"]
        # An own goal is credited to the benefiting team (scorer_team_id) but
        # the scorer plays for the opponent, so don't link/highlight him as one
        # of the benefiting team's roster players.
        if goal.get("own_goal"):
            suffix = "(オウンゴール)"
            display_name = goal.get("scorer_name_ja") or goal["scorer_name"]
            player_id = None
        else:
            player_id, display_name = _find_player(
                db, scorer_team_id, goal["scorer_name"], goal.get("scorer_name_ja")
            )
            suffix = "(PK)" if goal.get("penalty") else ""
        out.append(make_event(
            min(goal["minute"], 90), "goal", scorer_team_id,
            f"{display_name}{suffix} がゴール!",
            player_id=player_id,
        ))
    return out


def _build_player_ratings(db: Session, raw_ratings: list[dict]) -> list[dict]:
    if not raw_ratings:
        return []
    ratings = []
    for r in raw_ratings:
        player_id, display_name = _find_player(db, r["team_id"], r["name"], r.get("name_ja"))
        ratings.append({
            "player_id": player_id or f"real:{r['team_id']}:{r['name']}",
            "name": display_name,
            "team_id": r["team_id"],
            "rating": r["rating"],
        })
    ratings.sort(key=lambda r: -r["rating"])
    for i, r in enumerate(ratings):
        r["is_mom"] = i == 0
        r["is_estimated"] = False
    return ratings


def persist_real_match(
    db: Session,
    home_team_id: str,
    away_team_id: str,
    group_id: str,
    result: dict,
) -> Match:
    """Builds a real-data event timeline from a synced result dict and
    persists it as a completed Match, skipping the simulator entirely."""
    home_team = db.get(Team, home_team_id)
    away_team = db.get(Team, away_team_id)
    home_score = result["home_score"]
    away_score = result["away_score"]
    is_api_sourced = result.get("source") == "api-football"

    home_lineup: list[dict] = []
    away_lineup: list[dict] = []
    if result.get("lineups"):
        home_lineup, away_lineup = _build_lineups(db, home_team_id, away_team_id, result["lineups"])

    events: list[dict] = [make_event(0, "kickoff", home_team_id, "キックオフ。", x=50, y=50)]
    if result.get("events"):
        events.extend(_build_events_from_api(db, result["events"]))
    else:
        events.extend(_build_events_legacy(db, result.get("goals", [])))
    events.append(make_event(90, "fulltime", home_team_id, "試合終了。", event_metadata={
        "home_score": home_score, "away_score": away_score,
    }))

    home_roster = {p["player_id"]: p["name"] for p in home_lineup}
    away_roster = {p["player_id"]: p["name"] for p in away_lineup}
    player_ratings = _build_player_ratings(db, result.get("player_ratings") or [])

    played_at = datetime.fromisoformat(result["date"]) if result.get("date") else datetime.utcnow()
    stats = result.get("stats") or {}
    lineups = result.get("lineups") or {}

    match = Match(
        id=str(uuid.uuid4()),
        group_id=group_id,
        round="group",
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_formation=(lineups.get("home") or {}).get("formation") or home_team.default_formation,
        away_formation=(lineups.get("away") or {}).get("formation") or away_team.default_formation,
        home_lineup=home_lineup,
        away_lineup=away_lineup,
        home_roster=home_roster,
        away_roster=away_roster,
        home_score=home_score,
        away_score=away_score,
        went_to_penalties=False,
        status="completed",
        played_at=played_at,
        is_real=True,
        data_source=API_DATA_SOURCE if is_api_sourced else LEGACY_DATA_SOURCE,
        home_possession_pct=stats.get("home_possession_pct"),
        away_possession_pct=stats.get("away_possession_pct"),
        home_shots=stats.get("home_shots"),
        away_shots=stats.get("away_shots"),
        home_shots_on_target=stats.get("home_shots_on_target"),
        away_shots_on_target=stats.get("away_shots_on_target"),
        home_yellow_cards=stats.get("home_yellow_cards"),
        away_yellow_cards=stats.get("away_yellow_cards"),
        player_ratings=player_ratings,
    )
    db.add(match)
    for e in events:
        db.add(MatchEvent(match_id=match.id, **e))
    db.commit()
    db.refresh(match)
    return match
