"""Merges the 12 per-group katakana-name files in data/seed/names_ja/ into
the canonical data/seed/players.json, filling in each player's name_ja field.

Run with: venv/Scripts/python.exe scripts/merge_names_ja.py
"""

import json
import sys
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
NAMES_JA_DIR = SEED_DIR / "names_ja"
GROUP_LETTERS = list("ABCDEFGHIJKL")


def main() -> None:
    players: list[dict] = json.loads((SEED_DIR / "players.json").read_text(encoding="utf-8"))
    players_by_id = {p["id"]: p for p in players}

    name_ja_by_id: dict[str, str] = {}
    for letter in GROUP_LETTERS:
        entries = json.loads((NAMES_JA_DIR / f"{letter}.json").read_text(encoding="utf-8"))
        for e in entries:
            if e["id"] in name_ja_by_id:
                sys.exit(f"Group {letter}: duplicate player id {e['id']!r}")
            name_ja_by_id[e["id"]] = e["name_ja"]

    assert len(name_ja_by_id) == 669, f"Expected 669 katakana names, got {len(name_ja_by_id)}"

    missing_in_players = [pid for pid in name_ja_by_id if pid not in players_by_id]
    if missing_in_players:
        sys.exit(f"{len(missing_in_players)} ids not found in players.json: {missing_in_players[:10]}")

    missing_names = [p["id"] for p in players if p["id"] not in name_ja_by_id]
    if missing_names:
        sys.exit(f"{len(missing_names)} players have no katakana name: {missing_names[:10]}")

    for p in players:
        p["name_ja"] = name_ja_by_id[p["id"]]

    (SEED_DIR / "players.json").write_text(json.dumps(players, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Merged name_ja for {len(players)} players.")


if __name__ == "__main__":
    main()
