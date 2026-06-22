import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rating_v2.legacy_bridge import derive_legacy_attributes
from app.rating_v2.seed_pipeline_v2 import official_profile_attributes
from app.rating_v2.player_rating_model import compute_player_rating_v2


def _player(**overrides) -> dict:
    base = {
        "playerId": "TST_PLAYER", "teamId": "TST", "name": "Test Player", "age": 26,
        "primaryPosition": "ST", "secondaryPositions": [], "marketValueEur": 20_000_000,
        "careerStats": {
            "appearances": 30, "goals": 10, "assists": 5, "minutesPlayed": 2500,
            "keyPassesPer90": 1.5, "successfulDribblesPer90": 1.5,
            "tacklesPer90": 1.0, "interceptionsPer90": 0.8,
            "aerialDuelsWonPct": 50.0, "passCompletionPct": 80.0,
        },
        "qualitativeAdjustments": {}, "staminaMax": 90,
    }
    base.update(overrides)
    return base


def test_bridged_outfield_attributes_stay_in_0_99_range():
    rating = compute_player_rating_v2(_player(), peer_market_values_eur=[20_000_000])
    attrs = derive_legacy_attributes(rating)
    for key in ("pace", "shooting", "passing", "dribbling", "defending", "physical"):
        assert 0 <= attrs[key] <= 99
    assert attrs["gk_reflexes"] is None
    assert attrs["gk_handling"] is None


def test_bridged_goalkeeper_gets_gk_attributes_not_none():
    rating = compute_player_rating_v2(_player(primaryPosition="GK"), peer_market_values_eur=[20_000_000])
    attrs = derive_legacy_attributes(rating)
    assert attrs["gk_reflexes"] is not None
    assert attrs["gk_handling"] is not None
    assert 0 <= attrs["gk_reflexes"] <= 99
    assert 0 <= attrs["gk_handling"] <= 99


def test_bridge_round_trips_direct_copy_fields_exactly():
    # defense/passing/dribbling/physical are direct copies going forward
    # (player_rating_model.py), so the bridge must recover them exactly,
    # not just approximately.
    rating = compute_player_rating_v2(_player(), peer_market_values_eur=[20_000_000])
    attrs = derive_legacy_attributes(rating)
    assert attrs["defending"] == rating.defense
    assert attrs["passing"] == rating.passing
    assert attrs["dribbling"] == rating.dribbling
    assert attrs["physical"] == rating.physical


def test_official_profile_attributes_are_preserved_for_runtime_api():
    attrs = official_profile_attributes({
        "dateOfBirth": "02/10/1992",
        "heightCm": 193,
        "clubName": "Liverpool FC (ENG)",
        "caps": 80,
        "nationalTeamGoals": 0,
    })
    assert attrs == {
        "dateOfBirth": "02/10/1992",
        "heightCm": 193,
        "clubName": "Liverpool FC (ENG)",
        "caps": 80,
        "nationalTeamGoals": 0,
    }
