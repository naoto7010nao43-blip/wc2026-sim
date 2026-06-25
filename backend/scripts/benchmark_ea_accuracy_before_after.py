"""Before/after accuracy benchmark for the EA FC 26 rating injection.

Compares two rating regimes through the *same* Poisson prediction model:

  BEFORE = pure from-scratch estimator (no EA reference, no calibration) --
           i.e. compute_player_rating_v2(p, peers, override, None) for every
           player, exactly the pre-project state.
  AFTER  = production ratings (data/seed/playerRatings2026_estimated.json:
           498 EA-sourced + 171 calibrated-to-EA-scale).

It scores three independent angles, the last against ground truth that is
NOT EA (the 40 real 2026 group-stage results), so the test is a genuine
external-validity check rather than EA grading itself:

  1. Player-overall fidelity vs EA ground truth (how big an error the
     injection closes; AFTER~0 confirms the injection is faithful).
  2. Team squad-strength ordering vs official FIFA ranking (Spearman).
  3. Match-outcome prediction vs the 40 real results: 1X2 hit-rate,
     ranked probability score (RPS), Brier, log-loss, and expected-goals MAE.

Read-only: does not write any seed/rating data. Usage:
  PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe scripts/benchmark_ea_accuracy_before_after.py
"""
from __future__ import annotations

import glob
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rating.formulas import POSITION_GROUPS
from app.rating_v2.player_rating_model import compute_player_rating_v2
from app.prediction.poisson_model import predict_match
from app.prediction.model_config import DEFAULT_MODEL_CONFIG
from app.prediction.ratings import squad_strength_rating

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS = Path(__file__).resolve().parent.parent / "reports"
HOST_NATIONS = {"USA", "MEX", "CAN"}


def load(p):
    return json.loads((SEED / p).read_text(encoding="utf-8"))


def peer_values(players):
    by = {}
    for p in players:
        g = POSITION_GROUPS.get(p["primaryPosition"], "MID")
        v = p.get("marketValueEur")
        if v:
            by.setdefault(g, []).append(v)
    return by


def build_player_dicts(players, ratings_by_id):
    """Shape that app.prediction.ratings expects: primary_position, overall,
    attributes (the rating dict's v2 keys are read by _attr)."""
    by_team = {}
    for p in players:
        r = ratings_by_id[p["playerId"]]
        by_team.setdefault(p["teamId"], []).append({
            "primary_position": p["primaryPosition"],
            "overall": r["overall"],
            "attributes": r,
        })
    return by_team


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    sx = math.sqrt(sum((rx[i] - mx) ** 2 for i in range(n)))
    sy = math.sqrt(sum((ry[i] - my) ** 2 for i in range(n)))
    return cov / (sx * sy) if sx and sy else 0.0


def outcome(hs, as_):
    return "H" if hs > as_ else ("A" if as_ > hs else "D")


def score_predictions(players, ratings_by_id, teams_by_id):
    by_team = build_player_dicts(players, ratings_by_id)
    cfg = DEFAULT_MODEL_CONFIG
    hits = brier = logloss = rps = 0.0
    eg_err_h = eg_err_a = eg_err_tot = 0.0
    n = 0
    rows = []
    for f in sorted(glob.glob(str(SEED / "real_results" / "*.json"))):
        for e in json.loads(Path(f).read_text(encoding="utf-8")):
            h, a = e["home_team_id"], e["away_team_id"]
            if h not in by_team or a not in by_team:
                continue
            ht, at = teams_by_id[h], teams_by_id[a]
            pred = predict_match(
                h, a, by_team[h], by_team[a], ht["fifaRank"], at["fifaRank"],
                ht.get("tacticalProfile"), at.get("tacticalProfile"),
                cfg.host_advantage if h in HOST_NATIONS else 0.0,
                cfg.host_advantage if a in HOST_NATIONS else 0.0,
            )
            pH, pD, pA = pred.home_win_pct / 100, pred.draw_pct / 100, pred.away_win_pct / 100
            act = outcome(e["home_score"], e["away_score"])
            pred_oc = "H" if pH >= pD and pH >= pA else ("A" if pA >= pD else "D")
            hits += 1 if pred_oc == act else 0
            y = {"H": (1, 0, 0), "D": (0, 1, 0), "A": (0, 0, 1)}[act]
            p = (pH, pD, pA)
            brier += sum((p[i] - y[i]) ** 2 for i in range(3))
            p_act = max(p[{"H": 0, "D": 1, "A": 2}[act]], 1e-12)
            logloss += -math.log(p_act)
            # RPS over ordered outcomes H > D > A
            cp = [pH, pH + pD]
            cy = [y[0], y[0] + y[1]]
            rps += 0.5 * sum((cp[i] - cy[i]) ** 2 for i in range(2))
            eg_err_h += abs(pred.home_expected_goals - e["home_score"])
            eg_err_a += abs(pred.away_expected_goals - e["away_score"])
            eg_err_tot += abs((pred.home_expected_goals + pred.away_expected_goals)
                              - (e["home_score"] + e["away_score"]))
            n += 1
            rows.append((h, a, act, pred_oc, round(pH, 2), round(pD, 2), round(pA, 2)))
    return {
        "matches": n,
        "hit_rate": round(hits / n, 4),
        "rps": round(rps / n, 4),
        "brier": round(brier / n, 4),
        "log_loss": round(logloss / n, 4),
        "xg_mae_home": round(eg_err_h / n, 3),
        "xg_mae_away": round(eg_err_a / n, 3),
        "xg_mae_total": round(eg_err_tot / n, 3),
    }, rows


