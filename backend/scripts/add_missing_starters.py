"""Idempotent adder for real 2026 WC starters that were entirely MISSING from
the roster (like Keito Nakamura in Phase 2b). Each entry carries citable EA
SPORTS FC 26 values (dataConfidence="external", never "official") plus a
confirmed-starter startingProbability override sourced from an actual played
2026 World Cup match lineup.

Usage:  ./venv/Scripts/python.exe scripts/add_missing_starters.py
Then rerun scripts/rebuild_player_ratings_v2.py to regenerate estimated ratings,
and scripts/apply_external_factual_updates.py (or its regenerate fns) to mirror
players.json. This script only touches the source-of-truth v2 seed files.

Add new players to NEW_STARTERS below and rerun; existing playerIds are skipped.
"""

import json
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"
OFF = SEED / "players2026_official.json"
EXT = SEED / "externalPlayerRatings2026.json"
OVR = SEED / "manualPlayerOverrides2026.json"

# Each dict is fully sourced. `ea` holds the six EA FC 26 face stats + meta.
# `startProb`/`starterSource`/`starterUrl` come from a confirmed played-match XI.
NEW_STARTERS = [
    {
        "playerId": "NOR_NUSA", "teamId": "NOR", "name": "Antonio Nusa", "nameJa": "アントニオ・ヌサ",
        "age": 21, "dateOfBirth": None, "primaryPosition": "LM", "secondaryPositions": ["LW", "CAM"],
        "heightCm": 183, "clubName": "RB Leipzig (GER)", "staminaMax": 88,
        "ea": {"eaPlayerId": "262863", "position": "LM", "overall": 76,
               "pace": 89, "shooting": 72, "passing": 68, "dribbling": 81, "defending": 41, "physical": 63,
               "url": "https://www.ea.com/en/games/ea-sports-fc/ratings/player-ratings/antonio-nusa/262863"},
        "startProb": 78,
        "starterReason": "Confirmed Norway starter at the 2026 WC: started the R32 win vs Ivory Coast on the left wing. The roster lacked a natural left winger, so the slot was wrongly auto-filled by a striker (Sorloth).",
        "starterSource": "World Soccer Talk — Ivory Coast vs Norway confirmed lineups (2026 WC R32)",
        "starterUrl": "https://worldsoccertalk.com/world-cup/is-erling-haaland-playing-ivory-coast-vs-norway-confirmed-lineups-for-the-2026-world-cup-match/",
    },
    {
        "playerId": "ECU_ORDONEZ", "teamId": "ECU", "name": "Joel Ordonez", "nameJa": "ジョエル・オルドニェス",
        "age": 22, "dateOfBirth": None, "primaryPosition": "CB", "secondaryPositions": [],
        "heightCm": 188, "clubName": "Club Brugge (BEL)", "staminaMax": 82,
        "ea": {"eaPlayerId": "268611", "position": "CB", "overall": 75,
               "pace": 74, "shooting": 26, "passing": 54, "dribbling": 56, "defending": 74, "physical": 79,
               "url": "https://www.ea.com/en/games/ea-sports-fc/ratings/player-ratings/joel-ordonez/268611"},
        "startProb": 80,
        "starterReason": "Confirmed Ecuador starter at the 2026 WC: started the R32 vs Mexico in the back three (Ordonez-Pacho-Hincapie). Felix Torres, previously assumed, was a substitute. The roster's 3rd centre-back was missing so the slot was auto-filled out of position.",
        "starterSource": "khelnow / FanDuel Research — Mexico vs Ecuador confirmed lineups (2026 WC R32)",
        "starterUrl": "https://khelnow.com/football/ecuador-starting-lineup-vs-mexico-fifa-world-cup-2026",
    },
    {
        "playerId": "URU_M_ARAUJO", "teamId": "URU", "name": "Maximiliano Araujo", "nameJa": "マキシミリアーノ・アラウホ",
        "age": 26, "dateOfBirth": None, "primaryPosition": "LM", "secondaryPositions": ["LW", "LB"],
        "heightCm": 177, "clubName": "Sporting CP (POR)", "staminaMax": 86,
        "ea": {"eaPlayerId": "254817", "position": "LM", "overall": 77,
               "pace": 85, "shooting": 63, "passing": 70, "dribbling": 79, "defending": 68, "physical": 68,
               "url": "https://www.ea.com/en/games/ea-sports-fc/ratings/player-ratings/maximiliano-araujo/254817"},
        "startProb": 72,
        "starterReason": "Uruguay's left-sided attacker in Bielsa's front three (Canobbio-Nunez-Araujo) at the 2026 WC. The roster had no natural left winger so the slot was auto-filled by a central midfielder (Bentancur).",
        "starterSource": "FourFourTwo / SI / Al Jazeera — Uruguay confirmed & predicted 2026 WC lineups",
        "starterUrl": "https://www.fourfourtwo.com/team/uruguay-world-cup-2026-squad",
    },
    {
        "playerId": "SCO_DOAK", "teamId": "SCO", "name": "Ben Doak", "nameJa": "ベン・ドーク",
        "age": 20, "dateOfBirth": None, "primaryPosition": "RM", "secondaryPositions": ["RW", "LW"],
        "heightCm": 176, "clubName": "AFC Bournemouth (ENG)", "staminaMax": 88,
        "ea": {"eaPlayerId": "266815", "position": "RM", "overall": 71,
               "pace": 89, "shooting": 61, "passing": 63, "dribbling": 75, "defending": 28, "physical": 60,
               "url": "https://www.ea.com/games/ea-sports-fc/ratings/player-ratings/ben-doak/266815"},
        "startProb": 78,
        "starterReason": "Confirmed Scotland starter at the 2026 WC: started on the right wing vs Brazil (Group C) and created several chances vs Haiti. The roster lacked a natural right winger, so the slot was wrongly auto-filled by a left-back (Kieran Tierney).",
        "starterSource": "ESPN — Scotland vs Brazil confirmed line-ups (2026 WC Group C)",
        "starterUrl": "https://www.espn.com/soccer/story/_/id/49152740/scotland-brazil-line-ups-world-cup-predicted-xis",
    },
]

