"""FIFA World Cup 2026 official tiebreaker cascade, implemented as pure
functions over plain data (no DB access, no mutation of inputs).

Verified 2026-06 against FIFA's own tournament explainer and an
independent press cross-check (MLSSoccer.com), since the order changed for
2026 relative to earlier tournaments:

Group stage (teams tied on points):
  1. points obtained in matches between the tied teams (head-to-head)
  2. goal difference in those head-to-head matches
  3. goals scored in those head-to-head matches
     -- if some but not all teams are separated by 1-3, the same
        head-to-head comparison is re-applied to whichever teams remain
        tied, using only the matches between *that* smaller group.
  4. goal difference in all group matches (overall)
  5. goals scored in all group matches (overall)
  6. team conduct (fewest disciplinary points)
  7. FIFA World Ranking (better/lower rank wins)
  8. unresolved (no further official criterion)

Third-place ranking across groups (Step 1-3 do not apply -- these teams
never played each other): points -> overall goal difference -> overall
goals scored -> conduct -> FIFA World Ranking -> unresolved.
"""

from dataclasses import dataclass
from typing import Sequence

from app.models.match import Match

REASON_POINTS = "points"
REASON_H2H_POINTS = "head_to_head_points"
REASON_H2H_GOAL_DIFF = "head_to_head_goal_diff"
REASON_H2H_GOALS_FOR = "head_to_head_goals_for"
REASON_OVERALL_GOAL_DIFF = "overall_goal_diff"
REASON_OVERALL_GOALS_FOR = "overall_goals_for"
REASON_CONDUCT = "conduct_score"
REASON_FIFA_RANK = "fifa_rank"
REASON_UNRESOLVED = "unresolved"

CONDUCT_YELLOW_POINTS = 1
CONDUCT_RED_POINTS = 4


@dataclass(frozen=True)
class TeamAggregate:
    team_id: str
    points: int
    goal_diff: int
    goals_for: int


def compute_conduct_scores(matches: Sequence[Match]) -> dict[str, int]:
    """FIFA disciplinary points (fewer is better): yellow card = 1pt, red
    card = 4pt. Match rows only store aggregate yellow/red counts per team
    (not whether a red was direct or a second yellow), so both red-card
    forms score identically -- the common case in practice."""
    scores: dict[str, int] = {}
    for m in matches:
        for team_id, yellows, reds in (
            (m.home_team_id, m.home_yellow_cards, m.home_red_cards),
            (m.away_team_id, m.away_yellow_cards, m.away_red_cards),
        ):
            scores[team_id] = (
                scores.get(team_id, 0)
                + (yellows or 0) * CONDUCT_YELLOW_POINTS
                + (reds or 0) * CONDUCT_RED_POINTS
            )
    return scores


def _cluster_by(ids: Sequence[str], key_fn) -> list[list[str]]:
    """Sorts `ids` by `key_fn` and groups adjacent ids whose key is
    exactly equal (i.e. still tied) into the same cluster."""
    ordered = sorted(ids, key=key_fn)
    clusters: list[list[str]] = []
    for i in ordered:
        if clusters and key_fn(clusters[-1][0]) == key_fn(i):
            clusters[-1].append(i)
        else:
            clusters.append([i])
    return clusters


def _diff_reason(own: tuple, other: tuple, labels: Sequence[str]) -> str:
    for ov, ot, label in zip(own, other, labels):
        if ov != ot:
            return label
    return labels[-1]


def _head_to_head_aggregates(team_ids: Sequence[str], group_matches: Sequence[Match]) -> dict[str, TeamAggregate]:
    team_set = set(team_ids)
    raw = {tid: {"points": 0, "gf": 0, "ga": 0} for tid in team_ids}
    for m in group_matches:
        if m.home_team_id not in team_set or m.away_team_id not in team_set:
            continue
        h, a = raw[m.home_team_id], raw[m.away_team_id]
        h["gf"] += m.home_score
        h["ga"] += m.away_score
        a["gf"] += m.away_score
        a["ga"] += m.home_score
        if m.home_score > m.away_score:
            h["points"] += 3
        elif m.home_score < m.away_score:
            a["points"] += 3
        else:
            h["points"] += 1
            a["points"] += 1
    return {tid: TeamAggregate(tid, s["points"], s["gf"] - s["ga"], s["gf"]) for tid, s in raw.items()}


