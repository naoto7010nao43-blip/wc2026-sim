import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rating_v2.player_rating_model import compute_player_rating_v2, compute_starting_probabilities


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


def test_starting_probability_in_json_dict_and_default_for_old_files():
    rating = compute_player_rating_v2(_player(), peer_market_values_eur=[20_000_000])
    d = rating.to_json_dict()
    assert "startingProbability" in d
    assert d["startingProbability"] == 50  # placeholder until compute_starting_probabilities runs

    d_without_field = {k: v for k, v in d.items() if k != "startingProbability"}
    from app.rating_v2.types import PlayerRatingV2
    roundtrip = PlayerRatingV2.from_json_dict(d_without_field)
    assert roundtrip.starting_probability == 50  # backward-compat default for pre-existing rating files


def test_more_minutes_and_market_value_raises_starting_probability_within_team():
    regular = _player(playerId="p_regular", marketValueEur=30_000_000, careerStats={"minutesPlayed": 3000, "appearances": 34})
    backup = _player(playerId="p_backup", marketValueEur=2_000_000, careerStats={"minutesPlayed": 300, "appearances": 8})

    players = [regular, backup]
    ratings_by_id = {
        p["playerId"]: compute_player_rating_v2(p, peer_market_values_eur=[30_000_000, 2_000_000])
        for p in players
    }
    probs = compute_starting_probabilities(players, ratings_by_id)
    assert probs["p_regular"] > probs["p_backup"]


def test_sole_specialist_in_position_group_gets_neutral_probability():
    lone_forward = _player(playerId="p_lone_fwd", primaryPosition="ST")
    defenders = [
        _player(playerId="p_def1", primaryPosition="CB"),
        _player(playerId="p_def2", primaryPosition="CB"),
    ]
    players = [lone_forward, *defenders]
    ratings_by_id = {
        p["playerId"]: compute_player_rating_v2(p, peer_market_values_eur=[20_000_000])
        for p in players
    }
    probs = compute_starting_probabilities(players, ratings_by_id)
    assert probs["p_lone_fwd"] == 50


def test_starting_probability_is_team_scoped_not_league_wide():
    # Two separate teams, each with a "regular" and a "backup" -- a backup
    # on a weak team must not be inflated just because a stronger team's
    # players are part of the same input list.
    team_a = [
        _player(playerId="a_regular", teamId="A", marketValueEur=50_000_000, careerStats={"minutesPlayed": 3000, "appearances": 34}),
        _player(playerId="a_backup", teamId="A", marketValueEur=1_000_000, careerStats={"minutesPlayed": 200, "appearances": 5}),
    ]
    team_b = [
        _player(playerId="b_regular", teamId="B", marketValueEur=5_000_000, careerStats={"minutesPlayed": 3000, "appearances": 34}),
        _player(playerId="b_backup", teamId="B", marketValueEur=100_000, careerStats={"minutesPlayed": 200, "appearances": 5}),
    ]
    players = team_a + team_b
    ratings_by_id = {
        p["playerId"]: compute_player_rating_v2(p, peer_market_values_eur=[v["marketValueEur"] for v in players])
        for p in players
    }
    probs = compute_starting_probabilities(players, ratings_by_id)
    # Despite team B's players having far lower market values than team A's,
    # b_regular should still clearly outrank b_backup within team B's own cohort.
    assert probs["b_regular"] > probs["b_backup"]
    assert probs["a_regular"] > probs["a_backup"]
