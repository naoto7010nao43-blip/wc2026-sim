import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rating_v2.player_rating_model import compute_player_rating_v2


def _player(**overrides) -> dict:
    base = {
        "playerId": "TST_PLAYER",
        "teamId": "TST",
        "name": "Test Player",
        "age": 26,
        "primaryPosition": "ST",
        "secondaryPositions": [],
        "marketValueEur": 20_000_000,
        "careerStats": {
            "appearances": 30, "goals": 10, "assists": 5, "minutesPlayed": 2500,
            "keyPassesPer90": 1.5, "successfulDribblesPer90": 1.5,
            "tacklesPer90": 1.0, "interceptionsPer90": 0.8,
            "aerialDuelsWonPct": 50.0, "passCompletionPct": 80.0,
        },
        "qualitativeAdjustments": {},
        "staminaMax": 90,
    }
    base.update(overrides)
    return base


def test_higher_market_value_raises_overall_other_things_equal():
    low = compute_player_rating_v2(_player(marketValueEur=2_000_000), peer_market_values_eur=[2_000_000, 20_000_000, 60_000_000])
    high = compute_player_rating_v2(_player(marketValueEur=60_000_000), peer_market_values_eur=[2_000_000, 20_000_000, 60_000_000])
    assert high.overall > low.overall


def test_missing_market_value_does_not_become_zero():
    rating = compute_player_rating_v2(_player(marketValueEur=None), peer_market_values_eur=[10_000_000, 20_000_000])
    # A missing market value must fall back to a neutral mid-range score,
    # not be treated as "worthless" -- overall should stay in a plausible
    # band, not collapse toward the lower clamp bound.
    assert 40 <= rating.overall <= 90


def test_missing_data_increases_uncertainty():
    complete = compute_player_rating_v2(_player(), peer_market_values_eur=[20_000_000])
    sparse = compute_player_rating_v2(
        _player(marketValueEur=None, age=None, careerStats={}),
        peer_market_values_eur=[20_000_000],
    )
    assert sparse.uncertainty > complete.uncertainty


def test_uncertainty_has_a_nonzero_floor_even_with_complete_data():
    # Every player currently lacks national-team-context data (caps,
    # recent international minutes) regardless of how complete their club
    # stats are -- uncertainty must never read as a false "fully certain" 0.
    rating = compute_player_rating_v2(_player(), peer_market_values_eur=[20_000_000])
    assert rating.uncertainty > 0.0


def test_overall_is_clamped_between_35_and_95():
    extreme_low = compute_player_rating_v2(
        _player(marketValueEur=1, careerStats={"appearances": 1, "goals": 0, "assists": 0}),
        peer_market_values_eur=[50_000_000],
    )
    extreme_high = compute_player_rating_v2(
        _player(marketValueEur=200_000_000, careerStats={"appearances": 40, "goals": 35, "assists": 20}),
        peer_market_values_eur=[1_000_000, 200_000_000],
    )
    assert 35 <= extreme_low.overall <= 95
    assert 35 <= extreme_high.overall <= 95


def test_manual_override_is_applied_and_marks_mixed_confidence():
    override = {"playerId": "TST_PLAYER", "overrides": {"chanceCreation": 91}, "reason": "test override"}
    rating = compute_player_rating_v2(_player(), peer_market_values_eur=[20_000_000], manual_override=override)
    assert rating.chance_creation == 91
    assert rating.data_confidence == "mixed"
    assert rating.source_breakdown.manual_override_used is True


def test_goalkeeper_gets_goalkeeper_attributes_and_outfield_gets_none():
    gk = compute_player_rating_v2(_player(primaryPosition="GK"), peer_market_values_eur=[20_000_000])
    outfield = compute_player_rating_v2(_player(primaryPosition="ST"), peer_market_values_eur=[20_000_000])
    assert gk.goalkeeper_reflexes is not None
    assert gk.goalkeeper_handling is not None
    assert outfield.goalkeeper_reflexes is None
    assert outfield.goalkeeper_handling is None


def test_low_confidence_attributes_are_flagged_not_hidden():
    rating = compute_player_rating_v2(_player(), peer_market_values_eur=[20_000_000])
    assert "mentality" in rating.low_confidence_attributes
    assert "composure" in rating.low_confidence_attributes
    # but the stats-backed attributes must NOT be in that list
    assert "passing" not in rating.low_confidence_attributes
    assert "defense" not in rating.low_confidence_attributes


def _ea_reference(**overrides) -> dict:
    # Shape of one entry in externalPlayerRatings2026.json (EA FC 26 face stats).
    base = {
        "playerId": "TST_PLAYER", "source": "EA SPORTS FC 26",
        "sourceUrl": "https://www.ea.com/games/ea-sports-fc/ratings/player-ratings/x/1",
        "overall": 90, "pace": 86, "shooting": 91, "passing": 70,
        "dribbling": 80, "defending": 45, "physical": 88,
    }
    base.update(overrides)
    return base


def test_external_reference_overrides_estimated_overall_verbatim():
    # The whole point: a sourced EA overall replaces the compressed estimate,
    # rather than being blended/diluted by the per-90 pipeline.
    estimated = compute_player_rating_v2(_player(), peer_market_values_eur=[20_000_000])
    external = compute_player_rating_v2(
        _player(), peer_market_values_eur=[20_000_000], external_reference=_ea_reference(overall=90),
    )
    assert estimated.overall < 90  # the estimator compresses this player
    assert external.overall == 90  # the EA value is taken verbatim
    assert external.data_confidence == "external"
    assert external.source_breakdown.external_reference_used is True


def test_external_reference_face_stats_drive_derived_attributes():
    # The six EA face stats map onto the engine's base; derived sub-attributes
    # must reflect them (e.g. defense mirrors EA defending), so a sourced
    # player stays internally consistent rather than carrying stale estimates.
    rating = compute_player_rating_v2(
        _player(), peer_market_values_eur=[20_000_000],
        external_reference=_ea_reference(defending=45, physical=88, passing=70),
    )
    assert rating.defense == 45
    assert rating.physical == 88
    assert rating.passing == 70


def test_external_reference_has_low_uncertainty():
    estimated = compute_player_rating_v2(_player(), peer_market_values_eur=[20_000_000])
    external = compute_player_rating_v2(
        _player(), peer_market_values_eur=[20_000_000], external_reference=_ea_reference(),
    )
    assert external.uncertainty < estimated.uncertainty
    assert external.uncertainty > 0.0  # still a small source/observation slack


def test_external_reference_plus_manual_override_is_mixed():
    override = {"playerId": "TST_PLAYER", "overrides": {"finishing": 99}, "reason": "test"}
    rating = compute_player_rating_v2(
        _player(), peer_market_values_eur=[20_000_000],
        manual_override=override, external_reference=_ea_reference(),
    )
    assert rating.finishing == 99
    assert rating.data_confidence == "mixed"
    assert rating.source_breakdown.external_reference_used is True
    assert rating.source_breakdown.manual_override_used is True


def test_external_goalkeeper_uses_gk_reference_stats():
    rating = compute_player_rating_v2(
        _player(primaryPosition="GK"), peer_market_values_eur=[20_000_000],
        external_reference={
            "playerId": "TST_GK", "source": "EA SPORTS FC 26", "sourceUrl": "https://www.ea.com/x",
            "overall": 89, "gkReflexes": 90, "gkHandling": 85, "gkSpeed": 60,
        },
    )
    assert rating.overall == 89
    assert rating.goalkeeper_reflexes == 90
    assert rating.goalkeeper_handling == 85
    assert rating.data_confidence == "external"
