"""Recomputes playerRatings2026_estimated.json and
managerRatings2026_estimated.json from players2026_official.json /
managers2026_official.json / teams2026_official.json /
manualPlayerOverrides2026.json, via app.rating_v2.player_rating_model /
manager_rating_model. Also writes a diff report (vs. the previous
ratings file, if one exists) to reports/player_rating_diff_<date>.json
and refreshes metadata.json's lastUpdated.

Safe to re-run at any time (e.g. after editing manualPlayerOverrides2026.json
or after players2026_official.json changes).

Usage: ./venv/Scripts/python.exe scripts/rebuild_player_ratings_v2.py
"""

import json
import sys
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rating.formulas import POSITION_GROUPS
from app.rating_v2.manager_rating_model import compute_manager_rating_v2
from app.rating_v2.player_rating_model import compute_player_rating_v2, compute_starting_probabilities

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

LOW_CONFIDENCE_UNCERTAINTY_THRESHOLD = 0.5

# Calibration of estimated (non-EA-sourced) players onto the EA-anchored scale.
# The from-scratch estimator systematically compresses the top of the scale
# (proven: ~+21 median gap vs EA across the full quality range, on the 400+
# player EA overlap). Left uncorrected, estimated players sit a whole tier
# below their EA-sourced team-mates and opponents -- which would, e.g., make
# nations whose squads are thin in FC26 (Iran, South Africa, Uzbekistan...)
# systematically under-strength in the simulation. We therefore shift each
# estimated player's base onto the EA scale using the monotonic est->EA mapping
# fit from the overlap. Two honesty guards:
#   * SHRINK (<1): unmatched players skew toward weaker domestic leagues, so
#     they are probably a little weaker than the (big-league-skewed) overlap
#     players at the same estimated value. We apply only part of the fitted
#     gap rather than assume they equal the overlap mean.
#   * MAX_SHIFT: caps extrapolation for very low estimates.
# Calibrated players keep dataConfidence "estimated" and carry an extra
# uncertainty penalty + sourceBreakdown.calibrationApplied=True.
CALIBRATION_SHRINK = 0.7
CALIBRATION_MAX_SHIFT = 20


def _fit_monotonic_est_to_ea(pairs: list[tuple[int, int]]):
    """Isotonic (pool-adjacent-violators) fit of estimated overall -> EA
    overall. Returns a callable mapping any estimated overall to a
    non-decreasing EA-scale target, linearly interpolating between observed
    knots and clamping flat outside the observed range."""
    if not pairs:
        return lambda est: est
    agg: dict[int, list[int]] = {}
    for est, ea in pairs:
        agg.setdefault(est, []).append(ea)
    xs = sorted(agg)
    ys = [sum(agg[x]) / len(agg[x]) for x in xs]
    ws = [len(agg[x]) for x in xs]
    # PAV: enforce non-decreasing ys.
    i = 0
    blocks = [[x, y, w] for x, y, w in zip(xs, ys, ws)]
    while i < len(blocks) - 1:
        if blocks[i][1] <= blocks[i + 1][1]:
            i += 1
        else:
            x0, y0, w0 = blocks[i]
            x1, y1, w1 = blocks[i + 1]
            merged = [x0, (y0 * w0 + y1 * w1) / (w0 + w1), w0 + w1]
            blocks[i:i + 2] = [merged]
            if i > 0:
                i -= 1
    knot_x = [b[0] for b in blocks]
    knot_y = [b[1] for b in blocks]

    def mapping(est: float) -> float:
        if est <= knot_x[0]:
            return knot_y[0]
        if est >= knot_x[-1]:
            return knot_y[-1]
        for j in range(len(knot_x) - 1):
            if knot_x[j] <= est <= knot_x[j + 1]:
                t = (est - knot_x[j]) / (knot_x[j + 1] - knot_x[j])
                return knot_y[j] + t * (knot_y[j + 1] - knot_y[j])
        return knot_y[-1]

    return mapping


def _calibration_shift_for(est_overall: int, mapping) -> int:
    """Non-negative, shrunk, capped EA-scale shift for one estimated player."""
    raw_gap = mapping(est_overall) - est_overall
    shift = round(CALIBRATION_SHRINK * max(0.0, raw_gap))
    return int(max(0, min(CALIBRATION_MAX_SHIFT, shift)))


def _load(name: str):
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _peer_market_values(players: list[dict]) -> dict[str, list[float]]:
    by_group: dict[str, list[float]] = {}
    for p in players:
        group = POSITION_GROUPS.get(p["primaryPosition"], "MID")
        value = p.get("marketValueEur")
        if value:
            by_group.setdefault(group, []).append(value)
    return by_group


def _overrides_by_player_id(overrides: list[dict]) -> dict[str, dict]:
    return {o["playerId"]: o for o in overrides}


def _external_refs_by_player_id(external: list[dict]) -> dict[str, dict]:
    """Keyed by playerId. Each entry is a sourced EA-FC-26-style rating
    (overall + six face stats, or GK variants) that compute_player_rating_v2
    injects in place of the from-scratch estimation for that one player."""
    return {e["playerId"]: e for e in external}


