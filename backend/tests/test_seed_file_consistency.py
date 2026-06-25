"""Guardrail against the exact bug class that let Uruguay's fifa_rank fix go
live-incomplete during Spec 018 Phase 9: teams.json (read directly by the
diagnostics/benchmark scripts) silently drifting from teams2026_official.json
(the file the live app actually seeds from, see app/rating_v2/seed_pipeline_v2.py).

scripts/apply_external_factual_updates.py now regenerates teams.json from
teams2026_official.json on every run, but that only protects future safe
updates applied *through that script*. This test catches drift from any
other cause (a hand edit, a different script, a merge) by asserting the two
files in the actual repo are still consistent right now.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.apply_external_factual_updates import (
    PLAYERS_PATH,
    PLAYERS_V2_PATH,
    TEAMS_PATH,
    TEAMS_V2_PATH,
    regenerate_legacy_players_json,
    regenerate_legacy_teams_json,
)


def test_teams_json_matches_the_regenerated_mirror_of_teams2026_official():
    assert TEAMS_V2_PATH.exists(), "teams2026_official.json is expected to exist in this repo"

    teams_v2 = json.loads(TEAMS_V2_PATH.read_text(encoding="utf-8"))
    actual = json.loads(TEAMS_PATH.read_text(encoding="utf-8"))
    expected = regenerate_legacy_teams_json(teams_v2, actual)

    assert actual == expected, (
        "teams.json has drifted from teams2026_official.json -- run "
        "`./venv/Scripts/python.exe scripts/apply_external_factual_updates.py` "
        "to regenerate it, or fix whatever wrote to teams.json directly."
    )


def test_players_json_matches_the_regenerated_mirror_of_players2026_official():
    """Same guardrail for the players layer. players.json is read directly by
    the diagnostics/benchmark scripts, while the live app seeds players from
    players2026_official.json (+ playerRatings2026_estimated.json); this fails
    on any drift from any cause, so a roster correction applied to the v2 file
    (e.g. via apply_fifa_squad_field_updates.py) can never silently leave the
    diagnostics layer reading stale player data."""
    assert PLAYERS_V2_PATH.exists(), "players2026_official.json is expected to exist in this repo"

    players_v2 = json.loads(PLAYERS_V2_PATH.read_text(encoding="utf-8"))
    actual = json.loads(PLAYERS_PATH.read_text(encoding="utf-8"))
    expected = regenerate_legacy_players_json(players_v2, actual)

    assert actual == expected, (
        "players.json has drifted from players2026_official.json -- run "
        "`./venv/Scripts/python.exe scripts/apply_external_factual_updates.py` "
        "to regenerate it, or fix whatever wrote to players.json directly."
    )
