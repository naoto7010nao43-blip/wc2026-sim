from __future__ import annotations

from app.prediction.model_config import DEFAULT_MODEL_CONFIG, ModelConfig
from app.prediction.poisson_model import PREDICTION_DISCLAIMER, build_match_features, compute_lambda
from app.prediction.ratings import attack_rating, defense_rating, team_strength_rating
from app.rating_v2.lineup_builder import build_likely_lineup


def _edge_team(home_team_id: str, away_team_id: str, edge: float) -> str | None:
    if abs(edge) < 0.05:
        return None
    return home_team_id if edge > 0 else away_team_id


def _format_edge(edge: float) -> str:
    return f"{abs(edge):.1f}"


def _factor(
    *,
    key: str,
    label: str,
    home_team_id: str,
    away_team_id: str,
    home_value: float | None,
    away_value: float | None,
    edge: float,
    model_impact: float,
    unit: str,
) -> dict:
    edge_team_id = _edge_team(home_team_id, away_team_id, edge)
    if edge_team_id is None:
        description = f"{label}はほぼ互角です。"
    else:
        description = f"{edge_team_id}が{label}で{_format_edge(edge)}{unit}上回っています。"
    return {
        "key": key,
        "label": label,
        "home_value": None if home_value is None else round(home_value, 2),
        "away_value": None if away_value is None else round(away_value, 2),
        "edge": round(edge, 2),
        "edge_team_id": edge_team_id,
        "model_impact": round(model_impact, 4),
        "description_ja": description,
    }


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _lineup_summary(team_id: str, formation: str, players: list[dict]) -> dict:
    lineup = build_likely_lineup(players, formation)
    probabilities = [slot["starting_probability"] for slot in lineup if slot.get("starting_probability") is not None]
    avg_probability = _avg(probabilities)
    return {
        "team_id": team_id,
        "formation": formation,
        "starter_count": len(lineup),
        "avg_starting_probability": None if avg_probability is None else round(avg_probability, 1),
        "low_probability_starter_count": sum(1 for value in probabilities if value < 40),
        "full_xi": len(lineup) == 11,
    }


def _summary(home_team_id: str, away_team_id: str, factors: list[dict], lambda_home: float, lambda_away: float) -> tuple[str | None, str]:
    favorite_team_id = None
    if abs(lambda_home - lambda_away) >= 0.05:
        favorite_team_id = home_team_id if lambda_home > lambda_away else away_team_id
    largest = max(factors, key=lambda factor: abs(factor["model_impact"]), default=None)
    if favorite_team_id is None:
        return None, "予想得点はほぼ互角で、決定的な優位要因は限定的です。"
    if largest and largest["edge_team_id"]:
        return favorite_team_id, f"{favorite_team_id}がやや優勢です。主な要因は{largest['label']}です。"
    return favorite_team_id, f"{favorite_team_id}がやや優勢ですが、単独で大きく支配する要因はありません。"


def build_matchup_breakdown(
    *,
    home_team_id: str,
    away_team_id: str,
    home_players: list[dict],
    away_players: list[dict],
    home_fifa_rank: int | None,
    away_fifa_rank: int | None,
    home_formation: str,
    away_formation: str,
    home_tactical_profile: dict | None = None,
    away_tactical_profile: dict | None = None,
    host_bump_home: float = 0.0,
    host_bump_away: float = 0.0,
    config: ModelConfig = DEFAULT_MODEL_CONFIG,
) -> dict:
    features = build_match_features(
        home_players,
        away_players,
        home_fifa_rank,
        away_fifa_rank,
        home_tactical_profile,
        away_tactical_profile,
    )
    lambda_home, lambda_away = compute_lambda(features, config, host_bump_home, host_bump_away)
    home_attack = attack_rating(home_players)
    away_attack = attack_rating(away_players)
    home_defense = defense_rating(home_players)
    away_defense = defense_rating(away_players)
    home_strength, _ = team_strength_rating(home_fifa_rank, home_players)
    away_strength, _ = team_strength_rating(away_fifa_rank, away_players)
    host_edge = host_bump_home - host_bump_away

    factors = [
        _factor(
            key="attack",
            label="攻撃評価",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_value=home_attack,
            away_value=away_attack,
            edge=features.attack_diff,
            model_impact=config.attack_diff_weight * features.attack_diff,
            unit="pt",
        ),
        _factor(
            key="defense",
            label="守備相性",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_value=100.0 - home_defense,
            away_value=100.0 - away_defense,
            edge=features.defense_diff,
            model_impact=config.defense_diff_weight * features.defense_diff,
            unit="pt",
        ),
        _factor(
            key="strength",
            label="総合力",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_value=home_strength,
            away_value=away_strength,
            edge=features.strength_diff,
            model_impact=config.strength_diff_weight * features.strength_diff,
            unit="pt",
        ),
        _factor(
            key="tactical",
            label="戦術噛み合わせ",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_value=None,
            away_value=None,
            edge=features.tactical_modifier,
            model_impact=config.tactical_matchup_weight * features.tactical_modifier,
            unit="",
        ),
    ]
    if abs(host_edge) > 0:
        factors.append(
            _factor(
                key="host",
                label="開催国補正",
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_value=host_bump_home,
                away_value=host_bump_away,
                edge=host_edge,
                model_impact=host_edge,
                unit="",
            )
        )
    factors.sort(key=lambda factor: abs(factor["model_impact"]), reverse=True)
    favorite_team_id, summary = _summary(home_team_id, away_team_id, factors, lambda_home, lambda_away)
    return {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "favorite_team_id": favorite_team_id,
        "summary_ja": summary,
        "factors": factors,
        "lineups": [
            _lineup_summary(home_team_id, home_formation, home_players),
            _lineup_summary(away_team_id, away_formation, away_players),
        ],
        "model_version": config.model_version,
        "disclaimer": PREDICTION_DISCLAIMER,
    }
