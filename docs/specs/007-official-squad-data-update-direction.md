# Spec 007 Direction: Official Squad Data Update

## Status

Direction only. Not ready for implementation.

## Why This Matters

`backend/reports/fifa_squad_diff_2026-06-22.json` shows that the FIFA official squad list now provides 26 players for all 48 teams, while the current seed data has smaller rosters and drift for every team.

This is the highest-impact data accuracy gap currently known.

## Current Inputs

- Official source PDF:
  - `https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf`
- Read-only audit script:
  - `backend/scripts/audit_fifa_squad_list.py`
- Generated diff report:
  - `backend/reports/fifa_squad_diff_2026-06-22.json`

## Recommended Implementation Shape

Do not directly overwrite seed files in one step.

Use a three-stage import:

1. Official roster normalization
   - Convert parsed FIFA PDF data into a stable intermediate JSON file.
   - Include team code, official player line, position, DOB, club, height, caps, goals, and coach.

2. Seed merge proposal
   - Generate a proposal report that separates:
     - high-confidence matched existing players
     - unmatched official players
     - unmatched seed players
     - coach mismatches
     - fields that can be safely copied to existing players

3. Reviewed seed update
   - Apply only high-confidence field updates first:
     - `dateOfBirth`
     - `heightCm`
     - `clubName`
     - `caps`
     - `nationalTeamGoals`
     - manager name when matched
   - Do not add new players until a rating policy exists for players with missing market/stats data.

## Do Not Do Yet

- Do not add 500+ new official players with fabricated ratings.
- Do not delete seed players solely because they are absent from the first parser match.
- Do not change simulation formulas to compensate for roster drift.
- Do not treat the current parser as final until spot-checked against several teams.

## Next Ready Spec Candidate

`Spec 007A: Official Squad Merge Proposal`

Acceptance should be:

- Produce `backend/reports/fifa_squad_merge_proposal_YYYY-MM-DD.json`.
- No seed files modified.
- Report high-confidence field updates for matched players.
- Report unmatched players and coach mismatches.
- Backend tests pass.
