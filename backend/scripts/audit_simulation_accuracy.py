"""Read-only audit of the current Poisson prediction model's behavior
(app.prediction.*) -- attack/defense/strength rating spread, top-20
matchup plausibility, host-nation advantage visibility, tactical-modifier
direction, and Monte Carlo underdog/champion-odds sanity checks.

This script never changes any simulation behavior or seed data; it only
reads the existing database/seed data and the current ModelConfig, then
writes a JSON report to backend/reports/. See docs/specs/010 Phase 6.

Usage: ./venv/Scripts/python.exe scripts/audit_simulation_accuracy.py
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.api.matches import team_players_as_dicts
from app.database import SessionLocal
from app.models.team import Team
from app.prediction.model_config import DEFAULT_MODEL_CONFIG
from app.prediction.monte_carlo import HOST_NATIONS, simulate_tournament_outcomes
from app.prediction.poisson_model import _tactical_matchup_modifier, predict_match
from app.prediction.ratings import attack_rating, defense_rating, team_strength_rating

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def minimum_expected_win_pct(rank_gap: int) -> float:
    """A deliberately gentle, rank-gap-scaled bar for "the better-ranked
    team should be at least somewhat favored": two adjacently-ranked top
    teams playing a near-toss-up is normal football, not implausible, so
    the bar starts low and only rises for a genuinely large rank gap."""
    return min(33.0 + max(rank_gap, 0) * 1.2, 55.0)


def is_implausible_favorite(home_win_pct: float, rank_gap: int) -> bool:
    """True when the better FIFA-ranked team (placed at home in the
    comparison) is given less win probability than the rank gap would lead
    you to expect against its worse-ranked opponent -- a deterministic,
    easy-to-eyeball plausibility check, not a claim that upsets can't
    happen."""
    return home_win_pct < minimum_expected_win_pct(rank_gap)


def concentration_metrics(champion_pct: dict, total_teams: int) -> dict:
    """Summarizes how concentrated a champion-odds distribution is versus a
    uniform 1/total_teams baseline."""
    sorted_pct = sorted(champion_pct.values(), reverse=True)
    uniform_pct = round(100.0 / total_teams, 2) if total_teams else 0.0
    top1 = sorted_pct[0] if sorted_pct else 0.0
    top3 = round(sum(sorted_pct[:3]), 1)
    top5 = round(sum(sorted_pct[:5]), 1)

    assessment = "reasonable"
    if top1 >= 25.0 or top3 >= 50.0:
        assessment = "too_concentrated"
    elif len(champion_pct) <= max(4, total_teams // 12):
        assessment = "too_concentrated"
    elif top1 > 0 and top1 < uniform_pct * 1.3:
        assessment = "too_flat"

    return {
        "uniform_pct_if_equal_chance": uniform_pct,
        "top1_champion_pct": top1,
        "top3_champion_pct_sum": top3,
        "top5_champion_pct_sum": top5,
        "teams_with_nonzero_champion_pct": len(champion_pct),
        "assessment": assessment,
    }


def host_advantage_delta(home_win_pct_with_bump: float, home_win_pct_without_bump: float) -> float:
    return round(home_win_pct_with_bump - home_win_pct_without_bump, 1)


def frequent_underperformers(implausible_warnings: list[dict], min_occurrences: int = 3) -> list[dict]:
    """Teams that show up as the better-ranked side in several implausible-
    favorite warnings -- a pattern worth a human look (their squad-derived
    rating may undershoot their FIFA rank), separate from any single
    borderline matchup."""
    counts: dict[str, int] = {}
    for w in implausible_warnings:
        counts[w["home_team_id"]] = counts.get(w["home_team_id"], 0) + 1
    return sorted(
        ({"team_id": tid, "implausible_matchup_count": c} for tid, c in counts.items() if c >= min_occurrences),
        key=lambda r: -r["implausible_matchup_count"],
    )


def compute_team_ratings(db) -> dict:
    teams = db.scalars(select(Team)).all()
    ratings = {}
    for t in teams:
        players = team_players_as_dicts(db, t.id)
        if len(players) < 11:
            continue
        attack = attack_rating(players)
        defense = defense_rating(players)
        strength, confidence = team_strength_rating(t.fifa_rank, players)
        ratings[t.id] = {
            "team_id": t.id,
            "name": t.name,
            "fifa_rank": t.fifa_rank,
            "attack": round(attack, 1),
            "defense": round(defense, 1),
            "strength": round(strength, 1),
            "data_confidence": confidence,
        }
    return ratings


def top_bottom(ratings: dict, key: str, n: int = 5) -> dict:
    items = sorted(ratings.values(), key=lambda r: r[key], reverse=True)
    return {
        "highest": [{"team_id": r["team_id"], key: r[key]} for r in items[:n]],
        "lowest": [{"team_id": r["team_id"], key: r[key]} for r in items[-n:][::-1]],
    }


def top_twenty_matchup_samples(db, ratings: dict) -> tuple[list, list]:
    """Every pairing within the top 20 FIFA-ranked teams (190 pairs) -- cheap
    since predict_match is a closed-form calculation, not a simulation.
    Implausibility is judged against the *actual* numeric FIFA-rank gap
    (ranks can tie), not list position."""
    ranked = sorted((r for r in ratings.values() if r["fifa_rank"] is not None), key=lambda r: r["fifa_rank"])[:20]
    samples = []
    warnings = []
    for i, better in enumerate(ranked):
        home_players = team_players_as_dicts(db, better["team_id"])
        for worse in ranked[i + 1 :]:
            away_players = team_players_as_dicts(db, worse["team_id"])
            pred = predict_match(
                better["team_id"], worse["team_id"], home_players, away_players,
                better["fifa_rank"], worse["fifa_rank"],
            )
            rank_gap = worse["fifa_rank"] - better["fifa_rank"]
            sample = {
                "home_team_id": better["team_id"],
                "away_team_id": worse["team_id"],
                "home_fifa_rank": better["fifa_rank"],
                "away_fifa_rank": worse["fifa_rank"],
                "rank_gap": rank_gap,
                "home_win_pct": pred.home_win_pct,
                "draw_pct": pred.draw_pct,
                "away_win_pct": pred.away_win_pct,
                "home_expected_goals": pred.home_expected_goals,
                "away_expected_goals": pred.away_expected_goals,
            }
            samples.append(sample)
            if is_implausible_favorite(pred.home_win_pct, rank_gap):
                warnings.append({
                    **sample,
                    "warning": (
                        f"{better['team_id']} (FIFA #{better['fifa_rank']}) is given only "
                        f"{pred.home_win_pct}% to beat {worse['team_id']} (FIFA #{worse['fifa_rank']}), "
                        f"a {rank_gap}-rank gap."
                    ),
                })
    return samples, warnings


def reference_opponent(ratings: dict) -> str:
    non_host = [r for r in ratings.values() if r["team_id"] not in HOST_NATIONS]
    non_host.sort(key=lambda r: r["strength"])
    return non_host[len(non_host) // 2]["team_id"]


def host_advantage_check(db, ratings: dict) -> list:
    opponent_id = reference_opponent(ratings)
    opponent = ratings[opponent_id]
    away_players = team_players_as_dicts(db, opponent_id)
    results = []
    for host_id in sorted(HOST_NATIONS):
        if host_id not in ratings:
            continue
        host = ratings[host_id]
        home_players = team_players_as_dicts(db, host_id)
        pred_with = predict_match(
            host_id, opponent_id, home_players, away_players, host["fifa_rank"], opponent["fifa_rank"],
            host_bump_home=DEFAULT_MODEL_CONFIG.host_advantage,
        )
        pred_without = predict_match(
            host_id, opponent_id, home_players, away_players, host["fifa_rank"], opponent["fifa_rank"],
            host_bump_home=0.0,
        )
        results.append({
            "host_team_id": host_id,
            "reference_opponent_id": opponent_id,
            "home_win_pct_with_host_bump": pred_with.home_win_pct,
            "home_win_pct_without_host_bump": pred_without.home_win_pct,
            "delta_pp": host_advantage_delta(pred_with.home_win_pct, pred_without.home_win_pct),
        })
    return results


def tactical_modifier_direction_check(db) -> dict:
    teams = db.scalars(select(Team)).all()
    profiles = {t.id: t.tactical_profile for t in teams if t.tactical_profile}
    if not profiles:
        return {"note": "No tactical_profile data available for this check."}

    highest_press_id, highest_press = max(profiles.items(), key=lambda kv: kv[1].get("press_intensity", 50))
    highest_possession_id, highest_possession = max(profiles.items(), key=lambda kv: kv[1].get("possession_style", 50))
    modifier = _tactical_matchup_modifier(highest_press, highest_possession)
    return {
        "high_press_team_id": highest_press_id,
        "press_intensity": highest_press.get("press_intensity"),
        "high_possession_team_id": highest_possession_id,
        "possession_style": highest_possession.get("possession_style"),
        "tactical_modifier_for_high_press_team_at_home": round(modifier, 4),
        "note": "Positive value nudges expected goals toward the home (high-press) team, per poisson_model.py's documented formula.",
    }


def underdog_and_champion_odds_check(db, ratings: dict, base_seed: int) -> dict:
    ranked = sorted((r for r in ratings.values() if r["fifa_rank"] is not None), key=lambda r: r["fifa_rank"])
    underdog_ids = {r["team_id"] for r in ranked[len(ranked) // 2 :]}

    by_sample_size = {}
    champion_pct_at_500 = {}
    for n in (100, 500):
        sim = simulate_tournament_outcomes(db, iterations=n, base_seed=base_seed)
        by_sample_size[str(n)] = {
            "underdog_champion_pct_sum": round(sum(p for tid, p in sim.champion_pct.items() if tid in underdog_ids), 1),
            "underdog_round_of_16_pct_sum": round(sum(p for tid, p in sim.round_of_16_pct.items() if tid in underdog_ids), 1),
        }
        if n == 500:
            champion_pct_at_500 = sim.champion_pct

    return {
        "underdog_definition": "bottom half of teams by FIFA rank",
        "underdog_team_count": len(underdog_ids),
        "by_sample_size": by_sample_size,
        "champion_pct_at_500_iterations": champion_pct_at_500,
    }


def build_audit_report(db, base_seed: int = 42) -> dict:
    ratings = compute_team_ratings(db)
    matchup_samples, implausible_warnings = top_twenty_matchup_samples(db, ratings)
    host_check = host_advantage_check(db, ratings)
    tactical_check = tactical_modifier_direction_check(db)
    underdog_check = underdog_and_champion_odds_check(db, ratings, base_seed)
    concentration = concentration_metrics(underdog_check["champion_pct_at_500_iterations"], len(ratings))

    underperformers = frequent_underperformers(implausible_warnings)

    warnings = [w["warning"] for w in implausible_warnings]
    for h in host_check:
        if h["delta_pp"] < 1.0:
            warnings.append(f"Host advantage barely visible for {h['host_team_id']}: only {h['delta_pp']}pp shift.")
    if concentration["assessment"] != "reasonable":
        warnings.append(f"Champion odds distribution looks {concentration['assessment']}.")
    for u in underperformers:
        warnings.append(
            f"{u['team_id']} is the better-FIFA-ranked side in {u['implausible_matchup_count']} matchups where the "
            "model still doesn't clearly favor it -- its squad-derived rating may undershoot its FIFA rank."
        )

    recommended_changes = []
    if any(h["delta_pp"] < 1.0 for h in host_check):
        recommended_changes.append(
            "Consider whether host_advantage in ModelConfig should be increased; see Phase 7 for a guardrailed experiment."
        )
    if underperformers:
        recommended_changes.append(
            "Squad-rating review (not a formula change): "
            + ", ".join(f"{u['team_id']} ({u['implausible_matchup_count']} matchups)" for u in underperformers)
            + " consistently underperform their FIFA rank in this model. Worth a Codex review of these teams' "
            "player attributes/qualitative_adjustments rather than a global ModelConfig change."
        )
    if not recommended_changes:
        recommended_changes.append("No formula change is clearly justified by this audit; current constants look reasonable.")

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {"name": "Simulation Accuracy Audit", "modelVersion": DEFAULT_MODEL_CONFIG.model_version},
        "note": (
            "Read-only audit derived from local seed/team data and the current Poisson prediction model. "
            "Does not change any simulation behavior or seed data."
        ),
        "baseSeed": base_seed,
        "ratings": {
            "attack": top_bottom(ratings, "attack"),
            "defense": top_bottom(ratings, "defense"),
            "strength": top_bottom(ratings, "strength"),
        },
        "topTwentyMatchupSample": matchup_samples,
        "implausibleMatchupWarnings": implausible_warnings,
        "frequentRankUnderperformers": underperformers,
        "hostAdvantageCheck": host_check,
        "tacticalModifierCheck": tactical_check,
        "underdogWinRateCheck": underdog_check,
        "championOddsConcentration": concentration,
        "warnings": warnings,
        "recommendedChanges": recommended_changes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = build_audit_report(db, base_seed=args.seed)
    finally:
        db.close()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"simulation_accuracy_audit_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"Warnings: {len(report['warnings'])}")
    for w in report["warnings"]:
        print(f"  - {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
