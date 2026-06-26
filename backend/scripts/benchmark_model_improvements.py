"""Phase-0 model-improvement benchmark (Dixon-Coles + starting-prob weighting).

Unlike benchmark_ea_accuracy_before_after.py (which varies the DATA under a
fixed model), this varies the MODEL under fixed production ratings and scores
against the 40 real group-stage results. Run it BEFORE and AFTER editing
app/prediction/ratings.py to see the starting-probability effect, and use the
built-in Dixon-Coles rho sweep to pick rho.

Read-only. Usage:
  PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe scripts/benchmark_model_improvements.py [tag]
"""
from __future__ import annotations

import glob
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.prediction.poisson_model import build_match_features, compute_lambda
from app.prediction.model_config import DEFAULT_MODEL_CONFIG

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS = Path(__file__).resolve().parent.parent / "reports"
HOST = {"USA", "MEX", "CAN"}


def load(p):
    return json.loads((SEED / p).read_text(encoding="utf-8"))


def _pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def distribution(lh, la, mx, rho):
    hp = [_pmf(h, lh) for h in range(mx + 1)]
    ap = [_pmf(a, la) for a in range(mx + 1)]
    m = [[hp[h] * ap[a] for a in range(mx + 1)] for h in range(mx + 1)]
    if rho:
        m[0][0] *= 1 - lh * la * rho
        m[0][1] *= 1 + lh * rho
        m[1][0] *= 1 + la * rho
        m[1][1] *= 1 - rho
    for h in range(mx + 1):
        for a in range(mx + 1):
            if m[h][a] < 0:
                m[h][a] = 0.0
    tot = sum(sum(r) for r in m)
    return [[c / tot for c in r] for r in m] if tot else m


def outcome(h, a):
    return "H" if h > a else ("A" if a > h else "D")


def score(rho):
    players = load("players2026_official.json")
    teams = {t["teamId"]: t for t in load("teams2026_official.json")}
    ratings = {r["playerId"]: r for r in load("playerRatings2026_estimated.json")}
    cfg = DEFAULT_MODEL_CONFIG
    by_team = {}
    for p in players:
        r = ratings[p["playerId"]]
        by_team.setdefault(p["teamId"], []).append(
            {"primary_position": p["primaryPosition"], "overall": r["overall"], "attributes": r})

    hits = brier = logloss = rps = egt = 0.0
    n = 0
    for f in sorted(glob.glob(str(SEED / "real_results" / "*.json"))):
        for e in json.loads(Path(f).read_text(encoding="utf-8")):
            h, a = e["home_team_id"], e["away_team_id"]
            if h not in by_team or a not in by_team:
                continue
            ht, at = teams[h], teams[a]
            feat = build_match_features(by_team[h], by_team[a], ht["fifaRank"], at["fifaRank"],
                                        ht.get("tacticalProfile"), at.get("tacticalProfile"))
            lh, la = compute_lambda(feat, cfg, cfg.host_advantage if h in HOST else 0.0,
                                    cfg.host_advantage if a in HOST else 0.0)
            mtx = distribution(lh, la, cfg.max_goals, rho)
            sz = len(mtx)
            pH = sum(mtx[i][j] for i in range(sz) for j in range(sz) if i > j)
            pD = sum(mtx[i][j] for i in range(sz) for j in range(sz) if i == j)
            pA = sum(mtx[i][j] for i in range(sz) for j in range(sz) if i < j)
            act = outcome(e["home_score"], e["away_score"])
            pred = "H" if pH >= pD and pH >= pA else ("A" if pA >= pD else "D")
            hits += 1 if pred == act else 0
            y = {"H": (1, 0, 0), "D": (0, 1, 0), "A": (0, 0, 1)}[act]
            p = (pH, pD, pA)
            brier += sum((p[i] - y[i]) ** 2 for i in range(3))
            logloss += -math.log(max(p[{"H": 0, "D": 1, "A": 2}[act]], 1e-12))
            cp = [pH, pH + pD]
            cy = [y[0], y[0] + y[1]]
            rps += 0.5 * sum((cp[i] - cy[i]) ** 2 for i in range(2))
            egt += abs((lh + la) - (e["home_score"] + e["away_score"]))
            n += 1
    return {"matches": n, "hit_rate": round(hits / n, 4), "rps": round(rps / n, 4),
            "brier": round(brier / n, 4), "log_loss": round(logloss / n, 4),
            "xg_mae_total": round(egt / n, 3)}


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    print(f"=== model benchmark [{tag}] — production ratings, 40 real results ===")
    print(f"{'rho':>6} {'hit':>7} {'RPS':>8} {'Brier':>8} {'LogLoss':>9} {'xGtot':>7}")
    results = {}
    for rho in (0.0, -0.03, -0.05, -0.08, -0.10, -0.13):
        s = score(rho)
        results[rho] = s
        print(f"{rho:>6} {s['hit_rate']:>7} {s['rps']:>8} {s['brier']:>8} {s['log_loss']:>9} {s['xg_mae_total']:>7}")
    out = REPORTS / f"model_benchmark_{tag}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
