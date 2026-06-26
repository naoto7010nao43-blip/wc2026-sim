"""Team-level strength signals derived only from data that already exists
in this project: the v2 player attributes (finishing/shotPower/
chanceCreation/ballCarrying/crossing/setPiece/tackling/interception/
aerialDefense/goalkeeper* etc., see app/rating_v2/types.py) and each
team's official FIFA ranking. Falls back to the older 6+2 attributes
(shooting/dribbling/passing/defending/physical/gk_reflexes/gk_handling)
when a player's v2 attributes aren't present in Player.attributes (e.g.
the non-v2 seed pipeline was used), so this module degrades gracefully
rather than silently flattening every player to a default score.

These are *estimated* internal signals, not a maintained historical Elo
rating -- there is no real published rating history backing them, so they
must never be presented to users as "Elo". See model_config.py.
"""

from app.rating.formulas import POSITION_GROUPS

_BENCH_CUTOFF = 8  # only the strongest contributors per unit move the rating; deep bench depth matters less for a single match
_DEFAULT_SCORE = 50.0
_FIFA_RANK_WEIGHT = 0.75
_SQUAD_STRENGTH_WEIGHT = 0.25


def _position_group(player: dict) -> str:
    return POSITION_GROUPS.get(player["primary_position"], "MID")


def _attr(attrs: dict, v2_key: str, legacy_key: str) -> float:
    """Prefers the finer-grained v2 attribute; falls back to its nearest
    legacy 6+2 equivalent, then to a neutral default if neither is set."""
    value = attrs.get(v2_key)
    if value is None:
        value = attrs.get(legacy_key)
    return value if value is not None else _DEFAULT_SCORE


def _weighted_avg(values_and_weights: list[tuple[float, float]], default: float = _DEFAULT_SCORE) -> float:
    total_weight = sum(w for _, w in values_and_weights)
    if total_weight == 0:
        return default
    return sum(v * w for v, w in values_and_weights) / total_weight


_NEUTRAL_STARTING_PROBABILITY = 50.0


def _playing_factor(player: dict) -> float:
    """How much this player should move the team rating, based on how likely
    they are to actually start (startingProbability) and be available -- so a
    high-`overall` backup or an injured star doesn't inflate squad strength
    the way a nailed-on starter does. Both signals already exist per player
    in Player.attributes (see app.rating_v2.legacy_bridge). Falls back to a
    neutral constant when absent, which -- being constant across the squad --
    leaves the prior overall-ranked behavior unchanged (e.g. in tests that
    pass bare player dicts)."""
    attrs = player.get("attributes") or {}
    sp = attrs.get("startingProbability")
    av = attrs.get("availability")
    sp = sp if sp is not None else _NEUTRAL_STARTING_PROBABILITY
    av = av if av is not None else 100.0
    return max(0.0, sp / 100.0) * max(0.0, av / 100.0)


def _effective_overall(player: dict) -> float:
    """Selection key: rank candidates by quality discounted by how likely
    they are to actually feature, so the 'effective XI' is the players who
    will really take the field, not just the highest-rated names on paper."""
    return player["overall"] * _playing_factor(player)


def attack_rating(players: list[dict]) -> float:
    """Squad's attacking quality, weighted toward forwards and toward the
    strongest contributors (rather than a flat full-squad average):
    finishing and shot power for raw goal threat, chance creation and
    ball carrying for buildup, crossing and set pieces for secondary
    routes to goal."""
    contributors = [p for p in players if _position_group(p) in ("FWD", "MID")]
    if not contributors:
        return _DEFAULT_SCORE
    contributors = sorted(contributors, key=lambda p: -_effective_overall(p))[:_BENCH_CUTOFF]
    scored = []
    for p in contributors:
        attrs = p["attributes"]
        weight = (1.5 if _position_group(p) == "FWD" else 1.0) * _playing_factor(p)
        score = (
            _attr(attrs, "finishing", "shooting") * 0.35
            + _attr(attrs, "shotPower", "shooting") * 0.15
            + _attr(attrs, "chanceCreation", "passing") * 0.25
            + _attr(attrs, "ballCarrying", "dribbling") * 0.15
            + _attr(attrs, "crossing", "passing") * 0.05
            + _attr(attrs, "setPiece", "shooting") * 0.05
        )
        scored.append((score, weight))
    return _weighted_avg(scored)


def defense_rating(players: list[dict]) -> float:
    """Squad's defensive quality: tackling/interception/aerial duels of its
    DEF and MID players (weighted toward defenders), blended with
    goalkeeping quality from the best-rated goalkeeper."""
    contributors = [p for p in players if _position_group(p) in ("DEF", "MID")]
    outfield_score = _DEFAULT_SCORE
    if contributors:
        contributors = sorted(contributors, key=lambda p: -_effective_overall(p))[:_BENCH_CUTOFF]
        scored = []
        for p in contributors:
            attrs = p["attributes"]
            weight = (1.5 if _position_group(p) == "DEF" else 1.0) * _playing_factor(p)
            score = (
                _attr(attrs, "tackling", "defending") * 0.4
                + _attr(attrs, "interception", "defending") * 0.3
                + _attr(attrs, "aerialDefense", "physical") * 0.2
                + _attr(attrs, "strength", "physical") * 0.1
            )
            scored.append((score, weight))
        outfield_score = _weighted_avg(scored)

    keepers = [p for p in players if _position_group(p) == "GK"]
    gk_score = _DEFAULT_SCORE
    if keepers:
        best_gk = max(keepers, key=_effective_overall)
        attrs = best_gk["attributes"]
        gk_score = (
            _attr(attrs, "goalkeeperReflexes", "gk_reflexes") * 0.5
            + _attr(attrs, "goalkeeperHandling", "gk_handling") * 0.3
            + _attr(attrs, "goalkeeperDistribution", "gk_handling") * 0.2
        )

    return outfield_score * 0.75 + gk_score * 0.25


def squad_strength_rating(players: list[dict]) -> float:
    """Plain overall-rating average across the likely best XI (top 11 by
    playing-likelihood-discounted `overall`, see _effective_overall) -- a
    coarse whole-team strength signal."""
    if not players:
        return 50.0
    best_xi = sorted(players, key=lambda p: -_effective_overall(p))[:11]
    return sum(p["overall"] for p in best_xi) / len(best_xi)


def team_strength_rating(fifa_rank: int | None, players: list[dict]) -> tuple[float, str]:
    """A single blended team-strength number combining FIFA's official
    ranking (when known) with the squad's attribute-derived strength, so a
    team's actual named players still move the number rather than just
    their federation's rank. Returns (rating, data_confidence) -- always
    "estimated", since this blend itself is not an officially published
    figure even when fifa_rank is "official" data.
    """
    squad = squad_strength_rating(players)
    if fifa_rank is None:
        return squad, "estimated"
    # Heuristic, monotonic rank->score mapping (not derived from any
    # backtested formula yet -- see project roadmap for calibration):
    # rank 1 maps near 95, decaying with diminishing returns for lower-
    # ranked teams.
    rank_score = max(35.0, 95.0 - 8.0 * ((fifa_rank ** 0.5) - 1))
    blended = rank_score * _FIFA_RANK_WEIGHT + squad * _SQUAD_STRENGTH_WEIGHT
    return blended, "estimated"
