"""Normalization helpers shared by player_rating_model.py. Kept separate
since these are generic, reusable scoring primitives (not football-domain
logic), matching the user's spec's normalization.ts split.
"""

import math

from app.rating.formulas import percentile_rank


def market_value_score(value_eur: float | None, peer_values_eur: list[float]) -> tuple[float, bool]:
    """0-100 score from a log-scaled percentile within the player's
    position-group peers, so a handful of superstar valuations don't
    compress everyone else into the bottom of the scale. Returns
    (score, was_known) -- callers must raise uncertainty and use a
    neutral default (peer median, i.e. score=50) rather than zero when
    was_known is False, per the "don't treat missing as zero" rule.
    """
    if value_eur is None or value_eur <= 0:
        return 50.0, False
    log_peers = [math.log1p(v) for v in peer_values_eur if v and v > 0]
    if not log_peers:
        return 50.0, False
    pct = percentile_rank(math.log1p(value_eur), log_peers)
    return pct * 100.0, True


def age_curve_score(age: int | None) -> tuple[float, bool]:
    """0-100 score peaking in the mid-to-late 20s (a standard football
    aging-curve shape), flat near the peak rather than a sharp spike so a
    23-year-old and a 27-year-old aren't penalized much relative to each
    other. Returns (score, was_known)."""
    if age is None:
        return 60.0, False
    if age <= 21:
        return max(40.0, 55.0 + (age - 21) * 3.0), True
    if age <= 29:
        return 70.0 + min(age - 21, 8) * 1.5, True
    # Gentle decline after 29, steeper past 33 -- mirrors the existing
    # Stage B age-damping rationale in app/rating/formulas.py.
    decline = (age - 29) * 2.2 if age <= 33 else 8.8 + (age - 33) * 3.5
    return max(35.0, 82.0 - decline), True


def clamp(value: float, lo: float = 35.0, hi: float = 95.0) -> int:
    return int(round(max(lo, min(hi, value))))
