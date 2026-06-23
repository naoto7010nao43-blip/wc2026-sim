"""Read-only roster reconciliation candidate report -- proposes which
remaining unmatched official/seed players (from the latest
fifa_squad_merge_proposal report) are worth a human (Codex) look, without
adding, removing, or modifying any seed player.

Reuses the same conservative name-token normalization as
audit_fifa_squad_list.py, just at a looser bar (any shared meaningful
token) than that script's strict matcher -- this report's job is to
surface review *candidates*, not to auto-match.

Usage: ./venv/Scripts/python.exe scripts/build_roster_reconciliation_candidates.py
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_fifa_squad_list import meaningful_name_tokens

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

OFFICIAL_POSITION_TO_GROUP = {"GK": "GK", "DF": "DEF", "MF": "MID", "FW": "FWD"}
SEED_POSITION_TO_GROUP = {
    "GK": "GK",
    "CB": "DEF", "LB": "DEF", "RB": "DEF",
    "CDM": "MID", "CM": "MID", "CAM": "MID", "LM": "MID", "RM": "MID",
    "LW": "FWD", "RW": "FWD", "ST": "FWD",
}
# This seed dataset only carries 12-19 players/team (not a real 26-man
# squad), so "below 26" from the spec's suggested signal would flag every
# team. Use the dataset's own shallower half instead.
LOW_ROSTER_THRESHOLD = 15


def latest_report(pattern: str) -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(pattern))
    if not matches:
        return None
    return json.loads(matches[-1].read_text(encoding="utf-8"))


def seed_roster_sizes(players: list[dict]) -> dict:
    sizes: dict = defaultdict(int)
    for p in players:
        sizes[p["team_id"]] += 1
    return dict(sizes)


def fuzzy_overlap_score(seed_name: str, official_name_block: str) -> int:
    """Count of shared meaningful name tokens -- intentionally looser than
    official_matches_seed()'s strict bar, since this is a review candidate,
    not an auto-match."""
    seed_tokens = set(meaningful_name_tokens(seed_name))
    official_tokens = set(meaningful_name_tokens(official_name_block))
    return len(seed_tokens & official_tokens)


def best_fuzzy_match(seed_player: dict, official_candidates: list[tuple]) -> tuple:
    """official_candidates is a list of (index, official_dict) pairs so the
    caller can mark the winning index as claimed without relying on dict
    equality. Returns (index, official_dict, score) or (None, None, 0)."""
    best_idx, best_official, best_score = None, None, 0
    for idx, official in official_candidates:
        score = fuzzy_overlap_score(seed_player["name"], official["name_block"])
        if score > best_score:
            best_idx, best_official, best_score = idx, official, score
    return best_idx, best_official, best_score


def classify_add_candidate(seed_roster_size: int) -> tuple:
    if seed_roster_size < LOW_ROSTER_THRESHOLD:
        return "low", (
            f"Team's seed roster ({seed_roster_size} players) is below this dataset's typical size "
            f"({LOW_ROSTER_THRESHOLD}); likely a genuine gap."
        )
    return "medium", (
        f"Team's seed roster ({seed_roster_size} players) is already at/above this dataset's typical size; "
        "less urgent."
    )


def classify_seed_player(fuzzy_score: int) -> tuple:
    if fuzzy_score >= 2:
        return "medium", (
            f"Shares {fuzzy_score} name tokens with an unmatched official player in the same position group; "
            "may be the same person under a different name form."
        )
    if fuzzy_score == 1:
        return "medium", "Shares exactly one name token with an unmatched official player; weak signal, needs a human look."
    return "medium", "No name-token overlap with any unmatched official player on this team; may not be in the released 2026 squad."


def build_team_candidates(team_code: str, seed_unmatched: list, official_unmatched: list, roster_size: int) -> dict:
    ambiguous_pairs = []
    likely_stale = []
    claimed_official_indices: set = set()

    for seed_player in seed_unmatched:
        seed_group = SEED_POSITION_TO_GROUP.get(seed_player["primaryPosition"], "MID")
        same_group_official = [
            (i, o) for i, o in enumerate(official_unmatched)
            if i not in claimed_official_indices and OFFICIAL_POSITION_TO_GROUP.get(o["position"]) == seed_group
        ]
        idx, best, score = best_fuzzy_match(seed_player, same_group_official)
        if best is not None and score >= 1:
            claimed_official_indices.add(idx)
            risk, reason = classify_seed_player(score)
            ambiguous_pairs.append({
                "seed_player_id": seed_player["playerId"],
                "seed_player_name": seed_player["name"],
                "official_candidate_name_block": best["name_block"],
                "official_candidate_position": best["position"],
                "shared_token_count": score,
                "risk_level": risk,
                "reason": reason,
            })
        else:
            risk, reason = classify_seed_player(0)
            likely_stale.append({
                "seed_player_id": seed_player["playerId"],
                "seed_player_name": seed_player["name"],
                "seed_position": seed_player["primaryPosition"],
                "risk_level": risk,
                "reason": reason,
            })

    add_candidates = []
    for i, official in enumerate(official_unmatched):
        if i in claimed_official_indices:
            continue
        risk, reason = classify_add_candidate(roster_size)
        add_candidates.append({
            "official_name_block": official["name_block"],
            "official_position": official["position"],
            "official_club": official.get("club"),
            "official_caps": official.get("caps"),
            "risk_level": risk,
            "reason": reason,
        })

    return {
        "team_code": team_code,
        "seed_roster_size": roster_size,
        "high_confidence_add_candidates": [c for c in add_candidates if c["risk_level"] == "low"],
        "other_add_candidates": [c for c in add_candidates if c["risk_level"] != "low"],
        "likely_stale_seed_players": likely_stale,
        "ambiguous_pairs": ambiguous_pairs,
    }


def build_report(merge_proposal: dict, roster_sizes: dict) -> dict:
    by_team_official: dict = defaultdict(list)
    for o in merge_proposal["unmatchedOfficialPlayers"]:
        by_team_official[o["teamCode"]].append(o)
    by_team_seed: dict = defaultdict(list)
    for s in merge_proposal["unmatchedSeedPlayers"]:
        by_team_seed[s["teamCode"]].append(s)

    team_codes = sorted(set(by_team_official) | set(by_team_seed))
    team_reports = [
        build_team_candidates(tc, by_team_seed.get(tc, []), by_team_official.get(tc, []), roster_sizes.get(tc, 0))
        for tc in team_codes
    ]

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "Roster Reconciliation Candidate Report",
            "basedOnReportGeneratedAt": merge_proposal.get("generatedAt"),
        },
        "note": (
            "Read-only candidate report for Codex review. Does not add, remove, or modify any seed player. "
            "Uses a looser name-token bar than the strict official squad matcher specifically to surface "
            "human-review candidates."
        ),
        "lowRosterThreshold": LOW_ROSTER_THRESHOLD,
        "teamCount": len(team_reports),
        "teamReports": team_reports,
    }


def main() -> int:
    merge_proposal = latest_report("fifa_squad_merge_proposal_*.json")
    if merge_proposal is None:
        print("No merge proposal report found -- run build_fifa_squad_merge_proposal.py first.")
        return 1

    players = json.loads((SEED_DIR / "players.json").read_text(encoding="utf-8"))
    roster_sizes = seed_roster_sizes(players)
    report = build_report(merge_proposal, roster_sizes)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"roster_reconciliation_candidates_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    total_high = sum(len(t["high_confidence_add_candidates"]) for t in report["teamReports"])
    total_ambiguous = sum(len(t["ambiguous_pairs"]) for t in report["teamReports"])
    total_stale = sum(len(t["likely_stale_seed_players"]) for t in report["teamReports"])
    print(f"Wrote {out_path}")
    print(f"Teams: {report['teamCount']}")
    print(f"High-confidence add candidates: {total_high}")
    print(f"Ambiguous pairs: {total_ambiguous}")
    print(f"Likely-stale seed players: {total_stale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
