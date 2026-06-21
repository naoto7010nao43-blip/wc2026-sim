"""Merges the 12 per-group research files in data/seed/groups/ into the
canonical data/seed/teams.json (48 teams) and players.json (~600 players).

Each group file's team list either contains full team objects (new teams)
or a "patch" object for one of the 6 teams already researched in Phase 1
(detected by the absence of a "name" key) — those patches add group_id
and tactical_profile to the existing team record without touching its
other fields or its already-researched players.

Run with: venv/Scripts/python.exe scripts/merge_group_seed_data.py
"""

import json
import sys
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
GROUPS_DIR = SEED_DIR / "groups"
GROUP_LETTERS = list("ABCDEFGHIJKL")
VALID_POSITIONS = {"GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "ST"}


def main() -> None:
    teams: list[dict] = json.loads((SEED_DIR / "teams.json").read_text(encoding="utf-8"))
    players: list[dict] = json.loads((SEED_DIR / "players.json").read_text(encoding="utf-8"))

    teams_by_id = {t["id"]: t for t in teams}
    existing_player_ids = {p["id"] for p in players}

    for letter in GROUP_LETTERS:
        group_teams = json.loads((GROUPS_DIR / f"{letter}_teams.json").read_text(encoding="utf-8"))
        group_players = json.loads((GROUPS_DIR / f"{letter}_players.json").read_text(encoding="utf-8"))

        for t in group_teams:
            if "name" not in t:
                # Patch object for an already-researched Phase 1 team.
                target = teams_by_id.get(t["id"])
                if target is None:
                    sys.exit(f"Group {letter}: patch references unknown team id {t['id']!r}")
                target["group_id"] = t["group_id"]
                target["tactical_profile"] = t["tactical_profile"]
            else:
                if t["id"] in teams_by_id:
                    sys.exit(f"Group {letter}: duplicate team id {t['id']!r}")
                teams_by_id[t["id"]] = t
                teams.append(t)

        for p in group_players:
            if p["id"] in existing_player_ids:
                sys.exit(f"Group {letter}: duplicate player id {p['id']!r}")
            existing_player_ids.add(p["id"])
            players.append(p)

    # --- Validation ---
    assert len(teams) == 48, f"Expected 48 teams, got {len(teams)}"

    by_group: dict[str, list[str]] = {}
    for t in teams:
        gid = t.get("group_id")
        if gid is None:
            sys.exit(f"Team {t['id']!r} is missing group_id after merge")
        by_group.setdefault(gid, []).append(t["id"])
    assert set(by_group.keys()) == set(GROUP_LETTERS), f"Group letters mismatch: {sorted(by_group.keys())}"
    for letter, ids in by_group.items():
        assert len(ids) == 4, f"Group {letter} has {len(ids)} teams: {ids}"

    team_ids = {t["id"] for t in teams}
    seen_player_ids: set[str] = set()
    for p in players:
        assert p["id"] not in seen_player_ids, f"Duplicate player id {p['id']!r}"
        seen_player_ids.add(p["id"])
        assert p["team_id"] in team_ids, f"Player {p['id']!r} references unknown team {p['team_id']!r}"
        assert p["primary_position"] in VALID_POSITIONS, f"Player {p['id']!r} has invalid position {p['primary_position']!r}"
        for sp in p.get("secondary_positions", []):
            assert sp in VALID_POSITIONS, f"Player {p['id']!r} has invalid secondary position {sp!r}"

    (SEED_DIR / "teams.json").write_text(json.dumps(teams, indent=2, ensure_ascii=False), encoding="utf-8")
    (SEED_DIR / "players.json").write_text(json.dumps(players, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Merged {len(teams)} teams (12 groups x 4) and {len(players)} players.")
    for letter in GROUP_LETTERS:
        names = ", ".join(t["name"] for t in teams if t.get("group_id") == letter)
        print(f"  Group {letter}: {names}")


if __name__ == "__main__":
    main()