def main():
    players = load("players2026_official.json")
    teams = load("teams2026_official.json")
    teams_by_id = {t["teamId"]: t for t in teams}
    overrides = {o["playerId"]: o for o in (
        json.loads((SEED / "manualPlayerOverrides2026.json").read_text(encoding="utf-8"))
        if (SEED / "manualPlayerOverrides2026.json").exists() else [])}
    external = {e["playerId"]: e for e in load("externalPlayerRatings2026.json")}
    after_list = load("playerRatings2026_estimated.json")
    after_by_id = {r["playerId"]: r for r in after_list}

    pv = peer_values(players)

    # BEFORE: pure estimator, in-process.
    before_by_id = {}
    for p in players:
        g = POSITION_GROUPS.get(p["primaryPosition"], "MID")
        r = compute_player_rating_v2(p, pv.get(g, []), overrides.get(p["playerId"]), None)
        before_by_id[p["playerId"]] = r.to_json_dict()

    # --- Angle 1: player-overall fidelity vs EA ground truth ---
    ea_truth = {pid: e["overall"] for pid, e in external.items()}
    def fidelity(by_id):
        errs = [by_id[pid]["overall"] - ov for pid, ov in ea_truth.items() if pid in by_id]
        mae = sum(abs(x) for x in errs) / len(errs)
        bias = sum(errs) / len(errs)
        within3 = sum(1 for x in errs if abs(x) <= 3) / len(errs)
        return {"n": len(errs), "mae": round(mae, 2), "mean_signed_bias": round(bias, 2),
                "pct_within_3": round(100 * within3, 1)}
    fid_before, fid_after = fidelity(before_by_id), fidelity(after_by_id)

    # --- Angle 2: team squad-strength ordering vs FIFA rank ---
    def team_strengths(by_id):
        out = {}
        for p in players:
            r = by_id[p["playerId"]]
            out.setdefault(p["teamId"], []).append({"overall": r["overall"]})
        return {tid: squad_strength_rating(ps) for tid, ps in out.items()}
    def rank_corr(by_id):
        ts = team_strengths(by_id)
        tids = [t for t in ts if t in teams_by_id]
        strengths = [ts[t] for t in tids]
        ranks = [teams_by_id[t]["fifaRank"] for t in tids]
        # negative because lower FIFA rank = stronger; report magnitude
        return round(-spearman(strengths, ranks), 4)
    corr_before, corr_after = rank_corr(before_by_id), rank_corr(after_by_id)

    # --- Angle 3: match prediction vs real results ---
    pred_before, _ = score_predictions(players, before_by_id, teams_by_id)
    pred_after, rows_after = score_predictions(players, after_by_id, teams_by_id)

    report = {
        "angle1_player_fidelity_vs_EA": {"before": fid_before, "after": fid_after},
        "angle2_squad_strength_vs_fifa_rank_spearman": {"before": corr_before, "after": corr_after},
        "angle3_match_prediction_vs_40_real_results": {"before": pred_before, "after": pred_after},
    }
    out = REPORTS / "ea_accuracy_before_after_2026-06-26.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    def pct(a, b):
        if b == 0:
            return "n/a"
        return f"{(a-b)/b*100:+.1f}%"

    print("=" * 70)
    print("EA FC 26 INJECTION — BEFORE vs AFTER ACCURACY (3 angles)")
    print("=" * 70)
    print("\n[1] Player-overall fidelity vs EA ground truth "
          f"({fid_before['n']} players w/ EA value)")
    print(f"    MAE          before {fid_before['mae']:>6}  ->  after {fid_after['mae']:>6}")
    print(f"    signed bias  before {fid_before['mean_signed_bias']:>6}  ->  after {fid_after['mean_signed_bias']:>6}")
    print(f"    within +-3   before {fid_before['pct_within_3']:>5}% ->  after {fid_after['pct_within_3']:>5}%")
    print("\n[2] Squad-strength vs FIFA-rank ordering (Spearman, higher=better)")
    print(f"    rho          before {corr_before:>6}  ->  after {corr_after:>6}  ({pct(corr_after,corr_before)})")
    print(f"\n[3] Match prediction vs {pred_after['matches']} REAL results (independent ground truth)")
    print(f"    1X2 hit-rate before {pred_before['hit_rate']:>6}  ->  after {pred_after['hit_rate']:>6}  ({pct(pred_after['hit_rate'],pred_before['hit_rate'])})")
    print(f"    RPS (lower)  before {pred_before['rps']:>6}  ->  after {pred_after['rps']:>6}  ({pct(pred_after['rps'],pred_before['rps'])})")
    print(f"    Brier(lower) before {pred_before['brier']:>6}  ->  after {pred_after['brier']:>6}  ({pct(pred_after['brier'],pred_before['brier'])})")
    print(f"    LogLoss(low) before {pred_before['log_loss']:>6}  ->  after {pred_after['log_loss']:>6}  ({pct(pred_after['log_loss'],pred_before['log_loss'])})")
    print(f"    xG MAE total before {pred_before['xg_mae_total']:>6}  ->  after {pred_after['xg_mae_total']:>6}  ({pct(pred_after['xg_mae_total'],pred_before['xg_mae_total'])})")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
