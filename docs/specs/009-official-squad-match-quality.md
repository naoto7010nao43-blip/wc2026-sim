# Spec 009: Official Squad Match Quality Sprint

## Status

Ready for Claude Code implementation.

## Operating Rule

This is a long unattended sprint task. The user will not touch the computer until around noon.

Work through all phases without routine confirmation. Commit when verification passes. Do not ask the user whether to continue, whether the report looks okay, or whether to commit.

If one phase is blocked, document the blocker in `docs/codex/PROGRESS.md`, skip only that blocked phase, and continue to any later phase that is still safe.

## Product/Data Decision

Codex approves improving the official FIFA squad matching heuristic and regenerating read-only reports.

Allowed:

- improve deterministic name normalization and matching inside the official squad audit/proposal scripts
- add targeted unit tests for known missed-name patterns
- regenerate read-only official squad diff/proposal reports
- update `docs/codex/PROGRESS.md` with before/after counts and remaining risks

Not allowed:

- add unmatched official players to seed data
- delete unmatched seed players
- overwrite seed player fields
- change simulation formulas
- change player rating formulas
- change market values, career stats, or manual overrides
- perform network/source substitutions beyond the existing FIFA official PDF URL already used by the scripts
- push to remote

## Why This Matters

Spec 008 safely filled official-profile fields for 472 already-matched seed players. The largest remaining data risk is the unresolved roster drift:

- unmatched official players: 776
- unmatched seed players: 197

Some of these are genuine roster differences, but some are likely false negatives caused by name-block formatting, accents, surname-first ordering, short display names, particles, apostrophes, and pypdf extraction artifacts. We should reduce false negatives before any future import/add/remove decision.

## Files To Inspect

- `backend/scripts/audit_fifa_squad_list.py`
- `backend/scripts/build_fifa_squad_merge_proposal.py`
- `backend/tests/test_build_fifa_squad_merge_proposal.py`
- `backend/reports/fifa_squad_merge_proposal_2026-06-22.json`
- `backend/reports/fifa_squad_diff_2026-06-22.json` if present
- `backend/data/seed/players2026_official.json`
- `docs/codex/PROGRESS.md`

## Phase 1: Diagnose Current False Negatives

Create or use a temporary local analysis to identify likely missed matches from the current unmatched official/seed lists.

Prioritize deterministic signals:

- same `teamCode`
- compatible position group where possible
- high token overlap after normalization
- one side being a substring of the other after removing particles and extraction artifacts
- surname/known-name ordering differences
- apostrophe and hyphen variants
- short display-name vs full legal-name blocks

Do not commit temporary scratch files unless they are useful as tests or durable reports.

## Phase 2: Improve Matching Helpers

Improve `backend/scripts/audit_fifa_squad_list.py` without introducing fuzzy third-party dependencies.

Keep the matcher conservative. It is better to leave a true match unmatched than to merge the wrong player.

Recommended additions:

1. Expand normalization helpers to produce meaningful token sets:
   - remove diacritics
   - keep alphanumeric tokens
   - drop very common name particles when they do not help matching: `de`, `da`, `do`, `dos`, `das`, `del`, `di`, `van`, `von`, `bin`, `al`
   - normalize apostrophes/hyphens/periods
   - de-duplicate repeated tokens from FIFA name blocks
2. Add candidate-key helpers for seed and official names:
   - full compact normalized name
   - token set
   - first token + last token
   - last token + first token
   - compact versions of 2-token display names
3. Update `official_matches_seed(seed_name, official_name_block)` so it returns true only when at least one conservative condition is met:
   - existing exact compact substring condition
   - all meaningful seed tokens are present in official tokens
   - first+last or last+first compact candidate appears in official compact form
   - seed has 2+ meaningful tokens and at least 2 meaningful seed tokens appear in official tokens, including the final seed token

Avoid broad edit-distance matching unless it is tightly bounded and covered by tests.

## Phase 3: Add Tests For Missed Patterns

Add focused tests in `backend/tests/test_build_fifa_squad_merge_proposal.py` or a new audit-specific test file.

Cover at least these patterns:

