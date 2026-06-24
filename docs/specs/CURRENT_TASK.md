# Current Task

Read first:

- `docs/codex/ROLE_SPLIT.md`
- `docs/codex/HANDOFF_PROTOCOL.md`
- `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`
- `docs/codex/DATA_GOVERNANCE_POLICY.md`

## Active Claude Code Task

Ready:

1. Finish `docs/specs/017-external-data-verification-expansion.md`.
2. Continue directly into `docs/specs/018-claude-full-delivery-sprint.md`.

Claude Code should continue without routine user confirmation. The user wants Claude Code to carry implementation, verification, local commits, release-candidate preparation, production publication, and handoff reporting while Codex is unavailable. Codex will return later for review and aftercare.

The user has explicitly authorized production push/deploy after all local release gates pass and `backend/reports/release_readiness_2026-06-24.json` shows `readyForManualPush=true`.

## Critical Worktree Warning

If `backend/reports/external_data_verification_candidates_2026-06-24.json` is already modified when Claude Code starts, assume it is in-progress Claude research. Do not discard it, reset it, or overwrite it from the committed version. Parse it, continue from it, and include it in the next appropriate commit after validation passes.

## Immediate Priority

1. Complete external verification for all 48 teams.
2. Add URL-backed citations to material current-field candidates.
3. Regenerate:
   - `backend/reports/external_data_verification_validation_2026-06-24.json`
   - `backend/reports/external_source_traceability_audit_2026-06-24.json`
   - `backend/reports/external_data_decision_queue_2026-06-24.json`
4. Then execute Spec 018 phases in order.

Known state before this handoff:

- 16/48 teams are already covered.
- Covered teams: ARG, ESP, ENG, FRA, POR, CRO, NED, MEX, BRA, MAR, BEL, GER, URU, COL, USA, JPN.
- 32 teams remain in the JSON `scope.remainingUnresearchedTeams`.
- Current validation result before new Claude work: valid=true, 121 candidates, 16/16 covered teams strong signal, 4 warnings.
- Codex decision queue before new Claude work: 73 current-field review candidates, 4 warning-hold candidates, 15 future-engine candidates, 29 provisional-context candidates.
- Codex source traceability audit before new Claude work: 121/121 candidates missing resolvable URLs. Treat the data as useful signal, but do not apply seed/rating/tactical changes from URL-less claims.

## Autonomy Rules

Claude Code may:

- continue in long batches;
- commit after verification passes;
- proceed from one phase to the next without asking;
- improve UI, diagnostics, reports, tests, and bounded implementation details named in Spec 018;
- create release-candidate notes and final handoff docs.

Claude Code must not:

- delete in-progress work;
- apply URL-less external claims to seed/rating/tactical data;
- apply Tier C claims as data;
- silently mark estimated data as official.

Claude Code must stop before production only if the production target/branch/URLs cannot be determined from local configuration or project docs, or if deployment/post-deploy smoke fails and the safe recovery path is unclear.

## Required Minimum Verification For The Current External-Data Work

Run before committing the completed Spec 017 batch:

```powershell
cd backend
.\venv\Scripts\python.exe -c "import json, pathlib; json.loads(pathlib.Path('reports/external_data_verification_candidates_2026-06-24.json').read_text(encoding='utf-8')); print('json ok')"
.\venv\Scripts\python.exe scripts\validate_external_data_verification_report.py reports\external_data_verification_candidates_2026-06-24.json --out reports\external_data_verification_validation_2026-06-24.json
.\venv\Scripts\python.exe scripts\audit_external_source_traceability.py
.\venv\Scripts\python.exe scripts\build_external_data_decision_queue.py
.\venv\Scripts\python.exe scripts\audit_text_encoding.py
cd ..
git diff --check
```

If code is changed, also run the relevant backend tests and frontend lint/build. Spec 018 lists stronger verification for later implementation phases.

## Current Context

The benchmark-methodology issue has already been fixed by Codex with dual-order synthetic benchmarks. The rank75 model remains justified under corrected benchmarking.

The site currently has `/data-review` diagnostics for:

- release readiness;
- model calibration;
- simulation stability;
- external data verification;
- external decision queue;
- source traceability;
- substitution model gap;
- team/squad/manager/rating/source audits.

Use these diagnostics as product surfaces, not just backend reports.

## Reporting

After each committed phase, Claude Code should report:

- commit hash;
- changed files;
- summary;
- verification results;
- data/system changes made;
- remaining risks;
- next phase to continue.

Do not ask the user whether to commit or whether to continue when verification has passed.

## Completed Context

Completed specs:

- `docs/specs/001-lint-fix.md`
- `docs/specs/003-match-detail-trust-states.md`
- `docs/specs/004-simulator-prediction-panel.md`
- `docs/specs/005-tournament-odds-panel.md`
- `docs/specs/006-overnight-data-trust-sprint.md`
- `docs/specs/008-official-squad-safe-field-apply.md`
- `docs/specs/009-official-squad-match-quality.md`
- `docs/specs/010-unattended-site-quality-sprint.md`
- `docs/specs/011-team-data-review-diagnostics.md`
- `docs/specs/012-squad-rating-gap-review.md`
- `docs/specs/013-manager-tactical-trust-review.md`
- `docs/specs/014-rating-review-workbench.md`
- `docs/specs/015-rating-readiness-data-review.md`
- `docs/specs/016-model-calibration-transparency.md`

Context-only older direction docs:

- `docs/specs/002-match-detail-v2-direction.md`
- `docs/specs/007-official-squad-data-update-direction.md`