def main():
    players = _load("players2026_official.json")
    teams = _load("teams2026_official.json")
    managers = _load("managers2026_official.json")
    overrides_path = SEED_DIR / "manualPlayerOverrides2026.json"
    overrides = json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.exists() else []
    external_path = SEED_DIR / "externalPlayerRatings2026.json"
    external = json.loads(external_path.read_text(encoding="utf-8")) if external_path.exists() else []

    peer_values_by_group = _peer_market_values(players)
    overrides_by_id = _overrides_by_player_id(overrides)
    external_by_id = _external_refs_by_player_id(external)

    previous_ratings_by_id: dict[str, dict] = {}
    ratings_path = SEED_DIR / "playerRatings2026_estimated.json"
    if ratings_path.exists():
        previous_ratings_by_id = {r["playerId"]: r for r in json.loads(ratings_path.read_text(encoding="utf-8"))}

    players_by_id = {p["playerId"]: p for p in players}

    # Pass 1: EA-sourced players get their external rating; everyone else gets
    # the from-scratch estimate. Also record the (estimated overall, EA overall)
    # overlap -- estimating each externally-sourced player a second time WITHOUT
    # its reference -- to fit the calibration mapping.
    ratings_by_id: dict[str, object] = {}
    overlap_pairs: list[tuple[int, int]] = []
    for p in players:
        pid = p["playerId"]
        group = POSITION_GROUPS.get(p["primaryPosition"], "MID")
        peers = peer_values_by_group.get(group, [])
        ext = external_by_id.get(pid)
        rating = compute_player_rating_v2(p, peers, overrides_by_id.get(pid), ext)
        ratings_by_id[pid] = rating
        if ext is not None:
            est_only = compute_player_rating_v2(p, peers, overrides_by_id.get(pid), None)
            overlap_pairs.append((est_only.overall, int(ext["overall"])))

    # Pass 2: calibrate the estimated players onto the EA-anchored scale.
    mapping = _fit_monotonic_est_to_ea(overlap_pairs)
    calibrated_ids: list[str] = []
    for pid, rating in list(ratings_by_id.items()):
        if rating.source_breakdown.external_reference_used:
            continue
        if overrides_by_id.get(pid):  # respect manual overrides verbatim
            continue
        shift = _calibration_shift_for(rating.overall, mapping)
        if shift <= 0:
            continue
        p = players_by_id[pid]
        group = POSITION_GROUPS.get(p["primaryPosition"], "MID")
        ratings_by_id[pid] = compute_player_rating_v2(
            p, peer_values_by_group.get(group, []), None, None, calibration_shift=shift
        )
        calibrated_ids.append(pid)

    starting_prob_by_id = compute_starting_probabilities(players, ratings_by_id)
    new_ratings = []
    for p in players:
        rating = replace(ratings_by_id[p["playerId"]], starting_probability=starting_prob_by_id[p["playerId"]])
        new_ratings.append(rating.to_json_dict())

    team_by_code = {t["teamCode"]: t for t in teams}
    new_manager_ratings = []
    for m in managers:
        team = team_by_code.get(m["teamCode"], {})
        rating = compute_manager_rating_v2(m["managerId"], m["teamCode"], team.get("tacticalProfile"))
        new_manager_ratings.append(rating.to_json_dict())

    ratings_path.write_text(json.dumps(new_ratings, indent=2, ensure_ascii=False), encoding="utf-8")
    (SEED_DIR / "managerRatings2026_estimated.json").write_text(
        json.dumps(new_manager_ratings, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Diff report.
    biggest_risers, biggest_fallers = [], []
    for r in new_ratings:
        prev = previous_ratings_by_id.get(r["playerId"])
        if prev is None:
            continue
        delta = r["overall"] - prev["overall"]
        if delta != 0:
            (biggest_risers if delta > 0 else biggest_fallers).append({
                "playerId": r["playerId"], "delta": delta, "from": prev["overall"], "to": r["overall"],
            })
    biggest_risers.sort(key=lambda x: -x["delta"])
    biggest_fallers.sort(key=lambda x: x["delta"])

    low_confidence_players = [
        {"playerId": r["playerId"], "uncertainty": r["uncertainty"], "dataConfidence": r["dataConfidence"]}
        for r in new_ratings if r["uncertainty"] >= LOW_CONFIDENCE_UNCERTAINTY_THRESHOLD
    ]
    missing_critical_data = [
        r["playerId"] for r in new_ratings if r["dataConfidence"] == "missing"
    ]
    changed_by_manual_override = [
        r["playerId"] for r in new_ratings if r["sourceBreakdown"]["manualOverrideUsed"]
    ]
    externally_sourced = [
        r["playerId"] for r in new_ratings if r["sourceBreakdown"].get("externalReferenceUsed")
    ]
    calibrated = [
        r["playerId"] for r in new_ratings if r["sourceBreakdown"].get("calibrationApplied")
    ]

    report = {
        "generatedAt": _now_iso(),
        "totalPlayers": len(new_ratings),
        "biggestRisers": biggest_risers[:10],
        "biggestFallers": biggest_fallers[:10],
        "changedByManualOverride": changed_by_manual_override,
        "externallySourced": externally_sourced,
        "calibratedToEaScale": calibrated,
        "lowConfidencePlayers": low_confidence_players,
        "missingCriticalData": missing_critical_data,
    }
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"player_rating_diff_{date.today().isoformat()}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    metadata_path = SEED_DIR / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["lastUpdated"] = _now_iso()
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Rebuilt {len(new_ratings)} player ratings, {len(new_manager_ratings)} manager ratings.")
    print(f"Externally-sourced (EA FC 26) players: {len(externally_sourced)}")
    print(f"Calibrated-to-EA-scale (estimated) players: {len(calibrated)}")
    print(f"Low-confidence players (uncertainty >= {LOW_CONFIDENCE_UNCERTAINTY_THRESHOLD}): {len(low_confidence_players)}")
    print(f"Missing-critical-data players: {len(missing_critical_data)}")
    print(f"Diff report written to {report_path}")


if __name__ == "__main__":
    main()
