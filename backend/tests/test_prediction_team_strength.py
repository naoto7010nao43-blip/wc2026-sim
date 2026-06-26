import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.prediction.model_config import DEFAULT_MODEL_CONFIG
from app.prediction.ratings import squad_strength_rating, team_strength_rating


def player(overall: int):
    return {
        "id": f"P{overall}",
        "name": f"Player {overall}",
        "primary_position": "CM",
        "overall": overall,
        "attributes": {},
        "stamina_max": 60,
    }


def test_team_strength_uses_rank75_squad25_blend():
    players = [player(60) for _ in range(11)]
    strength, confidence = team_strength_rating(1, players)
    rank_score_for_number_one = 95.0
    expected = rank_score_for_number_one * 0.75 + squad_strength_rating(players) * 0.25
    assert round(strength, 3) == round(expected, 3)
    assert confidence == "estimated"


def test_team_strength_without_fifa_rank_uses_squad_only():
    players = [player(60) for _ in range(11)]
    strength, confidence = team_strength_rating(None, players)
    assert strength == squad_strength_rating(players)
    assert confidence == "estimated"


def test_prediction_model_version_tracks_rank75_calibration():
    # Bumped when the Dixon-Coles low-score correction + starting-probability
    # weighting (Phase 0 accuracy work) landed; the rank75 squad blend is
    # unchanged, the version just tracks the model revision.
    assert DEFAULT_MODEL_CONFIG.model_version == "poisson-v3-dc-startprob"
