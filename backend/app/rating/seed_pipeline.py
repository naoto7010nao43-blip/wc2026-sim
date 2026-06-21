"""Reads raw researched JSON (teams.json, players.json) and runs the rating
pipeline (Stage A/B/C from formulas.py) to produce Player rows ready for
persistence. Percentiles for Stage A and B are computed within each
player's position group, across the full seed dataset.
"""

import json
from pathlib import Path

from app.rating.formulas import (
    POSITION_GROUPS,
    StageAInputs,
    apply_pipeline,
    compute_overall,
    percentile_rank,
    stage_a_gk_attributes,
    stage_a_raw_attributes,
)

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "seed"


def _stage_a_inputs_from_raw(player_raw: dict) -> StageAInputs:
    stats = player_raw["career_stats"]
    position_group = POSITION_GROUPS.get(player_raw["primary_position"], "MID")
    appearances = max(stats.get("appearances", 1), 1)
    minutes = stats.get("minutes_played", appearances * 70)
    return StageAInputs(
        position_group=position_group,
        age=player_raw["age"],
        goals_per90=stats.get("goals", 0) / appearances,
        assists_per90=stats.get("assists", 0) / appearances,
        key_passes_per90=stats.get("key_passes_per90", 0.0),
        successful_dribbles_per90=stats.get("successful_dribbles_per90", 0.0),
        tackles_per90=stats.get("tackles_per90", 0.0),
        interceptions_per90=stats.get("interceptions_per90", 0.0),
        aerial_duels_won_pct=stats.get("aerial_duels_won_pct", 40.0),
        pass_completion_pct=stats.get("pass_completion_pct", 78.0),
        minutes_per_appearance=minutes / appearances,
        save_pct=stats.get("save_pct"),
        goals_conceded_per90=stats.get("goals_conceded_per90"),
    )


def load_seed_data() -> tuple[list[dict], list[dict]]:
    teams = json.loads((SEED_DIR / "teams.json").read_text(encoding="utf-8"))
    players = json.loads((SEED_DIR / "players.json").read_text(encoding="utf-8"))
    return teams, players


def build_player_rows(players_raw: list[dict]) -> list[dict]:
    """Returns a list of dicts ready to construct Player ORM rows, with
    final attributes/overall computed via the Stage A/B/C pipeline."""

    # Group raw players by position group for percentile normalization.
    by_group: dict[str, list[dict]] = {}
    for p in players_raw:
        group = POSITION_GROUPS.get(p["primary_position"], "MID")
        by_group.setdefault(group, []).append(p)

    # Pre-compute Stage A raw scores and market values per player.
    stage_a_by_id: dict[str, dict[str, float]] = {}
    market_value_by_id: dict[str, float] = {}
    for p in players_raw:
        inp = _stage_a_inputs_from_raw(p)
        group = inp.position_group
        if group == "GK":
            stage_a_by_id[p["id"]] = stage_a_gk_attributes(inp)
        else:
            stage_a_by_id[p["id"]] = stage_a_raw_attributes(inp)
        market_value_by_id[p["id"]] = p.get("market_value_eur", 0)

    rows = []
    for p in players_raw:
        group = POSITION_GROUPS.get(p["primary_position"], "MID")
        peers = by_group[group]
        peer_market_values = [market_value_by_id[peer["id"]] for peer in peers]
        market_pct = percentile_rank(market_value_by_id[p["id"]], peer_market_values)

        qualitative_adjustments = p.get("qualitative_adjustments", {})

        if group == "GK":
            gk_raw = stage_a_by_id[p["id"]]
            gk_final = apply_pipeline(gk_raw, market_pct, qualitative_adjustments)
            # Outfield-style attrs default to modest values for GKs (rarely used in engine).
            attributes = {
                "pace": 50, "shooting": 15, "passing": 55,
                "dribbling": 35, "defending": 40, "physical": 60,
                "gk_reflexes": gk_final["gk_reflexes"],
                "gk_handling": gk_final["gk_handling"],
            }
        else:
            raw = stage_a_by_id[p["id"]]
            final = apply_pipeline(raw, market_pct, qualitative_adjustments)
            attributes = {**final, "gk_reflexes": None, "gk_handling": None}

        overall = compute_overall(attributes, p["primary_position"])

        rows.append({
            "id": p["id"],
            "team_id": p["team_id"],
            "name": p["name"],
            "name_ja": p.get("name_ja"),
            "age": p["age"],
            "primary_position": p["primary_position"],
            "secondary_positions": p.get("secondary_positions", []),
            "overall": overall,
            "attributes": attributes,
            "stamina_max": p.get("stamina_max", 100),
            "source_notes": "; ".join(p.get("source_citations", [])) or None,
        })
    return rows