- official block repeats surname/known name multiple times
- seed name uses accents removed from official or vice versa
- apostrophe/hyphen variants, e.g. `OReilly` vs `O'REILLY`
- surname-first official blocks, e.g. `MARTINEZ Lautaro ...`
- particles, e.g. names containing `de`, `da`, `dos`, `van`
- a negative case where two players share only one common surname/token and must not match

If you identify specific real false negatives from the current report, add 2-5 regression tests using those real strings.

Useful real examples found during Codex-side read-only exploration:

| teamCode | seed playerId | seed name | official name block |
| --- | --- | --- | --- |
| BRA | `BRA_EDERSON` | `Ederson Moraes` | `EDERSON Ederson SANTANA DE MORAESEDERSON` |
| ARG | `ARG_ROMERO` | `Cristian Romero` | `ROMERO CristianCristian GabrielROMEROROMERO` |
| ARG | `ARG_DEPAUL` | `Rodrigo De Paul` | `DE PAUL RodrigoRodrigo Javier DE PAUL DE PAUL` |
| FRA | `FRA_SALIBA` | `William Saliba` | `SALIBA WilliamWilliam Alain André Gabriel SALIBA SALIBA` |
| ENG | `ENG_BELLINGHAM` | `Jude Bellingham` | `BELLINGHAM JudeJude Victor William BELLINGHAM BELLINGHAM` |
| USA | `USA_PULISIC` | `Christian Pulisic` | `PULISIC ChristianChristian MatePULISIC PULISIC` |
| CAN | `CAN_DAVIES` | `Alphonso Davies` | `DAVIES AlphonsoAlphonso Boyle DAVIES DAVIES` |
| NOR | `NOR_OSTIGARD` | `Leo Skiri Ostigard` | `OSTIGARD LeoLeo Skiri ØSTIGÅRDØSTIGÅRD` |
| TUN | `TUN_BENHESSEN` | `Sabri Ben Hessen` | `BEN HESSEN SabriSabri BEN HSANBEN HESSEN` |
| HAI | `HAI_ETIENNE` | `Derrick Etienne Jr.` | `ETIENNE DerrickDerrick Burckley ETIENNE JRETIENNE JR` |

These examples are not a license for broad fuzzy matching. Use them to test deterministic candidate-key behavior only.

Negative-match risks to preserve:

- do not match on one token alone, especially `David`, `James`, `Williams`, `Silva`, `Miller`, `Cordoba`
- do not infer nickname pairs such as `Matt/Matthew`, `Tim/Timothy`, `Ollie/Oliver`, `Nico/Nicholas`, `Ko/Kou` unless the official block itself contains the seed token sequence
- do not rely on `playerId` surname text, because some IDs are stale or misleading; match using seed `name`, team, and official block

## Phase 4: Regenerate Read-Only Reports

After matcher improvements, run:

```bash
cd backend
.\venv\Scripts\python.exe scripts\audit_fifa_squad_list.py
.\venv\Scripts\python.exe scripts\build_fifa_squad_merge_proposal.py
```

Commit the regenerated report files only if the counts improve or the report timestamp/counts are needed to document the new matcher behavior.

Expected outcome:

- `matchedPlayerFieldUpdateCount` may be lower than before because Spec 008 already filled many null fields.
- `unmatchedOfficialPlayerCount` and/or `unmatchedSeedPlayerCount` should ideally decrease.
- If counts do not improve, do not force changes. Document the result in `docs/codex/PROGRESS.md` and still commit tests/refactor only if useful.

## Phase 5: Verification

Run:

```bash
cd backend
.\venv\Scripts\python.exe -m pytest
```

Frontend verification is not required unless frontend files are changed. If frontend files are changed unexpectedly, run:

```bash
cd frontend
npm run lint
npm run build
```

## Acceptance Criteria

- Matching helper is more robust but still conservative.
- Tests cover both positive and negative matching cases.
- Official squad reports are regenerated or explicitly left unchanged with a reason in `docs/codex/PROGRESS.md`.
- No seed data is modified except report files and documentation.
- Backend tests pass.
- Work is committed locally.

## Commit Policy

Commit when all required verification passes.

Suggested commit message:

```text
Improve official squad name matching
```

Do not push.

## Report Back

After committing, report:

- commit hash
- changed files
- before/after unmatched official and seed counts
- matching improvements made
- verification results
- remaining data risks
