"""Closed-form Poisson expected-goals prediction model -- the statistical
replacement for the old minute-by-minute micro-simulator (app.engine.*).

Every prediction is an *estimate*: see PREDICTION_DISCLAIMER, which must
accompany any prediction shown to a user.
"""

import math
import random
from dataclasses import dataclass

from app.prediction.model_config import DEFAULT_MODEL_CONFIG, ModelConfig
from app.prediction.ratings import attack_rating, defense_rating, team_strength_rating

PREDICTION_DISCLAIMER = "これは予測であり、実際の結果を保証するものではありません。"


@dataclass(frozen=True)
class MatchFeatures:
    attack_diff: float
    defense_diff: float
    strength_diff: float
    tactical_modifier: float
    data_confidence: str


@dataclass(frozen=True)
class MatchPrediction:
    home_team_id: str
    away_team_id: str
    home_win_pct: float
    draw_pct: float
    away_win_pct: float
    home_expected_goals: float
    away_expected_goals: float
    most_likely_scores: list[tuple[int, int, float]]  # (home_goals, away_goals, probability_pct), top 3
    data_confidence: str
    explanation: list[str]
    model_version: str
    disclaimer: str = PREDICTION_DISCLAIMER


def _tactical_matchup_modifier(home_profile: dict | None, away_profile: dict | None) -> float:
    """A small, transparent opponent-dependent adjustment from the existing
    tactical_profile fields (press_intensity/possession_style/
    defensive_line_height) -- no new attribute ontology. A high press
    against a low defensive line, or against a low-possession-control
    opponent, nudges the matchup in the presser's favor."""
    if not home_profile or not away_profile:
        return 0.0
    press_vs_possession = home_profile.get("press_intensity", 50.0) - away_profile.get("possession_style", 50.0)
    line_vs_press = away_profile.get("defensive_line_height", 50.0) - home_profile.get("press_intensity", 50.0)
    return (press_vs_possession - line_vs_press) / 400.0


def build_match_features(
    home_players: list[dict],
    away_players: list[dict],
    home_fifa_rank: int | None,
    away_fifa_rank: int | None,
    home_tactical_profile: dict | None = None,
    away_tactical_profile: dict | None = None,
) -> MatchFeatures:
    home_attack, home_defense = attack_rating(home_players), defense_rating(home_players)
    away_attack, away_defense = attack_rating(away_players), defense_rating(away_players)
    home_strength, home_confidence = team_strength_rating(home_fifa_rank, home_players)
    away_strength, away_confidence = team_strength_rating(away_fifa_rank, away_players)

    return MatchFeatures(
        attack_diff=home_attack - away_attack,
        defense_diff=away_defense - home_defense,  # a weaker away defense favors the home attack
        strength_diff=home_strength - away_strength,
        tactical_modifier=_tactical_matchup_modifier(home_tactical_profile, away_tactical_profile),
        data_confidence="estimated" if "estimated" in (home_confidence, away_confidence) else "official",
    )


def lambdas_from_ratings(
    home_attack: float,
    home_defense: float,
    home_strength: float,
    home_confidence: str,
    away_attack: float,
    away_defense: float,
    away_strength: float,
    away_confidence: str,
    home_tactical_profile: dict | None = None,
    away_tactical_profile: dict | None = None,
    host_bump_home: float = 0.0,
    host_bump_away: float = 0.0,
    config: ModelConfig = DEFAULT_MODEL_CONFIG,
) -> tuple[float, float]:
    """Same end result as build_match_features + compute_lambda, but
    starting from already-computed team ratings (app.prediction.ratings)
    instead of raw player lists. Monte Carlo simulation calls this
    thousands of times per run and must not re-scan every player's
    attributes on every call."""
    features = MatchFeatures(
        attack_diff=home_attack - away_attack,
        defense_diff=away_defense - home_defense,
        strength_diff=home_strength - away_strength,
        tactical_modifier=_tactical_matchup_modifier(home_tactical_profile, away_tactical_profile),
        data_confidence="estimated" if "estimated" in (home_confidence, away_confidence) else "official",
    )
    return compute_lambda(features, config, host_bump_home, host_bump_away)


def compute_lambda(
    features: MatchFeatures,
    config: ModelConfig = DEFAULT_MODEL_CONFIG,
    host_bump_home: float = 0.0,
    host_bump_away: float = 0.0,
) -> tuple[float, float]:
    home_log = (
        config.attack_diff_weight * features.attack_diff
        + config.defense_diff_weight * features.defense_diff
        + config.strength_diff_weight * features.strength_diff
        + config.tactical_matchup_weight * features.tactical_modifier
        + config.home_advantage
        + host_bump_home
    )
    away_log = (
        -config.attack_diff_weight * features.attack_diff
        - config.defense_diff_weight * features.defense_diff
        - config.strength_diff_weight * features.strength_diff
        - config.tactical_matchup_weight * features.tactical_modifier
        + host_bump_away
    )
    return config.base_goals * math.exp(home_log), config.base_goals * math.exp(away_log)


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def score_distribution(lambda_home: float, lambda_away: float, max_goals: int = 8) -> list[list[float]]:
    """Independent-Poisson scoreline probability matrix; matrix[h][a] is
    P(home scores h AND away scores a), normalized to sum to 1 after
    truncating at max_goals."""
    home_pmf = [_poisson_pmf(h, lambda_home) for h in range(max_goals + 1)]
    away_pmf = [_poisson_pmf(a, lambda_away) for a in range(max_goals + 1)]
    matrix = [[home_pmf[h] * away_pmf[a] for a in range(max_goals + 1)] for h in range(max_goals + 1)]
    total = sum(sum(row) for row in matrix)
    if total > 0:
        matrix = [[p / total for p in row] for row in matrix]
    return matrix


