"""Monte Carlo tournament simulation: repeatedly samples every not-yet-
decided match's scoreline from the Poisson model, recomputes the full
group standings / third-place ranking / knockout bracket each time using
the exact same rules-engine functions as the real tournament
(app.services.standings.calculate_standings, app.services.third_place,
app.engine.bracket), and aggregates how often each team reaches each
stage or wins outright.

Already-completed real-world results (app.services.real_results) are
fixed inputs and are never resampled, matching run_full_tournament's
pattern in app.services.tournament. Each iteration works entirely on
unpersisted, in-memory Match-like records -- nothing is written to the
database.
"""

import itertools
import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.matches import team_players_as_dicts
from app.engine.bracket import R32_TEMPLATE, assign_third_place_slots, next_round_pairs
from app.models.match import Match
from app.models.team import Team
from app.prediction.model_config import DEFAULT_MODEL_CONFIG, ModelConfig
from app.prediction.poisson_model import lambdas_from_ratings, sample_scoreline, score_distribution, shootout_win_probability
from app.prediction.ratings import attack_rating, defense_rating, team_strength_rating
from app.services.real_results import load_real_results
from app.services.standings import calculate_standings
from app.services.third_place import rank_third_place_teams
from app.services.tournament import GROUP_LETTERS

HOST_NATIONS = {"USA", "MEX", "CAN"}
DEFAULT_ITERATIONS = 1000

_STAGE_KEYS = ["round_of_32", "round_of_16", "quarterfinal", "semifinal", "final", "champion"]


@dataclass(frozen=True)
class TournamentSimulationResult:
    iterations: int
    model_version: str
    round_of_32_pct: dict[str, float]
    round_of_16_pct: dict[str, float]
    quarterfinal_pct: dict[str, float]
    semifinal_pct: dict[str, float]
    final_pct: dict[str, float]
    champion_pct: dict[str, float]
    data_confidence: str
    explanation: list[str]
    disclaimer: str = "これは予測であり、実際の結果を保証するものではありません。"


@dataclass(frozen=True)
class TournamentPathOpponent:
    team_id: str
    team_name: str
    probability_pct: float


@dataclass(frozen=True)
class TournamentPathStage:
    stage_key: str
    stage_label_ja: str
    reach_pct: float
    most_likely_slot: str | None
    opponent_options: list[TournamentPathOpponent]


@dataclass(frozen=True)
class TournamentPathProjectionResult:
    team_id: str
    team_name: str
    iterations: int
    champion_pct: float
    stages: list[TournamentPathStage]
    model_version: str
    data_confidence: str
    note_ja: str
    disclaimer: str = "これは予測モデルによる到達ルートの集計であり、実際の対戦相手や勝敗を保証するものではありません。"


def _in_memory_match(home_team_id: str, away_team_id: str, home_score: int, away_score: int) -> Match:
    """An unpersisted, in-memory Match record. calculate_standings only
    reads plain attributes off it, so a real DB row is never needed."""
    return Match(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_score=home_score,
        away_score=away_score,
        home_yellow_cards=0,
        away_yellow_cards=0,
        home_red_cards=0,
        away_red_cards=0,
    )


def _build_tournament_projection_context(db: Session, config: ModelConfig):
    teams = db.scalars(select(Team)).all()
    team_names = {t.id: t.name for t in teams}
    fifa_ranks = {t.id: t.fifa_rank for t in teams}
    tactical_profiles = {t.id: t.tactical_profile for t in teams}
    teams_by_group: dict[str, list[str]] = {letter: [] for letter in GROUP_LETTERS}
    for t in teams:
        if t.group_id in teams_by_group:
            teams_by_group[t.group_id].append(t.id)

    ratings: dict[str, tuple[float, float, float, str]] = {}
    for t in teams:
        players = team_players_as_dicts(db, t.id)
        attack = attack_rating(players)
        defense = defense_rating(players)
        strength, confidence = team_strength_rating(t.fifa_rank, players)
        ratings[t.id] = (attack, defense, strength, confidence)
    data_confidence = "estimated" if any(confidence == "estimated" for *_ratings, confidence in ratings.values()) else "official"

    def lambdas_for(home_id: str, away_id: str) -> tuple[float, float]:
        h_attack, h_defense, h_strength, h_conf = ratings[home_id]
        a_attack, a_defense, a_strength, a_conf = ratings[away_id]
        host_bump_home = config.host_advantage if home_id in HOST_NATIONS else 0.0
        host_bump_away = config.host_advantage if away_id in HOST_NATIONS else 0.0
        return lambdas_from_ratings(
            h_attack, h_defense, h_strength, h_conf,
            a_attack, a_defense, a_strength, a_conf,
            tactical_profiles.get(home_id), tactical_profiles.get(away_id),
            host_bump_home, host_bump_away, config,
        )

    def winner_of(home_id: str, away_id: str, rng: random.Random) -> str:
        lam_h, lam_a = lambdas_for(home_id, away_id)
        matrix = score_distribution(lam_h, lam_a, config.max_goals, config.dixon_coles_rho)
        h, a = sample_scoreline(matrix, rng)
        if h != a:
            return home_id if h > a else away_id
        return home_id if rng.random() < shootout_win_probability(lam_h, lam_a) else away_id

    real_results_by_group = load_real_results()
    fixed_group_matches: dict[str, list[Match]] = {letter: [] for letter in GROUP_LETTERS}
    group_matrices: dict[str, dict[tuple[str, str], list[list[float]]]] = {letter: {} for letter in GROUP_LETTERS}
    for letter in GROUP_LETTERS:
        real_results = real_results_by_group.get(letter, {})
        for home_id, away_id in itertools.combinations(sorted(teams_by_group[letter]), 2):
            real_result = real_results.get(frozenset({home_id, away_id}))
            if real_result is not None:
                fixed_group_matches[letter].append(_in_memory_match(
                    real_result["home_team_id"], real_result["away_team_id"],
                    real_result["home_score"], real_result["away_score"],
                ))
            else:
                lam_h, lam_a = lambdas_for(home_id, away_id)
                group_matrices[letter][(home_id, away_id)] = score_distribution(lam_h, lam_a, config.max_goals, config.dixon_coles_rho)

    return teams, team_names, fifa_ranks, fixed_group_matches, group_matrices, winner_of, data_confidence


