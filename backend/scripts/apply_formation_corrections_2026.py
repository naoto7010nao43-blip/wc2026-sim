"""One-off: correct team defaultFormation values to the shapes actually used
at the 2026 World Cup group stage.

Source: mylineups.app/world-cup-2026/teams/<slug> (per-team starting XI +
formation, reflecting the played group stage). This is an external citable
reference, not an official FIFA publication, so each corrected team is tagged
with `defaultFormationSource` and the formation is mapped onto the six shapes
the engine supports (app.engine.formations.FORMATIONS):

    4-1-2-3, 4-1-4-1 -> 4-3-3
    4-4-1-1, 4-3-1-2 -> 4-4-2
    5-4-1            -> 3-4-2-1   (wing-back back-3, lone striker)
    5-3-2, 3-1-4-2   -> 3-5-2

Real (already-supported) notations pass through unchanged. Idempotent: only
teams whose stored formation differs from the target are rewritten.

Usage:
  PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe scripts/apply_formation_corrections_2026.py
Then regenerate the legacy mirror:
  PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe scripts/apply_external_factual_updates.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.formations import FORMATIONS

TEAMS_V2 = Path(__file__).resolve().parent.parent / "data" / "seed" / "teams2026_official.json"
SOURCE = "mylineups.app/world-cup-2026 (2026 group stage)"

# Target engine-shape per team, derived from the real 2026 WC formation
# (real notation in the trailing comment where it was mapped).
TARGET = {
    "JPN": "3-4-2-1",
    "ARG": "4-4-2",
    "BRA": "4-3-3",      # 4-1-2-3
    "ENG": "4-2-3-1",
    "POR": "4-2-3-1",
    "CRO": "3-4-2-1",
    "URU": "4-2-3-1",
    "COL": "4-3-3",
    "USA": "3-5-2",
    "MAR": "4-2-3-1",
    "SUI": "4-4-2",      # 4-3-1-2
    "SCO": "4-3-3",      # 4-1-4-1
    "SEN": "4-2-3-1",
    "GHA": "4-4-2",      # 4-4-1-1
    "KOR": "3-4-2-1",
    "IRN": "3-4-2-1",    # 5-4-1
    "KSA": "3-4-2-1",    # 5-4-1
    "QAT": "4-3-3",
    "SWE": "3-5-2",
    "TUN": "3-4-2-1",
    "ECU": "3-5-2",      # 3-1-4-2
    "PAN": "3-4-3",
    "NZL": "4-2-3-1",
    "RSA": "4-3-3",
    "IRQ": "4-3-3",
    "JOR": "3-4-2-1",
    "CPV": "4-3-3",      # 4-1-4-1
    "CUW": "3-4-2-1",    # 5-4-1
    "CZE": "3-5-2",
    "HAI": "3-4-2-1",    # 5-4-1
    "UZB": "3-4-2-1",
    # Already correct (kept for an explicit, auditable full-squad record):
    "ALG": "4-2-3-1", "AUS": "3-4-2-1", "AUT": "4-2-3-1", "BEL": "4-2-3-1",
    "BIH": "4-4-2", "CAN": "4-4-2", "CIV": "4-3-3", "COD": "3-5-2",
    "EGY": "4-2-3-1", "ESP": "4-3-3", "FRA": "4-2-3-1", "GER": "4-2-3-1",
    "MEX": "4-3-3", "NED": "4-3-3", "NOR": "4-3-3", "PAR": "4-4-2",
    "TUR": "4-2-3-1",
}


def main() -> None:
    bad = [f for f in set(TARGET.values()) if f not in FORMATIONS]
    if bad:
        raise SystemExit(f"target formation(s) not supported by engine: {bad}")

    teams = json.loads(TEAMS_V2.read_text(encoding="utf-8"))
    missing = sorted(set(TARGET) - {t["teamId"] for t in teams})
    extra = sorted({t["teamId"] for t in teams} - set(TARGET))
    if missing or extra:
        raise SystemExit(f"team-id mismatch missing={missing} extra={extra}")

    changes = []
    for t in teams:
        target = TARGET[t["teamId"]]
        if t.get("defaultFormation") != target:
            changes.append((t["teamId"], t.get("defaultFormation"), target))
            t["defaultFormation"] = target
            t["defaultFormationSource"] = SOURCE

    TEAMS_V2.write_text(
        json.dumps(teams, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"updated {len(changes)}/{len(teams)} teams")
    for code, old, new in sorted(changes):
        print(f"  {code}: {old} -> {new}")


if __name__ == "__main__":
    main()
