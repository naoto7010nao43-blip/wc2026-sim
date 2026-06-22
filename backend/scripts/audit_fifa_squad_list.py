"""Builds a read-only diff report between FIFA's official squad-list PDF
and this project's current seed data.

This script intentionally does not update seed JSON. It creates a report
under backend/reports/ so a later reviewed spec can decide what to import.

Usage:
    ./venv/Scripts/python.exe scripts/audit_fifa_squad_list.py
    ./venv/Scripts/python.exe scripts/audit_fifa_squad_list.py --input path/to/SquadLists-English.pdf
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypdf import PdfReader

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

DEFAULT_PDF_URL = "https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf"
TEAM_HEADER_RE = re.compile(r"(?:SQUAD LIST)?(?P<team>.+?)\s+\((?P<code>[A-Z]{3})\)$")
PLAYER_LINE_RE = re.compile(
    r"^(?P<position>GK|DF|MF|FW)\s+"
    r"(?P<name_block>.+?)\s+"
    r"(?P<dob>\d{2}/\d{2}/\d{4})\s+"
    r"(?P<club>.+?)\s+"
    r"(?P<height_cm>\d{2,3})\s+"
    r"(?P<caps>\d+)\s+"
    r"(?P<goals>\d+)$"
)
COACH_RE = re.compile(r"^Head coach\s+(?P<name_block>.+)\s+(?P<nationality>[A-Za-z .'-]+)$")


@dataclass(frozen=True)
class OfficialPlayer:
    position: str
    name_block: str
    dob: str
    club: str
    height_cm: int
    caps: int
    goals: int


@dataclass(frozen=True)
class OfficialTeam:
    team_name: str
    team_code: str
    players: list[OfficialPlayer]
    coach_name_block: str | None
    coach_nationality: str | None


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", asciiish.casefold())


def normalized_tokens(value: str | None) -> list[str]:
    if not value:
        return []
    decomposed = unicodedata.normalize("NFKD", value)
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return [token for token in re.split(r"[^a-z0-9]+", asciiish.casefold()) if len(token) > 1]


def load_pdf_bytes(input_arg: str) -> bytes:
    if input_arg.startswith("http://") or input_arg.startswith("https://"):
        with urllib.request.urlopen(input_arg, timeout=30) as response:
            return response.read()
    return Path(input_arg).read_bytes()


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _candidate_team_header(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("# ") or line.startswith("ROLE ") or line.startswith("DOB "):
        return None
    match = TEAM_HEADER_RE.search(line)
    if not match:
        return None
    name = match.group("team").replace("SQUAD LIST", "").strip()
    code = match.group("code")
    if not name or name.startswith("FIFA World Cup"):
        return None
    return name, code


def parse_squad_text(text: str) -> dict[str, OfficialTeam]:
    teams: dict[str, OfficialTeam] = {}
    current_code: str | None = None
    current_name: str | None = None
    current_players: list[OfficialPlayer] = []
    current_coach: tuple[str | None, str | None] = (None, None)

    def flush() -> None:
        nonlocal current_code, current_name, current_players, current_coach
        if current_code and current_name:
            teams[current_code] = OfficialTeam(
                team_name=current_name,
                team_code=current_code,
                players=list(current_players),
                coach_name_block=current_coach[0],
                coach_nationality=current_coach[1],
            )
        current_code = None
        current_name = None
        current_players = []
        current_coach = (None, None)

    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue

        header = _candidate_team_header(line)
        if header:
            flush()
            current_name, current_code = header
            continue

        if current_code is None:
            continue

        player_match = PLAYER_LINE_RE.match(line)
        if player_match:
            current_players.append(OfficialPlayer(
                position=player_match.group("position"),
                name_block=player_match.group("name_block"),
                dob=player_match.group("dob"),
                club=player_match.group("club"),
                height_cm=int(player_match.group("height_cm")),
                caps=int(player_match.group("caps")),
                goals=int(player_match.group("goals")),
            ))
            continue

        coach_match = COACH_RE.match(line)
        if coach_match:
            current_coach = (coach_match.group("name_block"), coach_match.group("nationality"))

    flush()
    return teams


def load_seed_json(name: str) -> list[dict]:
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def official_matches_seed(seed_name: str, official_name_block: str) -> bool:
    seed_norm = normalize_name(seed_name)
    official_norm = normalize_name(official_name_block)
    if not seed_norm or not official_norm:
        return False
    if seed_norm in official_norm:
        return True
    seed_tokens = normalized_tokens(seed_name)
    official_tokens = normalized_tokens(official_name_block)
    return bool(seed_tokens and all(token in official_tokens for token in seed_tokens))


def build_diff_report(official_teams: dict[str, OfficialTeam]) -> dict:
    seed_players = load_seed_json("players2026_official.json")
    seed_managers = load_seed_json("managers2026_official.json")
    seed_teams = load_seed_json("teams2026_official.json")

    seed_players_by_team: dict[str, list[dict]] = {}
    for player in seed_players:
        seed_players_by_team.setdefault(player["teamCode"], []).append(player)

    managers_by_team = {m["teamCode"]: m for m in seed_managers}
    seed_team_codes = [team["teamCode"] for team in seed_teams]

    team_reports = []
    for code in seed_team_codes:
        official = official_teams.get(code)
        seeded = seed_players_by_team.get(code, [])
        manager = managers_by_team.get(code, {})
        if official is None:
            team_reports.append({
                "teamCode": code,
                "status": "missing_in_official_pdf",
                "seedPlayerCount": len(seeded),
            })
            continue

        matched_seed_ids = set()
        unmatched_official = []
        for official_player in official.players:
            match = next(
                (p for p in seeded if p["playerId"] not in matched_seed_ids and official_matches_seed(p["name"], official_player.name_block)),
                None,
            )
            if match is None:
                unmatched_official.append(asdict(official_player))
            else:
                matched_seed_ids.add(match["playerId"])

        unmatched_seed = [
            {"playerId": p["playerId"], "name": p["name"], "primaryPosition": p["primaryPosition"]}
            for p in seeded
            if p["playerId"] not in matched_seed_ids
        ]

        seed_manager_name = manager.get("name")
        coach_match = (
            official.coach_name_block is not None
            and seed_manager_name is not None
            and official_matches_seed(seed_manager_name, official.coach_name_block)
        )

        team_reports.append({
            "teamCode": code,
            "teamName": official.team_name,
            "status": "compared",
            "officialPlayerCount": len(official.players),
            "seedPlayerCount": len(seeded),
            "matchedSeedPlayerCount": len(matched_seed_ids),
            "unmatchedOfficialPlayerCount": len(unmatched_official),
            "unmatchedSeedPlayerCount": len(unmatched_seed),
            "officialCoachNameBlock": official.coach_name_block,
            "seedManagerName": seed_manager_name,
            "coachMatches": coach_match,
            "unmatchedOfficialPlayers": unmatched_official[:12],
            "unmatchedSeedPlayers": unmatched_seed[:12],
        })

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "FIFA World Cup 2026 Squad List",
            "url": DEFAULT_PDF_URL,
        },
        "officialTeamCount": len(official_teams),
        "seedTeamCount": len(seed_team_codes),
        "teamsCompared": sum(1 for t in team_reports if t["status"] == "compared"),
        "teamsMissingInOfficialPdf": [t["teamCode"] for t in team_reports if t["status"] == "missing_in_official_pdf"],
        "teamsWithCoachMismatch": [
            t["teamCode"] for t in team_reports if t["status"] == "compared" and not t["coachMatches"]
        ],
        "teamsWithRosterDrift": [
            t["teamCode"] for t in team_reports
            if t["status"] == "compared" and (t["unmatchedOfficialPlayerCount"] > 0 or t["unmatchedSeedPlayerCount"] > 0)
        ],
        "teamReports": team_reports,
    }


def write_report(report: dict, output_path: Path | None = None) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_path = REPORTS_DIR / f"fifa_squad_diff_{stamp}.json"
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_PDF_URL, help="FIFA squad-list PDF URL or local path")
    parser.add_argument("--output", default=None, help="Optional output JSON path")
    args = parser.parse_args()

    pdf_bytes = load_pdf_bytes(args.input)
    official_teams = parse_squad_text(extract_pdf_text(pdf_bytes))
    report = build_diff_report(official_teams)
    output_path = write_report(report, Path(args.output) if args.output else None)

    print(f"Official teams parsed: {report['officialTeamCount']}")
    print(f"Teams compared: {report['teamsCompared']}")
    print(f"Teams with roster drift: {len(report['teamsWithRosterDrift'])}")
    print(f"Teams with coach mismatch: {len(report['teamsWithCoachMismatch'])}")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