OBSERVED = "2026-07-01"


def add_all():
    off = json.loads(OFF.read_text(encoding="utf-8"))
    ext = json.loads(EXT.read_text(encoding="utf-8"))
    ov = json.loads(OVR.read_text(encoding="utf-8"))
    off_ids = {p.get("playerId") for p in off}
    ext_ids = {p.get("playerId") for p in ext}
    ov_ids = {p.get("playerId") for p in ov}

    added = []
    for s in NEW_STARTERS:
        pid = s["playerId"]
        ea = s["ea"]
        if pid not in off_ids:
            off.append({
                "playerId": pid, "teamId": s["teamId"], "teamCode": s["teamId"],
                "name": s["name"], "nameJa": s.get("nameJa"),
                "age": s["age"], "dateOfBirth": s.get("dateOfBirth"), "shirtNumber": None,
                "primaryPosition": s["primaryPosition"], "secondaryPositions": s["secondaryPositions"],
                "preferredFoot": "unknown", "heightCm": s.get("heightCm"), "weightKg": None,
                "clubName": s["clubName"], "clubCountry": None, "leagueName": None,
                "caps": None, "nationalTeamGoals": None, "marketValueEur": None,
                "careerStats": {}, "qualitativeAdjustments": {},
                "sourceCitations": [
                    f"EA SPORTS FC 26 official player ratings (player {ea['eaPlayerId']}): "
                    f"overall {ea['overall']}, {ea['position']}, {s['clubName']} — {ea['url']}",
                    f"Confirmed 2026 World Cup starter — {s['starterSource']}: {s['starterUrl']}",
                ],
                "staminaMax": s.get("staminaMax", 85), "dataConfidence": "external",
                "lastUpdated": f"{OBSERVED}T00:00:00+00:00",
            })
            added.append(pid + " (official)")
        if pid not in ext_ids:
            ext.append({
                "playerId": pid, "name": s["name"], "source": "EA SPORTS FC 26", "sourceUrl": ea["url"],
                "sourceDataset": f"EA SPORTS FC 26 official player ratings page (fetched {OBSERVED})",
                "eaPlayerId": ea["eaPlayerId"], "position": ea["position"], "observedDate": OBSERVED,
                "overall": ea["overall"], "pace": ea["pace"], "shooting": ea["shooting"],
                "passing": ea["passing"], "dribbling": ea["dribbling"], "defending": ea["defending"],
                "physical": ea["physical"],
            })
            added.append(pid + " (external)")
        if pid not in ov_ids:
            ov.append({
                "playerId": pid, "name": s["name"], "reason": s["starterReason"],
                "source": s["starterSource"], "sourceUrl": s["starterUrl"], "observedDate": OBSERVED,
                "overrides": {"startingProbability": s["startProb"]},
            })
            added.append(pid + " (override)")

    OFF.write_text(json.dumps(off, ensure_ascii=False, indent=2), encoding="utf-8")
    EXT.write_text(json.dumps(ext, ensure_ascii=False, indent=2), encoding="utf-8")
    OVR.write_text(json.dumps(ov, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"official={len(off)} external={len(ext)} overrides={len(ov)}")
    print("added:", added or "nothing new")


if __name__ == "__main__":
    add_all()
