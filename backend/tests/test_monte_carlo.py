import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.match import Match  # noqa: F401  (ensures table is registered with Base.metadata)
from app.models.player import Player
from app.models.team import Team
from app.prediction.monte_carlo import (
    project_dark_horses,
    project_final_matchups,
    project_group_advancement,
    project_team_tournament_path,
    simulate_tournament_outcomes,
)
from app.rating.seed_pipeline import build_player_rows, load_seed_data


def _make_seeded_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    teams_raw, players_raw = load_seed_data()
    player_rows = build_player_rows(players_raw)

    for t in teams_raw:
        session.add(Team(
            id=t["id"],
            name=t["name"],
            confederation=t["confederation"],
            fifa_rank=t.get("fifa_rank"),
            default_formation=t["default_formation"],
            group_id=t.get("group_id"),
            tactical_profile=t.get("tactical_profile"),
        ))
    session.flush()
    for p in player_rows:
        session.add(Player(**p))
    session.commit()
    return session


@pytest.fixture()
def db_session():
    session = _make_seeded_session()
    try:
        yield session
    finally:
        session.close()


def test_monte_carlo_is_deterministic_given_the_same_seed(db_session):
    result1 = simulate_tournament_outcomes(db_session, iterations=20, base_seed=7)
    result2 = simulate_tournament_outcomes(db_session, iterations=20, base_seed=7)
    assert result1.champion_pct == result2.champion_pct
    assert result1.round_of_32_pct == result2.round_of_32_pct
    assert result1.data_confidence in {"official", "estimated"}
    assert result1.explanation


def test_monte_carlo_stage_percentages_sum_to_expected_slot_counts(db_session):
    iterations = 30
    result = simulate_tournament_outcomes(db_session, iterations=iterations, base_seed=1)

    # Exactly 32/16/8/4/2/1 teams occupy each stage every single iteration,
    # so the percentages across all teams at that stage must sum to
    # 100 * slot_count (within float rounding).
    assert abs(sum(result.round_of_32_pct.values()) - 3200) < 5
    assert abs(sum(result.round_of_16_pct.values()) - 1600) < 5
    assert abs(sum(result.quarterfinal_pct.values()) - 800) < 5
    assert abs(sum(result.semifinal_pct.values()) - 400) < 5
    assert abs(sum(result.final_pct.values()) - 200) < 5
    assert abs(sum(result.champion_pct.values()) - 100) < 5
    assert len(result.champion_pct) >= 1


def test_team_path_projection_is_deterministic_given_the_same_seed(db_session):
    result1 = project_team_tournament_path(db_session, team_id="JPN", iterations=20, base_seed=11)
    result2 = project_team_tournament_path(db_session, team_id="JPN", iterations=20, base_seed=11)
    assert result1.champion_pct == result2.champion_pct
    assert result1.stages == result2.stages
    assert [stage.stage_key for stage in result1.stages] == ["R32", "R16", "QF", "SF", "FINAL"]


def test_final_matchups_are_deterministic_given_the_same_seed(db_session):
    result1 = project_final_matchups(db_session, iterations=20, base_seed=13, limit=5)
    result2 = project_final_matchups(db_session, iterations=20, base_seed=13, limit=5)
    assert result1.candidates == result2.candidates
    assert result1.matchup_count >= len(result1.candidates) > 0
    for candidate in result1.candidates:
        assert candidate.team_a_id != candidate.team_b_id
        assert candidate.champion_favorite_team_id in {candidate.team_a_id, candidate.team_b_id}


def test_dark_horses_are_deterministic_and_exclude_top_ranked_favorites(db_session):
    result1 = project_dark_horses(db_session, iterations=30, base_seed=17, limit=6)
    result2 = project_dark_horses(db_session, iterations=30, base_seed=17, limit=6)
    assert result1.candidates == result2.candidates
    assert result1.candidate_count >= len(result1.candidates) > 0
    scores = [candidate.surprise_score for candidate in result1.candidates]
    assert scores == sorted(scores, reverse=True)
    for candidate in result1.candidates:
        assert candidate.fifa_rank is None or candidate.fifa_rank > 12
        assert candidate.quarterfinal_pct >= 8.0 or candidate.champion_pct >= 0.8
        assert candidate.reason_ja


def test_group_advancement_is_deterministic_and_balanced_by_group(db_session):
    result1 = project_group_advancement(db_session, iterations=30, base_seed=19)
    result2 = project_group_advancement(db_session, iterations=30, base_seed=19)
    assert result1.groups == result2.groups
    assert len(result1.groups) == 12
    total_advance_pct = 0.0
    for group in result1.groups:
        assert len(group.teams) == 4
        assert abs(sum(team.first_place_pct for team in group.teams) - 100.0) < 1.0
        assert abs(sum(team.second_place_pct for team in group.teams) - 100.0) < 1.0
        total_advance_pct += sum(team.advance_pct for team in group.teams)
        for team in group.teams:
            assert 0 <= team.advance_pct <= 100
            assert team.advance_pct >= team.first_place_pct + team.second_place_pct - 0.2
            assert team.average_points >= 0
    assert abs(total_advance_pct - 3200.0) < 8.0


def test_monte_carlo_disclaimer_present(db_session):
    result = simulate_tournament_outcomes(db_session, iterations=10, base_seed=0)
    assert "予測" in result.disclaimer
    assert "縺" not in result.disclaimer
    assert "繝" not in result.disclaimer


def test_monte_carlo_performance_benchmark(db_session):
    # Not a strict assertion of a specific threshold -- this exists to
    # surface a concrete number for the iteration-count tuning decision
    # documented in the project plan (Poisson-based sampling should be far
    # cheaper than the old minute-by-minute micro-simulator).
    start = time.perf_counter()
    simulate_tournament_outcomes(db_session, iterations=200, base_seed=0)
    elapsed = time.perf_counter() - start
    print(f"\nMonte Carlo: 200 iterations took {elapsed:.2f}s ({elapsed / 200 * 1000:.1f}ms/iteration)")
    assert elapsed < 60  # generous ceiling; real number is reported above for tuning
