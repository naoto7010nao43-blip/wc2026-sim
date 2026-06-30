"""Persists a Match row for a *simulated* (not-yet-real) fixture using the
Poisson statistical model (app.prediction.poisson_model) instead of the
old minute-by-minute micro-simulator (app.engine.simulator).

The Poisson model only produces a *scoreline*. A derived narrative layer
(app.prediction.match_narrative) then attaches plausible, clearly-simulated
supporting detail on top of that exact scoreline -- starting XIs, possession
split, shot counts and goal-scorer events -- so an inspected tournament
fixture shows who scored and how it played out. The scoreline itself is
never altered; the narrative is a deterministic function of the same seed.
"""

import random
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.matches import team_players_as_dicts
from app.engine.events import make_event
from app.models.match import Match, MatchEvent
from app.models.team import Team
from app.prediction.match_narrative import build_predicted_narrative
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

    home_formation = req.home_formation or home_team.default_formation
    away_formation = req.away_formation or away_team.default_formation

    # Derived narrative layer: starting XIs, possession, shots and the
    # goal-scorer timeline -- all built on top of the scoreline above.
    narrative = build_predicted_narrative(
        req.home_team_id, req.away_team_id,
        home_players, away_players,
        home_formation, away_formation,
        home_team.tactical_profile, away_team.tactical_profile,
        home_score, away_score,
        lambda_home, lambda_away,
        rng,
    )

    events = narrative["events"]
    if went_to_penalties:
        shootout_winner = home_team if penalty_home_score > penalty_away_score else away_team
        events.append(make_event(
            90, "penalty_shootout", req.home_team_id,
            f"PK戦: {home_team.name} {penalty_home_score}-{penalty_away_score} "
            f"{away_team.name} で{shootout_winner.name}が勝利。",
            event_metadata={
                "penalty_home_score": penalty_home_score,
                "penalty_away_score": penalty_away_score,
            },
        ))
    events.append(make_event(90, "fulltime", req.home_team_id, "試合終了。", event_metadata={
        "home_score": home_score, "away_score": away_score,
    }))

    match = Match(
        id=str(uuid.uuid4()),
        group_id=req.group_id,
        round=req.round,
        bracket_slot=req.bracket_slot,
        home_team_id=req.home_team_id,
        away_team_id=req.away_team_id,
        home_formation=home_formation,
        away_formation=away_formation,
        home_lineup=narrative["home_lineup"],
        away_lineup=narrative["away_lineup"],
        home_roster=narrative["home_roster"],
        away_roster=narrative["away_roster"],
        home_score=home_score,
        away_score=away_score,
        went_to_penalties=went_to_penalties,
        penalty_home_score=penalty_home_score,
        penalty_away_score=penalty_away_score,
        status="completed",
        seed=seed,
        data_source="poisson-model",
        home_possession_pct=narrative["home_possession_pct"],
        away_possession_pct=narrative["away_possession_pct"],
        home_shots=narrative["home_shots"],
        away_shots=narrative["away_shots"],
        home_shots_on_target=narrative["home_shots_on_target"],
        away_shots_on_target=narrative["away_shots_on_target"],
        home_yellow_cards=narrative["home_yellow_cards"],
        away_yellow_cards=narrative["away_yellow_cards"],
    )
    db.add(match)
    for e in events:
        db.add(MatchEvent(match_id=match.id, **e))
    db.commit()
    db.refresh(match)
    return match