def _resolve_head_to_head(
    team_ids: Sequence[str],
    group_matches: Sequence[Match],
    aggregates: dict[str, TeamAggregate],
    conduct_scores: dict[str, int],
    fifa_ranks: dict[str, int | None],
) -> list[tuple[str, str]]:
    h2h = _head_to_head_aggregates(team_ids, group_matches)
    clusters = _cluster_by(team_ids, key_fn=lambda t: (-h2h[t].points, -h2h[t].goal_diff, -h2h[t].goals_for))

    if len(clusters) == 1:
        # Head-to-head among exactly these teams -- using only their
        # mutual matches -- produced no separation at all. Fall through to
        # overall group stats.
        return _resolve_overall_stage(team_ids, aggregates, conduct_scores, fifa_ranks, stage_index=0)

    result: list[tuple[str, str]] = []
    for i, cluster in enumerate(clusters):
        if len(cluster) == 1:
            tid = cluster[0]
            neighbor = clusters[i + 1][0] if i + 1 < len(clusters) else clusters[i - 1][0]
            reason = _diff_reason(
                (h2h[tid].points, h2h[tid].goal_diff, h2h[tid].goals_for),
                (h2h[neighbor].points, h2h[neighbor].goal_diff, h2h[neighbor].goals_for),
                (REASON_H2H_POINTS, REASON_H2H_GOAL_DIFF, REASON_H2H_GOALS_FOR),
            )
            result.append((tid, reason))
        else:
            # Still tied even on the full head-to-head triple -- re-apply
            # head-to-head recursively, scoped to just this smaller group.
            # Their matches against the now-separated teams no longer
            # dilute the comparison, so this can yield new information.
            result.extend(_resolve_head_to_head(cluster, group_matches, aggregates, conduct_scores, fifa_ranks))
    return result


_OVERALL_STAGES = [
    (lambda t, agg, cond, rank: -agg[t].goal_diff, REASON_OVERALL_GOAL_DIFF),
    (lambda t, agg, cond, rank: -agg[t].goals_for, REASON_OVERALL_GOALS_FOR),
    (lambda t, agg, cond, rank: cond.get(t, 0), REASON_CONDUCT),
    (lambda t, agg, cond, rank: (rank.get(t) is None, rank.get(t) or 0), REASON_FIFA_RANK),
]


def _resolve_overall_stage(
    ids: Sequence[str],
    aggregates: dict[str, TeamAggregate],
    conduct_scores: dict[str, int],
    fifa_ranks: dict[str, int | None],
    stage_index: int,
) -> list[tuple[str, str]]:
    if stage_index >= len(_OVERALL_STAGES):
        return [(i, REASON_UNRESOLVED) for i in ids]

    key_fn, reason = _OVERALL_STAGES[stage_index]
    clusters = _cluster_by(ids, lambda t: key_fn(t, aggregates, conduct_scores, fifa_ranks))
    if len(clusters) == 1:
        return _resolve_overall_stage(ids, aggregates, conduct_scores, fifa_ranks, stage_index + 1)

    result: list[tuple[str, str]] = []
    for cluster in clusters:
        if len(cluster) == 1:
            result.append((cluster[0], reason))
        else:
            result.extend(_resolve_overall_stage(cluster, aggregates, conduct_scores, fifa_ranks, stage_index + 1))
    return result


def break_ties(
    team_ids: Sequence[str],
    group_matches: Sequence[Match],
    aggregates: dict[str, TeamAggregate],
    conduct_scores: dict[str, int],
    fifa_ranks: dict[str, int | None],
) -> list[tuple[str, str]]:
    """Ranks `team_ids` (typically the 4 teams of a single group) from
    best to worst, applying FIFA's full 2026 group-stage tiebreak cascade.
    Returns (team_id, reason) pairs; does not mutate any input."""
    if len(team_ids) <= 1:
        return [(tid, REASON_POINTS) for tid in team_ids]

    clusters = _cluster_by(team_ids, key_fn=lambda t: -aggregates[t].points)
    if len(clusters) == 1:
        return _resolve_head_to_head(team_ids, group_matches, aggregates, conduct_scores, fifa_ranks)

    result: list[tuple[str, str]] = []
    for cluster in clusters:
        if len(cluster) == 1:
            result.append((cluster[0], REASON_POINTS))
        else:
            result.extend(_resolve_head_to_head(cluster, group_matches, aggregates, conduct_scores, fifa_ranks))
    return result


def break_third_place_ties(
    ids: Sequence[str],
    aggregates: dict[str, TeamAggregate],
    conduct_scores: dict[str, int],
    fifa_ranks: dict[str, int | None],
) -> list[tuple[str, str]]:
    """Same cascade as break_ties but skipping head-to-head: third-placed
    teams from different groups never played each other."""
    if len(ids) <= 1:
        return [(i, REASON_POINTS) for i in ids]

    clusters = _cluster_by(ids, key_fn=lambda t: -aggregates[t].points)
    if len(clusters) == 1:
        return _resolve_overall_stage(ids, aggregates, conduct_scores, fifa_ranks, stage_index=0)

    result: list[tuple[str, str]] = []
    for cluster in clusters:
        if len(cluster) == 1:
            result.append((cluster[0], REASON_POINTS))
        else:
            result.extend(_resolve_overall_stage(cluster, aggregates, conduct_scores, fifa_ranks, stage_index=0))
    return result