def simulate_tournament_outcomes(
    db: Session,
    iterations: int = DEFAULT_ITERATIONS,
    base_seed: int = 0,
    config: ModelConfig = DEFAULT_MODEL_CONFIG,
) -> TournamentSimulationResult:
    teams = db.scalars(select(Team)).all()
    team_names = {t.id: t.name for t in teams}
    fifa_ranks = {t.id: t.fifa_rank for t in teams}
    tactical_profiles = {t.id: t.tactical_profile for t in teams}
    teams_by_group: dict[str, list[str]] = {letter: [] for letter in GROUP_LETTERS}
    for t in teams:
        if t.group_id in teams_by_group:
            teams_by_group[t.group_id].append(t.id)

    # Cache each team's attack/defense/strength rating once -- these don't
    # change across iterations, only the random scoreline draws do.
    ratings: dict[str, tuple[float, float, float, str]] = {}
    for t in teams:
        players = team_players_as_dicts(db, t.id)
        attack = attack_rating(players)
        defense = defense_rating(players)
        strength, confidence = team_strength_rating(t.fifa_rank, players)
        ratings[t.id] = (attack, defense, strength, confidence)
    data_confidence = "estimated" if any(confidence == "estimated" for *_ratings, confidence in ratings.values()) else "official"

    def lambdas_for(home_id: str, away_id: str) -> tuple[float, float]:
        h_attack, h_defense, h_strength, h_conf = ratings[home_id]
        a_attack, a_defense, a_strength, a_conf = ratings[away_id]
        host_bump_home = config.host_advantage if home_id in HOST_NATIONS else 0.0
        host_bump_away = config.host_advantage if away_id in HOST_NATIONS else 0.0
        return lambdas_from_ratings(
            h_attack, h_defense, h_strength, h_conf,
            a_attack, a_defense, a_strength, a_conf,
            tactical_profiles.get(home_id), tactical_profiles.get(away_id),
            host_bump_home, host_bump_away, config,
        )

    def winner_of(home_id: str, away_id: str, rng: random.Random) -> str:
        lam_h, lam_a = lambdas_for(home_id, away_id)
        matrix = score_distribution(lam_h, lam_a, config.max_goals, config.dixon_coles_rho)
        h, a = sample_scoreline(matrix, rng)
        if h != a:
            return home_id if h > a else away_id
        return home_id if rng.random() < shootout_win_probability(lam_h, lam_a) else away_id

    real_results_by_group = load_real_results()
    fixed_group_matches: dict[str, list[Match]] = {letter: [] for letter in GROUP_LETTERS}
    group_matrices: dict[str, dict[tuple[str, str], list[list[float]]]] = {letter: {} for letter in GROUP_LETTERS}
    for letter in GROUP_LETTERS:
        real_results = real_results_by_group.get(letter, {})
        for home_id, away_id in itertools.combinations(sorted(teams_by_group[letter]), 2):
            real_result = real_results.get(frozenset({home_id, away_id}))
            if real_result is not None:
                fixed_group_matches[letter].append(_in_memory_match(
                    real_result["home_team_id"], real_result["away_team_id"],
                    real_result["home_score"], real_result["away_score"],
                ))
            else:
                lam_h, lam_a = lambdas_for(home_id, away_id)
                group_matrices[letter][(home_id, away_id)] = score_distribution(lam_h, lam_a, config.max_goals, config.dixon_coles_rho)

    stage_counts: dict[str, dict[str, int]] = {key: {t.id: 0 for t in teams} for key in _STAGE_KEYS}

    def resolve_slot(
        slot: str,
        group_standings: dict,
        third_place_team_by_group: dict[str, str],
        third_place_assignment: dict[str, str],
    ) -> str:
        if slot.startswith("3RD:"):
            source_group = third_place_assignment[slot.removeprefix("3RD:")]
            return third_place_team_by_group[source_group]
        group_letter, position = slot[0], int(slot[1])
        return group_standings[group_letter][position - 1].team_id

    def play_round(participants: list[str], stage_key: str, rng: random.Random) -> list[str]:
        for tid in participants:
            stage_counts[stage_key][tid] += 1
        pairs = next_round_pairs(participants)
        return [winner_of(h, a, rng) for h, a in pairs]

    for i in range(iterations):
        rng = random.Random(base_seed + i)

        group_standings = {}
        for letter in GROUP_LETTERS:
            matches = list(fixed_group_matches[letter])
            for (home_id, away_id), matrix in group_matrices[letter].items():
                h, a = sample_scoreline(matrix, rng)
                matches.append(_in_memory_match(home_id, away_id, h, a))
            group_standings[letter] = calculate_standings(matches, team_names, fifa_ranks)

        third_place_rows = {letter: standings[2] for letter, standings in group_standings.items()}
        qualifying_rankings = [r for r in rank_third_place_teams(third_place_rows) if r.qualified]
        qualifying_third_groups = [r.group_id for r in qualifying_rankings]
        third_place_team_by_group = {r.group_id: r.team_id for r in qualifying_rankings}
        third_place_assignment = assign_third_place_slots(qualifying_third_groups)

        r32_participants = [
            resolve_slot(slot, group_standings, third_place_team_by_group, third_place_assignment)
            for pair in R32_TEMPLATE
            for slot in pair
        ]
        round_of_16_participants = play_round(r32_participants, "round_of_32", rng)
        quarterfinal_participants = play_round(round_of_16_participants, "round_of_16", rng)
        semifinal_participants = play_round(quarterfinal_participants, "quarterfinal", rng)
        finalists = play_round(semifinal_participants, "semifinal", rng)
        for tid in finalists:
            stage_counts["final"][tid] += 1
        champion = winner_of(finalists[0], finalists[1], rng)
        stage_counts["champion"][champion] += 1

    def to_pct(counts: dict[str, int]) -> dict[str, float]:
        return {tid: round(100.0 * c / iterations, 1) for tid, c in counts.items() if c > 0}

    return TournamentSimulationResult(
        iterations=iterations,
        model_version=config.model_version,
        round_of_32_pct=to_pct(stage_counts["round_of_32"]),
        round_of_16_pct=to_pct(stage_counts["round_of_16"]),
        quarterfinal_pct=to_pct(stage_counts["quarterfinal"]),
        semifinal_pct=to_pct(stage_counts["semifinal"]),
        final_pct=to_pct(stage_counts["final"]),
        champion_pct=to_pct(stage_counts["champion"]),
        data_confidence=data_confidence,
        explanation=[
            "未実施試合は攻撃力・守備力・FIFAランク・監督戦術を反映したPoissonモデルで抽選しています。",
            "実結果が登録済みの試合は再抽選せず、固定結果として扱います。",
            "各試行でグループ順位、3位突破、決勝トーナメントを2026大会形式に沿って再計算します。",
        ],
    )


