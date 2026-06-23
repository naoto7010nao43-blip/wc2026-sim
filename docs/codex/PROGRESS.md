# Progress

## Current Operating Model

- Codex owns product direction, data policy, simulation-quality review, and implementation specs.
- Claude Code owns implementation and test execution.
- The user should not be asked for routine implementation approvals.
- Claude Code should commit Ready-task work after passing verification, then report.
- For longer implementation runs, Claude Code should follow `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`.

## Current Priority

Spec 011 is active: turn Spec 010's simulation-audit and roster-reconciliation findings into a read-only team data review diagnostic layer. The goal is to prioritize squad/rating data review without mutating seed players, ratings, formulas, or simulation behavior.

Completed:

- `docs/specs/001-lint-fix.md`
- `docs/specs/003-match-detail-trust-states.md`
- `docs/specs/004-simulator-prediction-panel.md`
- `docs/specs/005-tournament-odds-panel.md`
- `docs/specs/006-overnight-data-trust-sprint.md`
- Spec 007A official squad merge proposal, commit `ebe4064`
- `docs/specs/008-official-squad-safe-field-apply.md`
- `docs/specs/009-official-squad-match-quality.md`
- Spec 009 follow-up: applied official-profile fields for newly matched players and cleaned PDF ligature artifacts.
- Product polish: verified and cleaned Japanese copy across home, tournament, simulator, bracket, match cards, and match detail; expanded prediction API mojibake regression checks.
- Tournament odds transparency: Monte Carlo API now exposes data confidence and method explanation; frontend displays it and remains compatible with older local API responses.
- Spec 010 Phase 1 base work: added deterministic text encoding audit script and tests.
- Codex parallel UI sprint: added team-level manager/tactical model visibility and simulator matchup comparison without touching Claude's Spec 010 data-quality API work.
- Codex parallel UI sprint follow-up: added TeamPage squad depth, age-band, profile-coverage, and key-player summary panels derived from existing team player data.
- Codex parallel tournament UX sprint: added TournamentPage highlights and group-card summary cues derived from existing tournament results.
- Codex parallel navigation sprint: added a searchable Teams index page and top-nav entry so users can reach every team profile directly.
- Codex parallel standings UX sprint: added direct-qualification and third-place-candidate labels to group standings tables.
- Codex parallel navigation polish: added a 404 fallback page with direct recovery links to tournament, simulator, and teams.
- Spec 010 Phase 1: confirmed `audit_text_encoding.py` scan scope/markers already match the spec; no changes needed.
- Spec 010 Phase 2: added read-only `GET /api/data-quality/summary` (`app/services/data_quality.py`, `app/schemas/data_quality.py`, `app/api/data_quality.py`), wired into `app/main.py`. Computes seed/official-profile counts and reads the latest `fifa_squad_merge_proposal_*.json` report; never mutates seed/report files. 4 new tests (`tests/test_data_quality.py`) cover the live report numbers and a missing-report fallback.
- Spec 010 Phase 3: added a compact `DataQualityPanel` to the home page (`frontend/src/components/DataQualityPanel.tsx`), consuming the new API with a calm fallback message on fetch failure or while loading. Notes returned by the API are Japanese to match the rest of the UI.
- Spec 010 Phase 4: reviewed match detail trust states against the spec's acceptance criteria -- Spec 003 already implemented distinct real/detailed-simulation/score-prediction labels, a compact description line near the score, calm empty states per match kind, a conditional ratings panel, and a responsive grid layout. No further changes were required.
- Spec 010 Phase 5: ran Playwright smoke checks (desktop 1280px and mobile 390px) across `/`, `/simulate`, `/tournament`, `/teams/BRA`, and a freshly simulated match detail page -- 10/10 checks passed with zero mojibake/replacement-character findings, zero horizontal overflow, and zero console errors.
- Spec 010 Phase 10 (autonomous loop, 1 cycle run): re-ran the encoding audit, full backend test suite, and frontend lint/build (all clean) per the loop's steps 1-3, then reviewed `docs/codex/PROGRESS.md` Open Risks for the highest-impact safe fix. Found that `audit_text_encoding.py` (Phase 1's guardrail) only scanned source code, never `backend/data/seed/**` or `backend/reports/**` -- the actual JSON files where this project's Japanese name/copy data (and its real past mojibake bugs) live. Extended `DEFAULT_ROOTS`/`TEXT_SUFFIXES` to cover those, verified zero false positives against the real repo (passes clean, 0.4s), and added 2 regression tests. Stopping the loop here rather than continuing further rounds, since the next remaining items (roster import, coach-name correction) need a Codex-reviewed import spec or unverifiable external data, both explicit stop conditions.
- Spec 010 Phase 9: added `app/services/match_analysis.py` (pure, read-only helpers) plus a `MatchAnalysis` field on the match API response and a new `MatchAnalysisPanel.tsx` on the match detail page. Derives a turning-point goal (last lead-change, not just the final goal), 15-minute momentum segments from existing shot/goal events, top-3 key players from the already-computed player ratings, and a templated tactical note from formations/manager/tactical-profile fields -- nothing fabricated, no xG-style shot-quality claim since that data doesn't exist yet. Only populated for detailed-simulation matches (`not is_real and events`); real and score-only-Poisson matches get the existing calm "分析は利用できません" fallback. 10 new backend tests; frontend `tsc`/`lint`/`build` all clean; Playwright smoke checks (desktop+mobile, all 5 pages) still 10/10 clean after the change; visually confirmed the panel renders correctly on a fresh simulated match (turning point, momentum bars, key players, tactical note).
- Spec 010 Phase 8: added `backend/scripts/build_roster_reconciliation_candidates.py` and `backend/reports/roster_reconciliation_candidates_2026-06-23.json` (read-only; no seed player added/removed/modified). For all 48 teams, classifies the 652 unmatched official players and 73 unmatched seed players into: 474 high-confidence add candidates (team's seed roster below this dataset's own 15-player shallow-half threshold -- note this dataset only carries 12-19 players/team, not a real 26-man squad, so the spec's literal "below 26" signal would have flagged every team and was replaced with a dataset-relative one), 162 lower-priority add candidates, 16 ambiguous seed/official pairs found via a looser name-token overlap than the strict matcher, and 57 likely-stale seed players with no token overlap at all. Counts reconcile exactly against the source report (636+16=652 official, 16+57=73 seed). Spot-checked the ambiguous pairs: e.g. EGY's seed "Mostafa Shobeir" vs official "MOSTAFA SHOUBIR..." and "Mohamed Abdelmonem" vs "MOHAMED ABDELMONEIM..." both look like the same player under a different Arabic-name transliteration -- good human-review candidates, not auto-applied. 8 new tests cover the classification/pairing helpers.
- Spec 010 Phase 7: SKIPPED by design, not blocked. The Phase 6 audit found no formula-level issue clearing the spec's bar for a change -- host_advantage is already clearly visible (+6.3 to +7.1pp), the tactical matchup modifier already points the documented direction, and champion-odds concentration is "reasonable". The only finding (CRO/NED/POR/etc. underperforming their FIFA rank) is a squad-rating data question, not a ModelConfig/tactical-weight/host-advantage/shootout-bounds question, and Spec 010 explicitly forbids "arbitrary changes because one favorite team feels wrong." Tuning a formula constant with no audit evidence behind it would be exactly that. Recommendation for Codex: review CRO/NED/POR/MEX/ARG/ESP/MAR/URU's `qualitative_adjustments`/attributes in `players.json` against current club-season form before considering any rating-data change; no code change proposed here.
- Spec 010 Phase 6: added `backend/scripts/audit_simulation_accuracy.py` (read-only; uses the existing Poisson model and ModelConfig, never mutates seed/report data) and `backend/reports/simulation_accuracy_audit_2026-06-23.json`. Findings: host_advantage is clearly visible (+6.3 to +7.1pp home-win swing for CAN/MEX/USA vs a fixed mid-table reference opponent); the tactical matchup modifier points the documented direction (high-press team at home gets a small positive nudge); champion-odds concentration looks reasonable (top1 18.8%, top3 42.6%, 31/48 teams with nonzero title odds); underdog (bottom-half-by-rank) combined champion-odds stayed low and stable between 100 and 500 Monte Carlo iterations (7.0% vs 6.4%). The most actionable finding: across all-pairs matchups within the top-20 FIFA-ranked teams, CRO (9), NED (8), POR (6), and to a lesser extent MEX/ARG/ESP/MAR/URU (3-4 each) are repeatedly given a less-than-expected win probability for their FIFA rank, suggesting their squad-derived attack/defense/strength ratings (not the formula) may be undershooting their FIFA rank -- flagged as a data-review candidate for Codex, not a formula change. 9 new tests cover the pure classification/aggregation helpers.
- Spec 011 authored by Codex: `docs/specs/011-team-data-review-diagnostics.md` is ready for Claude Code. It asks for a deterministic team data review plan report, read-only diagnostics API, and `/data-review` UI page derived only from existing local reports/seed files.
- Codex parallel match-detail polish: improved `MatchAnalysisPanel` readability by showing turning-point descriptions, momentum dominance labels, team badges for key players, and a text MOM badge without changing match-analysis logic or API shape.

Primary task:

- `docs/specs/011-team-data-review-diagnostics.md`
- This task is intentionally read-only because the next accuracy step requires review prioritization before any seed roster/rating import.
- Spec 010 remains completed context.

Direction-only context:

- `docs/specs/002-match-detail-v2-direction.md`
- `docs/specs/007-official-squad-data-update-direction.md`

## Verification Baseline

Last known baseline from Codex inspection after Spec 009 follow-up:

- Backend tests: `147 passed`
- Frontend build: passed
- Frontend lint: passed
- Local backend: responding on port 8000
- Local frontend: responding on `localhost:5173`
- Browser smoke check: `/teams/BRA` desktop and mobile width passed; official club/caps-goals fields visible; no full-page horizontal overflow detected.
- Browser smoke check: `/`, `/tournament`, `/simulate`, and a generated match detail page passed; no replacement characters, no halfwidth-kana mojibake, and no full-page horizontal overflow detected.
- Browser smoke check: tournament odds panel calculation renders without blank-page failure even when an older local backend response lacks the new explanation fields.
- Production frontend/backend: responding with HTTP 200

## Open Risks

- Do not ask the user for routine implementation or commit approval.
- Claude Code should continue through the overnight sprint phases without routine user confirmation.
- Match Detail v2 beyond trust states should not be implemented until a concrete follow-up spec is written.
- Player/manager data updates must be evidence-based and should not rely on unverifiable claims.
- Formula changes are allowed only inside an explicit experiment phase with before/after reports and tests; arbitrary tuning remains prohibited.
- FIFA Official Squad List diff report parses 48 teams and 26 official players per team. Current seed has roster drift for all 48 teams and coach mismatches for 16 teams; seed updates need a separate reviewed import spec.
- Spec 008 applied 2,360 safe official-profile fields across 472 existing matched players, with no skipped conflicts, no missing IDs, and no players added or removed.
- Spec 009 improved conservative name matching and regenerated read-only official squad reports. After PDF ligature cleanup, remaining roster risk is now 652 official players and 73 seed players unmatched by the current heuristic, down from 776 and 197.
- Spec 009 follow-up applied official-profile fields for newly matched players. Compared with the previous commit, 124 players gained official profile data; 624 official-profile field values changed in total, including cleanup of PDF `fi` ligature extraction artifacts. The regenerated merge proposal now has 0 matched-player field update candidates.
- All backend JSON files currently scan clean for control characters.
- Prediction API disclaimer/explanation tests now check a broader set of mojibake markers.
- Text encoding audit command passes: `cd backend && .\venv\Scripts\python.exe scripts\audit_text_encoding.py`.
- Round of 32 third-place assignment uses candidate-pool constraint solving, not the literal FIFA Annex C 495-row table.
- Tactical UI verification: `cd frontend && npm run lint`, `cd frontend && npm run build`, and `python backend\scripts\audit_text_encoding.py` pass after adding the tactical panels. Local API `/api/teams/BRA` returns tactical profile data and Vite `/simulate` responds with HTTP 200. Full browser pixel smoke was skipped because this environment has no Chrome/Edge executable and the Playwright browser binary is not installed.
- Squad analysis verification: repeated `cd frontend && npm run lint`, `cd frontend && npm run build`, and `python backend\scripts\audit_text_encoding.py` after adding the TeamPage squad analysis panel; all passed.
- Tournament UX verification: repeated `cd frontend && npm run lint`, `cd frontend && npm run build`, and `python backend\scripts\audit_text_encoding.py` after adding tournament highlights and group summary cues; all passed.
- Teams index verification: repeated `cd frontend && npm run lint`, `cd frontend && npm run build`, and `python backend\scripts\audit_text_encoding.py` after adding `/teams`; all passed while Claude's data-quality frontend changes were also present in the worktree.
- Standings UX verification: repeated `cd frontend && npm run lint`, `cd frontend && npm run build`, and `python backend\scripts\audit_text_encoding.py` after adding qualification labels; all passed.
- 404 page verification: repeated `cd frontend && npm run lint`, `cd frontend && npm run build`, and `python backend\scripts\audit_text_encoding.py`; all passed.
- Independent Claude data-quality check: `cd backend && ..\backend\venv\Scripts\python.exe -m pytest` passed with `151 passed, 1 warning` while Claude's uncommitted data-quality implementation was present.
- Spec 010 Phases 1-5 verification: backend `pytest -q` -> `151 passed`; frontend `npx tsc --noEmit` clean; frontend `npm run lint` clean; frontend `npm run build` succeeded (dist output ~300KB JS / ~30KB CSS); `audit_text_encoding.py` passed. Dev servers were stale (no `--reload`) after backend edits, so they were restarted (`Stop-Process -Force` + relaunch `uvicorn`) per the daily-maintenance runbook; `/api/health` and the new `/api/data-quality/summary` both responded after restart.
- Spec 010 Phase 5 browser smoke detail: Playwright (chromium, already installed under a temp dir from a prior session) checked `/`, `/simulate`, `/tournament`, `/teams/BRA`, `/matches/{id}` at 1280px and 390px widths. All 10 checks: 0 mojibake findings, 0 page-overflow, 0 console errors. Screenshots of `/` (desktop + mobile) confirm the new data-quality panel renders correctly and is mobile-safe with no nested-card visual noise.
- Match analysis polish verification: repeated `cd frontend && npm run lint`, `cd frontend && npm run build`, and `python backend\scripts\audit_text_encoding.py`; all passed.

## Next After Current Task

Next Codex actions:

1. Review Spec 011 output and decide whether any team data update/import spec is justified.
2. Keep formula changes frozen until an explicit calibration spec exists.
3. Use the diagnostic output to prioritize CRO/NED/POR and ambiguous roster/name-pair review.
