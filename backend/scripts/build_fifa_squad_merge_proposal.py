"""Spec 007A: Official Squad Merge Proposal.

Read-only: produces backend/reports/fifa_squad_merge_proposal_<date>.json
and does NOT modify any seed file. Reuses audit_fifa_squad_list.py's PDF
parsing/name-matching logic rather than re-implementing it, so this
report and the existing diff report always agree on who matched whom.

This is a proposal for human/Codex review, not an applied update -- see
docs/specs/007-official-squad-data-update-direction.md. The name-matching
heuristic is known to be imperfect (e.g. it can miss a real match when
the official PDF's name block and the seed's display name diverge more
than the token-overlap check tolerates); unmatched players are NOT
necessarily new/unknown to the roster, just unmatched by this heuristic.

Usage:
    ./venv/Scripts/python.exe scripts/build_fifa_squad_merge_proposal.py
    ./venv/Scripts/python.exe scripts/build_fifa_squad_merge_proposal.py --input path/to/SquadLists-English.pdf
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_fifa_squad_list as audit  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

# Fields spec 007 lists as safe to propose copying onto an existing,
# already-matched player -- never used to fabricate a new player.
PROPOSABLE_FIELDS = ("dateOfBirth", "heightCm", "clubName", "caps", "nationalTeamGoals")


def _proposed_updates(seed_player: dict, official_player: "audit.OfficialPlayer") -> dict:
    official_values = {
        "dateOfBirth": official_player.dob,
        "heightCm": official_player.height_cm,
        "clubName": official_player.club,
        "caps": official_player.caps,
        "nationalTeamGoals": official_player.goals,
    }
    return {field: official_values[field] for field in PROPOSABLE_FIELDS if seed_player.get(field) is None}


def build_merge_proposal(official_teams: dict[str, "audit.OfficialTeam"]) -> dict:
    seed_players = audit.load_seed_json("players2026_official.json")
    seed_managers = audit.load_seed_json("managers2026_official.json")
    seed_teams = audit.load_seed_json("teams2026_official.json")

    seed_players_by_team: dict[str, list[dict]] = {}
    for player in seed_players:
        seed_players_by_team.setdefault(player["teamCode"], []).append(player)
    managers_by_team = {m["teamCode"]: m for m in seed_managers}
    seed_team_codes = [t["teamCode"] for t in seed_teams]

    matched_player_field_updates = []
    unmatched_official_players = []
    unmatched_seed_players = []
    coach_mismatches = []
    teams_missing_in_official_pdf = []

    for code in seed_team_codes:
        official = official_teams.get(code)
        seeded = seed_players_by_team.get(code, [])
        manager = managers_by_team.get(code, {})

        if official is None:
            teams_missing_in_official_pdf.append(code)
            continue

        matched_seed_ids: set[str] = set()
        for official_player in official.players:
            match = next(
                (p for p in seeded if p["playerId"] not in matched_seed_ids
                 and audit.official_matches_seed(p["name"], official_player.name_block)),
                None,
            )
            if match is None:
                unmatched_official_players.append({"teamCode": code, **dataclasses.asdict(official_player)})
                continue
            matched_seed_ids.add(match["playerId"])

            proposed = _proposed_updates(match, official_player)
            if proposed:
                matched_player_field_updates.append({
                    "teamCode": code,
                    "playerId": match["playerId"],
                    "seedName": match["name"],
                    "officialNameBlock": official_player.name_block,
                    "proposedUpdates": proposed,
                })

        for p in seeded:
            if p["playerId"] not in matched_seed_ids:
                unmatched_seed_players.append({
                    "teamCode": code, "playerId": p["playerId"], "name": p["name"],
                    "primaryPosition": p["primaryPosition"],
                })

        seed_manager_name = manager.get("name")
        coach_matches = (
            official.coach_name_block is not None
            and seed_manager_name is not None
            and audit.official_matches_seed(seed_manager_name, official.coach_name_block)
        )
        if not coach_matches:
            coach_mismatches.append({
                "teamCode": code,
                "seedManagerName": seed_manager_name,
                "officialCoachNameBlock": official.coach_name_block,
                "officialCoachNationality": official.coach_nationality,
            })

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "FIFA World Cup 2026 Squad List",
            "url": audit.DEFAULT_PDF_URL,
        },
        "note": (
            "Read-only proposal (spec 007A). No seed files were modified by generating "
            "this report. Do not apply matchedPlayerFieldUpdates without a separate "
            "reviewed spec -- see docs/specs/007-official-squad-data-update-direction.md."
        ),
        "teamsMissingInOfficialPdf": teams_missing_in_official_pdf,
        "matchedPlayerFieldUpdateCount": len(matched_player_field_updates),
        "unmatchedOfficialPlayerCount": len(unmatched_official_players),
        "unmatchedSeedPlayerCount": len(unmatched_seed_players),
        "coachMismatchCount": len(coach_mismatches),
        "matchedPlayerFieldUpdates": matched_player_field_updates,
        "unmatchedOfficialPlayers": unmatched_official_players,
        "unmatchedSeedPlayers": unmatched_seed_players,
        "coachMismatches": coach_mismatches,
    }


def write_report(report: dict, output_path: Path | None = None) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_path = REPORTS_DIR / f"fifa_squad_merge_proposal_{stamp}.json"
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=audit.DEFAULT_PDF_URL, help="FIFA squad-list PDF URL or local path")
    parser.add_argument("--output", default=None, help="Optional output JSON path")
    args = parser.parse_args()

    pdf_bytes = audit.load_pdf_bytes(args.input)
    official_teams = audit.parse_squad_text(audit.extract_pdf_text(pdf_bytes))
    report = build_merge_proposal(official_teams)
    output_path = write_report(report, Path(args.output) if args.output else None)

    print(f"Matched player field updates proposed: {report['matchedPlayerFieldUpdateCount']}")
    print(f"Unmatched official players: {report['unmatchedOfficialPlayerCount']}")
    print(f"Unmatched seed players: {report['unmatchedSeedPlayerCount']}")
    print(f"Coach mismatches: {report['coachMismatchCount']}")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
