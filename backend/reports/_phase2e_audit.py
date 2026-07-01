"""Reproducible formation / position-fit audit (Phase 2e). Analysis only --
writes nothing. Run from backend/:

    PYTHONPATH=. ./venv/Scripts/python.exe reports/_phase2e_audit.py

Joins players.json (positions) with playerRatings2026_estimated.json
(startingProbability/overall), runs the shared select_starting_assignments()
for each team's defaultFormation, and flags out-of-position (OOP) starters and
fielded starters with startingProbability < 40 (LOWPROB). See
phase2e_formation_position_fit_audit_2026-07-01.md for interpretation.
"""

import json
from collections import defaultdict
from pathlib import Path

from app.engine.formations import FORMATIONS
from app.engine.lineup_selection import select_starting_assignments

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"


def load():
    ratings = {r["playerId"]: r for r in json.load(open(SEED / "playerRatings2026_estimated.json", encoding="utf-8"))}
    base = json.load(open(SEED / "players.json", encoding="utf-8"))
    teams = {t["teamId"]: t for t in json.load(open(SEED / "teams2026_official.json", encoding="utf-8"))}
    by_team = defaultdict(list)
    for p in base:
        r = ratings.get(p["id"], {})
        by_team[p["team_id"]].append({
            "id": p["id"],
            "name": p["name"],
            "name_ja": p.get("name_ja"),
            "primary_position": p["primary_position"],
            "secondary_positions": p.get("secondary_positions") or [],
            "overall": r.get("overall", 50),
            "attributes": {"startingProbability": r.get("startingProbability")},
            "stamina_max": p.get("stamina_max", 90),
        })
    return by_team, teams


def main():
    by_team, teams = load()
    for tid in sorted(by_team):
        form = teams[tid]["defaultFormation"]
        roster = by_team[tid]
        assign = select_starting_assignments(roster, form)
        slots = FORMATIONS[form].slots
        oop, lowprob = [], []
        for idx, slot in enumerate(slots):
            p = assign.get(idx)
            if p is None:
                oop.append(f"{slot.position}=EMPTY")
                continue
            prob = (p["attributes"] or {}).get("startingProbability")
            pp = p["primary_position"]
            if pp != slot.position and slot.position not in p.get("secondary_positions", []):
                oop.append(f'{slot.position}<-{p["name"]}({pp})')
            if prob is None or prob < 40:
                lowprob.append(f'{p["name"]}={prob}')
        if oop or lowprob:
            print(f"{tid} {form} n={len(roster)}")
            if oop:
                print("   OOP:", oop)
            if lowprob:
                print("   LOWPROB:", lowprob)


if __name__ == "__main__":
    main()