def project_team_tournament_path(
    db: Session,
    team_id: str,
    iterations: int = DEFAULT_ITERATIONS,
    base_seed: int = 0,
    config: ModelConfig = DEFAULT_MODEL_CONFIG,
) -> TournamentPathProjectionResult:
    (
        teams,
        team_names,
        fifa_ranks,
        fixed_group_matches,
        group_matrices,
        winner_of,
        data_confidence,
    ) = _build_tournament_projection_context(db, config)
    if team_id not in team_names:
        raise KeyError(team_id)

    stage_labels = {
        "R32": "ラウンド32",
        "R16": "ラウンド16",
        "QF": "準々決勝",
        "SF": "準決勝",
        "FINAL": "決勝",
    }
    reach_counts = {key: 0 for key in stage_labels}
    opponent_counts: dict[str, dict[str, int]] = {key: {} for key in stage_labels}
    slot_counts: dict[str, dict[str, int]] = {key: {} for key in stage_labels}
    champion_count = 0

    def resolve_slot(
        slot: str,
        group_standings: dict,
        third_place_team_by_group: dict[str, str],
        third_place_assignment: dict[str, str],
    ) -> str:
        if slot.startswith("3RD:"):
            source_group = third_place_assignment[slot.removeprefix("3RD:")]
            return third_place_team_by_group[source_group]
        group_letter, position = slot[0], int(slot[1])
        return group_standings[group_letter][position - 1].team_id

    def record_stage(stage_key: str, pairs: list[tuple[str, str]], slots: list[tuple[str, str]] | None = None) -> None:
        for idx, (home_id, away_id) in enumerate(pairs):
            if team_id not in {home_id, away_id}:
                continue
            opponent_id = away_id if home_id == team_id else home_id
            reach_counts[stage_key] += 1
            opponent_counts[stage_key][opponent_id] = opponent_counts[stage_key].get(opponent_id, 0) + 1
            if slots is not None:
                home_slot, away_slot = slots[idx]
                slot = home_slot if home_id == team_id else away_slot
                slot_counts[stage_key][slot] = slot_counts[stage_key].get(slot, 0) + 1

    def play_pairs(pairs: list[tuple[str, str]], rng: random.Random) -> list[str]:
        return [winner_of(home_id, away_id, rng) for home_id, away_id in pairs]

    for i in range(iterations):
        rng = random.Random(base_seed + i)

        group_standings = {}
        for letter in GROUP_LETTERS:
            matches = list(fixed_group_matches[letter])
            for (home_id, away_id), matrix in group_matrices[letter].items():
                h, a = sample_scoreline(matrix, rng)
                matches.append(_in_memory_match(home_id, away_id, h, a))
            group_standings[letter] = calculate_standings(matches, team_names, fifa_ranks)

        third_place_rows = {letter: standings[2] for letter, standings in group_standings.items()}
        qualifying_rankings = [r for r in rank_third_place_teams(third_place_rows) if r.qualified]
        qualifying_third_groups = [r.group_id for r in qualifying_rankings]
        third_place_team_by_group = {r.group_id: r.team_id for r in qualifying_rankings}
        third_place_assignment = assign_third_place_slots(qualifying_third_groups)

        r32_pairs = [
            (
                resolve_slot(slot_a, group_standings, third_place_team_by_group, third_place_assignment),
                resolve_slot(slot_b, group_standings, third_place_team_by_group, third_place_assignment),
            )
            for slot_a, slot_b in R32_TEMPLATE
        ]
        record_stage("R32", r32_pairs, R32_TEMPLATE)
        r16_participants = play_pairs(r32_pairs, rng)

        r16_pairs = next_round_pairs(r16_participants)
        record_stage("R16", r16_pairs)
        qf_participants = play_pairs(r16_pairs, rng)

        qf_pairs = next_round_pairs(qf_participants)
        record_stage("QF", qf_pairs)
        sf_participants = play_pairs(qf_pairs, rng)

        sf_pairs = next_round_pairs(sf_participants)
        record_stage("SF", sf_pairs)
        finalists = play_pairs(sf_pairs, rng)

        final_pairs = [(finalists[0], finalists[1])]
        record_stage("FINAL", final_pairs)
        champion = winner_of(finalists[0], finalists[1], rng)
        if champion == team_id:
            champion_count += 1

    def pct(count: int) -> float:
        return round(100.0 * count / iterations, 1)

    stages: list[TournamentPathStage] = []
    for stage_key, stage_label in stage_labels.items():
        opponents = sorted(
            opponent_counts[stage_key].items(),
            key=lambda item: (-item[1], team_names.get(item[0], item[0])),
        )[:5]
        slots = sorted(slot_counts[stage_key].items(), key=lambda item: (-item[1], item[0]))
        stages.append(
            TournamentPathStage(
                stage_key=stage_key,
                stage_label_ja=stage_label,
                reach_pct=pct(reach_counts[stage_key]),
                most_likely_slot=slots[0][0] if slots else None,
                opponent_options=[
                    TournamentPathOpponent(
                        team_id=opponent_id,
                        team_name=team_names.get(opponent_id, opponent_id),
                        probability_pct=pct(count),
                    )
                    for opponent_id, count in opponents
                ],
            )
        )

    selected_team = next(t for t in teams if t.id == team_id)
    group_label = selected_team.group_id or "未設定"
    return TournamentPathProjectionResult(
        team_id=team_id,
        team_name=team_names[team_id],
        iterations=iterations,
        champion_pct=pct(champion_count),
        stages=stages,
        model_version=config.model_version,
        data_confidence=data_confidence,
        note_ja=f"{team_names[team_id]}（Group {group_label}）の想定ルートです。各ラウンドの相手候補は全試行回数に対する出現率で、到達した場合の条件付き確率ではありません。",
    )
