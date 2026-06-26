"""Persists a Match row for a *simulated* (not-yet-real) fixture using the
Poisson statistical model (app.prediction.poisson_model) instead of the
old minute-by-minute micro-simulator (app.engine.simulator).

No lineup/events/shots/cards are generated for these matches -- the
Poisson model only produces a scoreline, not a possession-by-possession
narrative. Those fields stay null, and the existing frontend already
falls back gracefully when they're absent (the same path used today for
real-world matches that have no lineup data).
"""

import random
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.matches import team_players_as_dicts
from app.models.match import Match
from app.models.team import Team
from app.prediction.model_config import DEFAULT_MODEL_CONFIG, ModelConfig
from app.prediction.poisson_model import (
    build_match_features,
    compute_lambda,
    plausible_shootout_score,
    sample_scoreline,
    score_distribution,
    shootout_win_probability,
)
from app.schemas.match import SimulateMatchRequest

HOST_NATIONS = {"USA", "MEX", "CAN"}


def run_and_persist_predicted_match(
    db: Session,
    req: SimulateMatchRequest,
    config: ModelConfig = DEFAULT_MODEL_CONFIG,
) -> Match:
    home_team = db.get(Team, req.home_team_id)
    away_team = db.get(Team, req.away_team_id)
    if home_team is None or away_team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    home_players = team_players_as_dicts(db, req.home_team_id)
    away_players = team_players_as_dicts(db, req.away_team_id)

    features = build_match_features(
        home_players, away_players,
        home_team.fifa_rank, away_team.fifa_rank,
        home_team.tactical_profile, away_team.tactical_profile,
    )
    host_bump_home = config.host_advantage if req.home_team_id in HOST_NATIONS else 0.0
    host_bump_away = config.host_advantage if req.away_team_id in HOST_NATIONS else 0.0
    lambda_home, lambda_away = compute_lambda(features, config, host_bump_home, host_bump_away)
    matrix = score_distribution(lambda_home, lambda_away, config.max_goals, config.dixon_coles_rho)

    seed = req.seed if req.seed is not None else uuid.uuid4().int & 0xFFFFFFFF
    rng = random.Random(seed)
    home_score, away_score = sample_scoreline(matrix, rng)

    went_to_penalties = False
    penalty_home_score = penalty_away_score = None
    if not req.allow_draw and home_score == away_score:
        went_to_penalties = True
        home_wins = rng.random() < shootout_win_probability(lambda_home, lambda_away)
        penalty_home_score, penalty_away_score = plausible_shootout_score(home_wins, rng)

    match = Match(
        id=str(uuid.uuid4()),
        group_id=req.group_id,
        round=req.round,
        bracket_slot=req.bracket_slot,
        home_team_id=req.home_team_id,
        away_team_id=req.away_team_id,
        home_formation=req.home_formation or home_team.default_formation,
        away_formation=req.away_formation or away_team.default_formation,
        home_score=home_score,
        away_score=away_score,
        went_to_penalties=went_to_penalties,
        penalty_home_score=penalty_home_score,
        penalty_away_score=penalty_away_score,
        status="completed",
        seed=seed,
        data_source="poisson-model",
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match
