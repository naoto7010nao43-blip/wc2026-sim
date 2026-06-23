# Spec 017 - External Data Verification Expansion

Status: Ready for Claude Code

Owner split:

- Codex owns data governance, final product/data decisions, and whether any candidate becomes a future seed/rating/formula change.
- Claude Code owns read-only research collection, structuring, local consistency checks, and committing candidate reports.

## Goal

Expand the external real-world verification work beyond the first 8 priority teams so Codex has enough evidence to decide future accuracy-improvement specs with minimal user involvement.

This task is intentionally read-only. Do not change seed data, player ratings, manager/tactical values, formulas, simulation logic, or UI behavior.

## Scope

1. Research the remaining 40 teams not covered by `docs/codex/EXTERNAL_DATA_VERIFICATION_CANDIDATES_2026-06-24.md`.
2. Add a dedicated manager substitution-tendency research layer for all 48 teams where evidence is available.
3. Convert findings into structured candidate artifacts that Codex can later review.
4. Do not ask the user for routine approval. Continue in batches until the scope is complete or a hard stop condition is hit.

Already covered priority teams:

- ARG
- ESP
- ENG
- FRA
- POR
- CRO
- NED
- MEX

## Research Fields

For each team, collect evidence for:

- `manager_status`: current manager, contract/status if readily available.
- `default_formation_candidate`: likely/base formation, with alternatives when the team clearly varies.
- `tactical_profile_candidates`: qualitative evidence for possession style, pressing intensity, defensive line height, transition/directness, and defensive block.
- `key_player_status_candidates`: missing seed players, stale seed players, transfers, injuries, suspensions, likely starters, notable form changes.
- `national_team_strength_context`: national-level strength signals such as FIFA ranking movement, Elo-style strength if available, recent competitive results, qualification form, and host/confederation context.
- `substitution_tendency_candidates`: manager/team substitution behavior, including early/late substitution tendency, first-sub timing, youth/bench trust, defensive closing substitutions, like-for-like vs. tactical reshapes, and extra-time penalty/shootout preparation if evidence exists.

Important: substitution tendencies currently have no direct engine field. Still collect them as future feature candidates. Label them as `future_engine_feature_candidate`, not as current seed changes.

## Source Rules

Follow `docs/codex/DATA_GOVERNANCE_POLICY.md`.

Use source tiers:

- Tier S: FIFA or federation/tournament official sources.
- Tier A: club/federation sites, structured statistical providers, established football databases.
- Tier B: reputable news/editorial tactical reporting.
- Tier C: fan speculation or low-confidence claims. Use only as a review question, never as a proposed data value.

Every material claim must include:

- source name
- URL when available
- source tier
- observed date
- confidence: `high`, `medium`, or `low`
- whether it maps to an existing field, future field, or review-only note

## Output Files

Create or update:

- `docs/codex/EXTERNAL_DATA_VERIFICATION_REMAINING_TEAMS_2026-06-24.md`
- `docs/codex/EXTERNAL_SUBSTITUTION_TENDENCY_CANDIDATES_2026-06-24.md`
- `backend/reports/external_data_verification_candidates_2026-06-24.json`

The JSON report should be structured enough for later scripts to consume. Suggested top-level shape:

```json
{
  "generatedAt": "...",
  "scope": {
    "coveredTeams": [],
    "remainingUnresearchedTeams": [],
    "notes": []
  },
  "teams": [
    {
      "teamId": "BRA",
      "teamName": "Brazil",
      "managerStatus": [],
      "formationCandidates": [],
      "tacticalProfileCandidates": [],
      "keyPlayerStatusCandidates": [],
      "nationalStrengthContext": [],
      "substitutionTendencyCandidates": [],
      "recommendedCodexNextActions": []
    }
  ],
  "crossTeamPatterns": [],
  "futureEngineFeatureCandidates": []
}
```

Use exact repo team IDs from `backend/data/seed/teams.json`.

## Analysis Requirements

Do not only paste source facts. Add Claude's own careful synthesis:

- Which findings are high-impact for simulation accuracy?
- Which findings map to existing fields now?
- Which findings require a future engine field?
- Which findings are too weak or stale to use?
- Which teams should Codex prioritize for a future data-changing spec?

Separate these categories clearly:

- safe factual candidate
- ambiguous candidate
- rating-review candidate
- tactical-profile candidate
- roster/availability candidate
- future-engine candidate

Do not over-filter sparse teams. If evidence is weak but potentially useful,
keep it as a low-confidence review question rather than deleting it. Codex will
later decide whether it can be used as:

- a direct data-change candidate,
- provisional context for simulation tuning,
- a UI uncertainty note,
- a future-engine feature candidate,
- or a discarded claim.

The goal is not to maximize automatic acceptance. The goal is to preserve useful
signal while making uncertainty explicit enough that the simulator does not gain
false confidence.

The validation output now includes `teamSignalProfiles`, `teamSignalBandCounts`,
and `sparseTeamIds`. Treat `sparse` as a routing signal, not a failure. A sparse
team should keep low-confidence review questions when they are the best available
evidence, because Codex may later use them as provisional context, UI uncertainty
notes, or future research leads.

## Stop Conditions

Stop and report only if:

- network/search access is unavailable for the whole task,
- source reliability is too poor to produce useful candidate reports,
- repo files needed for team IDs or governance cannot be read,
- another agent has already completed the same files and there is a real conflict.

Do not stop merely because some teams have sparse information. Mark those teams as low-confidence and continue.

## Verification

Required before commit:

- `cd backend && .\venv\Scripts\python.exe scripts\audit_text_encoding.py`
- Validate the JSON report can be parsed:
  - `cd backend && .\venv\Scripts\python.exe -c "import json, pathlib; json.loads(pathlib.Path('reports/external_data_verification_candidates_2026-06-24.json').read_text(encoding='utf-8')); print('json ok')"`
- Run the Codex acceptance gate for research quality and simulator relevance:
  - `cd backend && .\venv\Scripts\python.exe scripts\validate_external_data_verification_report.py reports\external_data_verification_candidates_2026-06-24.json --out reports\external_data_verification_validation_2026-06-24.json`
- `git diff --check`

No backend pytest or frontend build is required unless code is changed. Code should not be changed in this spec.

## Commit

Commit the completed read-only reports with a concise message such as:

`Expand external data verification candidates`

Do not push.
