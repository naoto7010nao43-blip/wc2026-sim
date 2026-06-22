"""Bridges the v2 official-roster + estimated-ratings files into the same
row shapes app/rating/seed_pipeline.py produces, so scripts/seed_db.py
needs only a small "which pipeline" branch -- the Player/Team ORM
construction and the rest of the app are completely unaware v2 exists.
"""

import json
from pathlib import Path

from app.rating_v2.legacy_bridge import derive_legacy_attributes, v2_skill_attributes
from app.rating_v2.types import PlayerRatingV2

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "seed"

REQUIRED_FILES = ("players2026_official.json", "playerRatings2026_estimated.json", "teams2026_official.json")


def v2_files_present() -> bool:
    return all((SEED_DIR / name).exists() for name in REQUIRED_FILES)


def _load(name: str) -> list[dict]:
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def load_v2_seed_data() -> tuple[list[dict], list[dict]]:
    """Returns (teams, player_rows) in the same shapes
    app.rating.seed_pipeline.load_seed_data()/build_player_rows() produce,
    so scripts/seed_db.py's Team(...)/Player(**p) construction is unchanged."""
    teams_official = _load("teams2026_official.json")
    players_official = _load("players2026_official.json")
    ratings = _load("playerRatings2026_estimated.json")
    ratings_by_id = {r["playerId"]: r for r in ratings}

    teams = [
        {
            "id": t["teamId"],
            "name": t["name"],
            "confederation": t["confederation"],
            "fifa_rank": t.get("fifaRank"),
            "default_formation": t["defaultFormation"],
            "group_id": t.get("groupId"),
            "tactical_profile": t.get("tacticalProfile"),
        }
        for t in teams_official
    ]

    player_rows = []
    for p in players_official:
        rating_dict = ratings_by_id.get(p["playerId"])
        if rating_dict is None:
            continue  # no estimated rating yet for this roster entry -- skip rather than fabricate one
        rating = PlayerRatingV2.from_json_dict(rating_dict)
        # Legacy 6+2 keys for app/engine/* (the micro-simulator) plus the
        # finer-grained v2 keys for app/prediction/ratings.py (the Poisson
        # model) -- both read the same Player.attributes JSON column.
        attributes = {**derive_legacy_attributes(rating), **v2_skill_attributes(rating)}
        player_rows.append({
            "id": p["playerId"],
            "team_id": p["teamId"],
            "name": p["name"],
            "name_ja": p.get("nameJa"),
            "age": p.get("age") or 27,
            "primary_position": p["primaryPosition"],
            "secondary_positions": p.get("secondaryPositions", []),
            "overall": rating.overall,
            "attributes": attributes,
            "stamina_max": p.get("staminaMax", 100),
            "source_notes": "; ".join(p.get("sourceCitations", [])) or None,
        })
    return teams, player_rows
