"""Audit curated real-results seed data for structural consistency.

This script deliberately checks invariants that ordinary API/unit tests can
miss when the real-results JSON is updated by hand:

- every group has exactly its six round-robin fixtures, no duplicates;
- scores, goal entries, and penalty fields are internally coherent;
- already-entered knockout results line up with the bracket generated from the
  seeded group results.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import Base
from app.models.match import Match  # noqa: F401  ensures table metadata is registered
from app.models.player import Player
from app.models.team import Team
from app.rating.seed_pipeline import build_player_rows, load_seed_data
from app.services.tournament import run_full_tournament

REAL_RESULTS_DIR = BACKEND_ROOT / "data" / "seed" / "real_results"
GROUPS = tuple("ABCDEFGHIJKL")


@dataclass(frozen=True)
class RealResultsFinding:
    scope: str
    message: str


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _team_groups() -> tuple[dict[str, str], dict[str, set[str]]]:
    teams = _load_json(BACKEND_ROOT / "data" / "seed" / "teams.json")
    team_to_group: dict[str, str] = {}
    group_to_teams: dict[str, set[str]] = {group: set() for group in GROUPS}
    for team in teams:
        team_id = team["id"]
        group = team.get("group_id")
        team_to_group[team_id] = group
        if group in group_to_teams:
            group_to_teams[group].add(team_id)
    return team_to_group, group_to_teams


def _score_value(value: object) -> bool:
    return isinstance(value, int) and value >= 0


def _check_score_and_goals(scope: str, entry: dict) -> list[RealResultsFinding]:
    findings: list[RealResultsFinding] = []
    home_id = entry.get("home_team_id")
    away_id = entry.get("away_team_id")
    home_score = entry.get("home_score")
    away_score = entry.get("away_score")

    if not _score_value(home_score):
        findings.append(RealResultsFinding(scope, f"home_score must be a non-negative integer: {home_score!r}"))
    if not _score_value(away_score):
        findings.append(RealResultsFinding(scope, f"away_score must be a non-negative integer: {away_score!r}"))
    if not isinstance(entry.get("date"), str) or not entry["date"]:
        findings.append(RealResultsFinding(scope, "date is required"))

    if not findings:
        goal_counts = {home_id: 0, away_id: 0}
        for goal_index, goal in enumerate(entry.get("goals") or []):
            team_id = goal.get("team_id")
            if team_id not in goal_counts:
                findings.append(RealResultsFinding(scope, f"goal {goal_index} has team_id outside fixture: {team_id!r}"))
                continue
            if not isinstance(goal.get("minute"), int) or goal["minute"] < 0:
                findings.append(RealResultsFinding(scope, f"goal {goal_index} has invalid minute: {goal.get('minute')!r}"))
            if not goal.get("scorer_name"):
                findings.append(RealResultsFinding(scope, f"goal {goal_index} is missing scorer_name"))
            goal_counts[team_id] += 1
        if goal_counts[home_id] != home_score:
            findings.append(RealResultsFinding(scope, f"home goals list has {goal_counts[home_id]} goals but score is {home_score}"))
        if goal_counts[away_id] != away_score:
            findings.append(RealResultsFinding(scope, f"away goals list has {goal_counts[away_id]} goals but score is {away_score}"))

    return findings


def audit_group_results() -> list[RealResultsFinding]:
    team_to_group, group_to_teams = _team_groups()
    findings: list[RealResultsFinding] = []

    for group, teams in group_to_teams.items():
        if len(teams) != 4:
            findings.append(RealResultsFinding(f"group {group}", f"expected 4 teams, found {len(teams)}"))

    for group in GROUPS:
        path = REAL_RESULTS_DIR / f"{group}.json"
        if not path.exists():
            findings.append(RealResultsFinding(f"group {group}", "missing real-results file"))
            continue
        entries = _load_json(path)
        if not isinstance(entries, list):
            findings.append(RealResultsFinding(f"group {group}", "file must contain a JSON list"))
            continue
        if len(entries) != 6:
            findings.append(RealResultsFinding(f"group {group}", f"expected 6 matches, found {len(entries)}"))

        actual_pairs: set[frozenset[str]] = set()
        expected_pairs = {frozenset(pair) for pair in combinations(group_to_teams[group], 2)}
        for index, entry in enumerate(entries):
            scope = f"group {group} match {index}"
            home_id = entry.get("home_team_id")
            away_id = entry.get("away_team_id")
            if team_to_group.get(home_id) != group or team_to_group.get(away_id) != group:
                findings.append(RealResultsFinding(scope, f"fixture teams are not both in group {group}: {home_id}-{away_id}"))
            pair = frozenset({home_id, away_id})
            if len(pair) != 2:
                findings.append(RealResultsFinding(scope, f"fixture must have two different teams: {home_id}-{away_id}"))
            if pair in actual_pairs:
                findings.append(RealResultsFinding(scope, f"duplicate fixture pair: {sorted(pair)}"))
            actual_pairs.add(pair)
            findings.extend(_check_score_and_goals(scope, entry))

        missing = expected_pairs - actual_pairs
        extra = actual_pairs - expected_pairs
        if missing:
            findings.append(RealResultsFinding(f"group {group}", f"missing fixture pairs: {sorted(sorted(p) for p in missing)}"))
        if extra:
            findings.append(RealResultsFinding(f"group {group}", f"unexpected fixture pairs: {sorted(sorted(p) for p in extra)}"))

    return findings


def audit_knockout_results() -> list[RealResultsFinding]:
    team_to_group, _ = _team_groups()
    path = REAL_RESULTS_DIR / "knockout.json"
    if not path.exists():
        return []

    entries = _load_json(path)
    findings: list[RealResultsFinding] = []
    seen_pairs: set[tuple[str, frozenset[str]]] = set()
    for index, entry in enumerate(entries):
        scope = f"knockout match {index}"
        round_name = entry.get("round")
        if round_name not in {"R32", "R16", "QF", "SF", "THIRD_PLACE", "FINAL"}:
            findings.append(RealResultsFinding(scope, f"invalid knockout round: {round_name!r}"))
        home_id = entry.get("home_team_id")
        away_id = entry.get("away_team_id")
        if home_id not in team_to_group or away_id not in team_to_group:
            findings.append(RealResultsFinding(scope, f"unknown team in fixture: {home_id}-{away_id}"))
        pair_key = (round_name, frozenset({home_id, away_id}))
        if pair_key in seen_pairs:
            findings.append(RealResultsFinding(scope, f"duplicate knockout fixture: {round_name} {home_id}-{away_id}"))
        seen_pairs.add(pair_key)
        findings.extend(_check_score_and_goals(scope, entry))

        home_score = entry.get("home_score")
        away_score = entry.get("away_score")
        went_to_penalties = bool(entry.get("went_to_penalties"))
        if home_score == away_score and not went_to_penalties:
            findings.append(RealResultsFinding(scope, "drawn knockout match must include went_to_penalties=true"))
        if went_to_penalties:
            ph = entry.get("penalty_home_score")
            pa = entry.get("penalty_away_score")
            if not _score_value(ph) or not _score_value(pa) or ph == pa:
                findings.append(RealResultsFinding(scope, f"invalid penalty score: {ph}-{pa}"))

    findings.extend(_audit_knockout_entries_are_used(entries))
    return findings


def _make_seeded_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    teams_raw, players_raw = load_seed_data()
    player_rows = build_player_rows(players_raw)
    for team in teams_raw:
        session.add(Team(
            id=team["id"],
            name=team["name"],
            confederation=team["confederation"],
            fifa_rank=team.get("fifa_rank"),
            default_formation=team["default_formation"],
            group_id=team.get("group_id"),
            tactical_profile=team.get("tactical_profile"),
        ))
    session.flush()
    for player in player_rows:
        session.add(Player(**player))
    session.commit()
    return session


def _audit_knockout_entries_are_used(entries: list[dict]) -> list[RealResultsFinding]:
    findings: list[RealResultsFinding] = []
    session = _make_seeded_session()
    try:
        result = run_full_tournament(session, base_seed=0)
        real_matches_by_round: dict[str, set[frozenset[str]]] = {}
        for round_name, matches in result["matches"].items():
            for match in matches:
                if match.is_real:
                    real_matches_by_round.setdefault(round_name, set()).add(frozenset({match.home_team_id, match.away_team_id}))

        for index, entry in enumerate(entries):
            round_name = entry.get("round")
            pair = frozenset({entry.get("home_team_id"), entry.get("away_team_id")})
            if pair not in real_matches_by_round.get(round_name, set()):
                findings.append(RealResultsFinding(
                    f"knockout match {index}",
                    f"real result is not reachable in generated bracket: {round_name} {sorted(pair)}",
                ))
    finally:
        session.close()
    return findings


def audit_real_results_integrity() -> list[RealResultsFinding]:
    return [*audit_group_results(), *audit_knockout_results()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON")
    args = parser.parse_args()

    findings = audit_real_results_integrity()
    if args.json:
        print(json.dumps([finding.__dict__ for finding in findings], ensure_ascii=False, indent=2))
    elif findings:
        for finding in findings:
            print(f"{finding.scope}: {finding.message}")
    else:
        print("Real results integrity audit passed.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
