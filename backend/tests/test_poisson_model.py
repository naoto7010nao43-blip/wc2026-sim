import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.prediction.model_config import DEFAULT_MODEL_CONFIG
from app.prediction.poisson_model import (
    PREDICTION_DISCLAIMER,
    predict_match,
    sample_scoreline,
    score_distribution,
)


def make_squad(team_id: str, base_overall: int) -> list[dict]:
    positions = ["GK", "CB", "CB", "LB", "RB", "CDM", "CM", "CM", "LW", "ST", "RW"]
    squad = []
    for i, pos in enumerate(positions):
        attrs = {
            "pace": base_overall, "shooting": base_overall, "passing": base_overall,
            "dribbling": base_overall, "defending": base_overall, "physical": base_overall,
            "gk_reflexes": base_overall if pos == "GK" else None,
            "gk_handling": base_overall if pos == "GK" else None,
        }
        squad.append({
            "id": f"{team_id}_{pos}_{i}",
            "name": f"{team_id} {pos} {i}",
            "primary_position": pos,
            "secondary_positions": [],
            "overall": base_overall,
            "attributes": attrs,
            "stamina_max": 90,
        })
    return squad


def test_stronger_team_is_favored_to_win():
    strong = make_squad("STRONG", 80)
    weak = make_squad("WEAK", 55)
    prediction = predict_match("STRONG", "WEAK", strong, weak, home_fifa_rank=3, away_fifa_rank=90)
    assert prediction.home_win_pct > prediction.away_win_pct
    assert prediction.home_expected_goals > prediction.away_expected_goals


def test_probabilities_sum_to_roughly_100():
    a = make_squad("A", 70)
    b = make_squad("B", 68)
    prediction = predict_match("A", "B", a, b, home_fifa_rank=20, away_fifa_rank=22)
    total = prediction.home_win_pct + prediction.draw_pct + prediction.away_win_pct
    assert abs(total - 100.0) < 0.5


def test_disclaimer_is_always_present():
    a = make_squad("A", 70)
    b = make_squad("B", 70)
    prediction = predict_match("A", "B", a, b, home_fifa_rank=None, away_fifa_rank=None)
    assert prediction.disclaimer == PREDICTION_DISCLAIMER


def test_evenly_matched_teams_with_no_fifa_rank_are_flagged_estimated():
    a = make_squad("A", 70)
    b = make_squad("B", 70)
    prediction = predict_match("A", "B", a, b, home_fifa_rank=None, away_fifa_rank=None)
    assert prediction.data_confidence == "estimated"


def test_host_advantage_increases_home_win_probability():
    a = make_squad("A", 70)
    b = make_squad("B", 70)
    baseline = predict_match("A", "B", a, b, home_fifa_rank=20, away_fifa_rank=20)
    hosted = predict_match(
        "A", "B", a, b, home_fifa_rank=20, away_fifa_rank=20,
        host_bump_home=DEFAULT_MODEL_CONFIG.host_advantage,
    )
    assert hosted.home_win_pct > baseline.home_win_pct


def test_score_distribution_matrix_sums_to_one():
    matrix = score_distribution(1.4, 1.1, max_goals=8)
    total = sum(sum(row) for row in matrix)
    assert abs(total - 1.0) < 1e-9


def test_sample_scoreline_is_within_bounds_and_seed_reproducible():
    matrix = score_distribution(1.6, 0.9, max_goals=6)
    r1 = sample_scoreline(matrix, random.Random(42))
    r2 = sample_scoreline(matrix, random.Random(42))
    assert r1 == r2
    h, a = r1
    assert 0 <= h <= 6
    assert 0 <= a <= 6