def sample_scoreline(matrix: list[list[float]], rng: random.Random) -> tuple[int, int]:
    """Draws a single (home_goals, away_goals) outcome from the scoreline
    probability matrix."""
    r = rng.random()
    cumulative = 0.0
    last = (len(matrix) - 1, len(matrix[-1]) - 1)
    for h, row in enumerate(matrix):
        for a, p in enumerate(row):
            cumulative += p
            if r <= cumulative:
                return h, a
    return last


def shootout_win_probability(lambda_home: float, lambda_away: float) -> float:
    """Approximates a penalty-shootout win probability for the home side
    when a knockout match is still level after regulation, biased by each
    side's relative attacking threat. Penalty shootouts are close to a
    coin flip even between mismatched teams, so the bias is bounded."""
    total = lambda_home + lambda_away
    if total <= 0:
        return 0.5
    return max(0.35, min(0.65, lambda_home / total))


def plausible_shootout_score(home_wins: bool, rng: random.Random) -> tuple[int, int]:
    """A cosmetic, plausible-looking penalty shootout scoreline (the actual
    winner is already decided by shootout_win_probability) -- most real
    shootouts end with the winner on 4 or 5 after the first 5 rounds."""
    winner_score = rng.choice([3, 4, 4, 5, 5])
    loser_score = winner_score - 1
    return (winner_score, loser_score) if home_wins else (loser_score, winner_score)


def _explain(features: MatchFeatures, home_team_id: str, away_team_id: str, host_team_id: str | None) -> list[str]:
    lines = []
    if abs(features.attack_diff) >= 3:
        leader = home_team_id if features.attack_diff > 0 else away_team_id
        lines.append(f"{leader} の攻撃評価が優位です。")
    if abs(features.defense_diff) >= 3:
        leader = home_team_id if features.defense_diff > 0 else away_team_id
        lines.append(f"{leader} は相手の守備に対して優位と評価されています。")
    if abs(features.strength_diff) >= 3:
        leader = home_team_id if features.strength_diff > 0 else away_team_id
        lines.append(f"{leader} はFIFAランキングとスカッド総合力で優位です。")
    if abs(features.tactical_modifier) >= 0.05:
        leader = home_team_id if features.tactical_modifier > 0 else away_team_id
        lines.append(f"{leader} はプレス強度と守備ラインの噛み合わせでやや優位です。")
    if host_team_id is not None:
        lines.append(f"{host_team_id} は開催国としてのホームアドバンテージを得ています。")
    if not lines:
        lines.append("両チームの評価はほぼ互角です。")
    return lines


def predict_match(
    home_team_id: str,
    away_team_id: str,
    home_players: list[dict],
    away_players: list[dict],
    home_fifa_rank: int | None,
    away_fifa_rank: int | None,
    home_tactical_profile: dict | None = None,
    away_tactical_profile: dict | None = None,
    host_bump_home: float = 0.0,
    host_bump_away: float = 0.0,
    config: ModelConfig = DEFAULT_MODEL_CONFIG,
) -> MatchPrediction:
    features = build_match_features(
        home_players, away_players, home_fifa_rank, away_fifa_rank,
        home_tactical_profile, away_tactical_profile,
    )
    lambda_home, lambda_away = compute_lambda(features, config, host_bump_home, host_bump_away)
    matrix = score_distribution(lambda_home, lambda_away, config.max_goals)

    size = len(matrix)
    home_win = sum(matrix[h][a] for h in range(size) for a in range(size) if h > a)
    draw = sum(matrix[h][a] for h in range(size) for a in range(size) if h == a)
    away_win = sum(matrix[h][a] for h in range(size) for a in range(size) if h < a)

    scored = sorted(
        ((h, a, matrix[h][a]) for h in range(size) for a in range(size)),
        key=lambda t: -t[2],
    )
    top_scores = [(h, a, round(p * 100, 1)) for h, a, p in scored[:3]]

    host_team_id = home_team_id if host_bump_home > 0 else (away_team_id if host_bump_away > 0 else None)

    return MatchPrediction(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_win_pct=round(home_win * 100, 1),
        draw_pct=round(draw * 100, 1),
        away_win_pct=round(away_win * 100, 1),
        home_expected_goals=round(lambda_home, 2),
        away_expected_goals=round(lambda_away, 2),
        most_likely_scores=top_scores,
        data_confidence=features.data_confidence,
        explanation=_explain(features, home_team_id, away_team_id, host_team_id),
        model_version=config.model_version,
    )
