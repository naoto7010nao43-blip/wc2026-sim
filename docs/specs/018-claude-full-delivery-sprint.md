# Spec 018 - Claude Full Delivery Sprint

Status: Ready for Claude Code

## Why This Spec Exists

Codex may be unavailable because of usage limits. The user wants Claude Code to carry implementation, verification, local commits, release-candidate preparation, and aftercare setup as far as possible without routine confirmation.

Codex will return later as reviewer, auditor, and aftercare owner. Until then, Claude Code should treat this file as the active product/data/simulation implementation plan.

## Operating Authority

Claude Code may proceed autonomously through this spec without asking the user for routine approval.

Claude Code may:

- finish external data verification work;
- add or improve read-only diagnostics, reports, tests, and UI surfaces;
- implement bounded system features explicitly described in this spec;
- apply source-backed data changes only through generated reports and deterministic scripts;
- make focused UX/design improvements that improve simulation comprehension, trust, or usability;
- run local verification and commit completed phases.

Claude Code must not:

- push to remote or deploy production unless the user explicitly says production push/deploy is allowed;
- silently mark estimated data as official;
- copy unsupported ratings from market value or reputation alone;
- apply Tier C claims as data;
- apply source claims with no resolvable URL to seed/rating/tactical data;
- perform broad rewrites unrelated to the phases below;
- remove existing user/Codex/Claude work to make a task easier.

If the working tree contains an uncommitted `backend/reports/external_data_verification_candidates_2026-06-24.json`, assume it is Claude Code's in-progress research. Continue from it. Do not discard it.

## Current State To Read First

Read these before editing:

- `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`
- `docs/codex/DATA_GOVERNANCE_POLICY.md`
- `docs/specs/CURRENT_TASK.md`
- `docs/specs/017-external-data-verification-expansion.md`
- `docs/codex/PROGRESS.md`
- `backend/reports/external_data_verification_candidates_2026-06-24.json`
- `backend/reports/external_data_verification_validation_2026-06-24.json`
- `backend/reports/external_data_decision_queue_2026-06-24.json`
- `backend/reports/external_source_traceability_audit_2026-06-24.json`
- `backend/reports/release_readiness_2026-06-24.json`

Known external-data state before Claude resumes:

- 16/48 teams covered.
- 32 teams remain.
- 121 candidates currently exist.
- Decision queue: 73 current-field review candidates, 4 warning-hold candidates, 15 future-engine candidates, 29 provisional-context candidates.
- Source traceability audit: all 121 current candidates lack resolvable URLs. They are useful research signal but blocked for seed/rating/tactical data changes until URL-backed citations are added.

## Phase 0 - Preserve Worktree And Rebuild Baseline

1. Run `git status --short`.
2. Identify uncommitted files. Do not overwrite unrelated or in-progress work.
3. If `backend/reports/external_data_verification_candidates_2026-06-24.json` is modified, parse it and continue from that exact file.
4. Re-run:

```powershell
cd backend
.\venv\Scripts\python.exe scripts\validate_external_data_verification_report.py reports\external_data_verification_candidates_2026-06-24.json --out reports\external_data_verification_validation_2026-06-24.json
.\venv\Scripts\python.exe scripts\audit_external_source_traceability.py
.\venv\Scripts\python.exe scripts\build_external_data_decision_queue.py
```

5. Commit Phase 0 only if it changes reports/docs and the JSON remains valid.

## Phase 1 - Complete External Data Verification For All 48 Teams

Complete Spec 017 fully.

For every remaining team in `scope.remainingUnresearchedTeams`, collect:

- current manager/status;
- base formation and credible alternatives;
- tactical profile evidence: pressing, possession/directness, defensive line/block, transition style;
- key player status: likely starters, missing seed players, stale players, injuries/suspensions, transfers, form;
- national strength context: FIFA rank movement, recent results, qualification form, host/confederation context;
- substitution tendencies: first-sub timing, chasing/leading patterns, bench trust, defensive closing changes, penalty/extra-time preparation.

Hard data rule:

- If a claim may become a current-field candidate, every supporting source must include a resolvable `url`.
- If no URL can be found, keep the claim as `provisional_context` or `review_question`; do not label it ready for current-field data changes.
- Substitution tendencies remain `future-engine candidate` unless/until Phase 5 creates a field and tests it.

Required after each substantial batch:

```powershell
cd backend
.\venv\Scripts\python.exe -c "import json, pathlib; json.loads(pathlib.Path('reports/external_data_verification_candidates_2026-06-24.json').read_text(encoding='utf-8')); print('json ok')"
.\venv\Scripts\python.exe scripts\validate_external_data_verification_report.py reports\external_data_verification_candidates_2026-06-24.json --out reports\external_data_verification_validation_2026-06-24.json
.\venv\Scripts\python.exe scripts\audit_external_source_traceability.py
.\venv\Scripts\python.exe scripts\build_external_data_decision_queue.py
.\venv\Scripts\python.exe scripts\audit_text_encoding.py
```

Commit when all 48 teams are covered, or after a large coherent batch if the work is too big for one commit. Commit message example:

`Expand external data verification coverage`

## Phase 2 - Repair Source Traceability For The First 16 Teams

The existing 16 covered teams have useful candidate signal but no URL-backed citations.

For the first 16 teams, add source URLs for material claims whenever possible:

- ARG, ESP, ENG, FRA, POR, CRO, NED, MEX, BRA, MAR, BEL, GER, URU, COL, USA, JPN.

Do not delete useful claims just because they currently lack URLs. Instead:

- add URLs when findable;
- lower confidence or use tier if the URL is weak;
- move no-URL claims to review-only/provisional context if not verifiable;
- keep sparse-team signal rather than blanking the team out.

Acceptance criteria:

- `external_source_traceability_audit_2026-06-24.json` improves materially from 121/121 missing URL candidates.
- No current-field candidate should remain URL-less.
- Validation remains `valid=true`.

Commit message example:

`Add traceable source URLs to external verification candidates`

## Phase 3 - Build Data Change Proposal Reports, Not Direct Mutations

Before changing seed data, create proposal reports:

- `backend/reports/external_current_field_change_proposals_2026-06-24.json`
- `backend/reports/external_rating_change_proposals_2026-06-24.json`
- `backend/reports/external_tactical_change_proposals_2026-06-24.json`
- `backend/reports/external_roster_change_proposals_2026-06-24.json`

Each proposal row must include:

- team/player IDs;
- current value;
- proposed value;
- source URLs;
- source tiers;
- confidence;
- expected simulator impact;
- why the proposal is safe or why it remains pending.

Proposal rules:

- Tier S/A factual fields can become safe candidates.
- Tier B tactical claims can support a proposal but should remain `external`/estimated, never `official`.
- Tier C can only be a review question.
- Rating changes must be small, bounded, and justified by multiple signals; do not make broad reputation-based jumps.
- Roster additions/removals need Tier S/FIFA/federation evidence or must remain proposals only.

Commit these proposal reports before applying any data changes.

Commit message example:

`Build external data change proposal reports`

## Phase 4 - Apply Only Safe, Bounded Data Updates

After Phase 3, Claude Code may apply safe data updates if all criteria are met:

- proposal exists;
- source URL exists;
- source tier is appropriate;
- field maps to existing seed schema;
- change can be applied deterministically by script;
- generated apply report lists exact changed fields and counts;
- tests and diagnostics pass.

Preferred order:

1. safe factual updates:
   - manager names/status if already represented;
   - club names/transfers;
   - confirmed missing/stale seed roster facts only with Tier S/A evidence;
   - FIFA rank/national context only if already supported by seed schema.
2. formation updates:
   - default formation only when stable and source-backed.
3. tactical profile updates:
   - only when source-backed and bounded;
   - add an apply report and compare model diagnostics before/after.
4. rating updates:
   - only after proposal, source review, and benchmark comparison;
   - cap individual changes unless a very strong case exists;
   - skip if benchmark/smoke suggests worse plausibility.

Required implementation pattern:

- create an apply script under `backend/scripts/`;
- write tests for the apply script;
- write an applied report under `backend/reports/`;
- update `backend/data/seed/metadata.json` honestly;
- regenerate diagnostics that feed `/data-review`;
- run benchmark/report checks relevant to the changed data.

Do not hand-edit large JSON seed files manually.

Commit message examples:

- `Apply traceable factual data updates`
- `Apply bounded tactical profile updates`
- `Apply reviewed rating adjustments`

## Phase 5 - Implement Manager-Specific Substitution Model If Evidence Supports It

The current engine has no manager-specific substitution tendency. If Phase 1/2 yields enough URL-backed substitution evidence, implement a bounded feature.

Recommended design:

- Add a neutral substitution profile with defaults that preserve current behavior.
- Store per-team/manager substitution tendencies as estimated/external metadata, not official fact.
- Candidate fields may include:
  - first_sub_minute_bias;
  - trailing_aggression;
  - leading_defensive_bias;
  - bench_trust;
  - like_for_like_preference;
  - late_penalty_prep_bias.
- Modify substitution logic so neutral defaults match current output as closely as possible.
- Add tests proving:
  - neutral profile preserves baseline behavior;
  - trailing teams can substitute earlier/more aggressively when profile says so;
  - leading teams can prefer defensive closing changes when profile says so;
  - max substitutions and windows remain respected.
- Add UI/report copy explaining that substitution tendencies are estimated and source-backed, not guaranteed.

If evidence is too sparse, do not implement the engine behavior. Instead, keep the candidates in a future-engine report and surface the limitation on `/data-review`.

Commit message example:

`Add manager substitution profile prototype`

## Phase 6 - Improve Simulation Accuracy Diagnostics After Any Data/System Change

After any seed/rating/tactical/model behavior change, rebuild and compare:

- prediction benchmarks;
- simulation accuracy audit;
- team data review plan;
- squad gap review;
- rating workbench;
- rating decision audit;
- source provenance audit;
- external decision queue;
- release readiness.

If a change worsens benchmark plausibility, champion odds stability, or data confidence in a meaningful way, revert only that change or mark it as proposal-only. Do not keep accuracy-regressing changes just because they are interesting.

Expected commands will vary by script availability, but always run:

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\python.exe scripts\audit_text_encoding.py
cd ..\frontend
npm run lint
npm run build
```

Also run browser smoke on:

- `/`
- `/simulate`
- `/tournament`
- `/teams`
- `/teams/BRA`
- `/data-review`
- one detailed match page

Check both desktop and mobile widths when browser tooling is available.

## Phase 7 - UX And Product Polish

Make focused improvements that help users understand and trust the simulator.

Prioritize:

- simulator page clarity: prediction panel, simulation result, seed/decisive controls, same-team empty state;
- tournament page: champion odds stability, bracket/group clarity, model confidence copy;
- match detail page: trust state, event replay availability, stats, tactical notes, key players;
- team pages: likely lineup, squad confidence, source/uncertainty, tactical profile;
- data-review page: clear progress, blockers, decision queues, source traceability;
- mobile usability: no horizontal overflow, readable cards, no oversized text in dense panels.

Avoid:

- marketing-style landing pages;
- decorative noise;
- claims that make estimated data look official;
- visible walls of explanation that distract from the tool.

Commit UX work in focused chunks with lint/build/browser checks.

## Phase 8 - Release Candidate Preparation

When all implementation work is locally complete:

1. Run the full local release gate:

```powershell
.\scripts\pre_release_check.ps1
```

If this fails only because `CURRENT_TASK.md` is active while the implementation is otherwise complete, update `CURRENT_TASK.md` to a completed/awaiting state and rerun.

2. Rebuild release readiness:

```powershell
cd backend
.\venv\Scripts\python.exe scripts\build_release_readiness_report.py
```

3. Create/update:

- `docs/codex/RELEASE_CANDIDATE_NOTES_2026-06-24.md`
- `docs/codex/CLAUDE_FINAL_HANDOFF_2026-06-24.md`

4. Confirm `backend/reports/release_readiness_2026-06-24.json` has:

- `readyForManualPush=true`;
- no missing required reports;
- no dirty git status;
- benchmark status acceptable.

5. Commit release-candidate notes and readiness report.

Do not push/deploy unless the user explicitly writes that production push/deploy is allowed.

## Phase 9 - If User Explicitly Allows Production Push/Deploy

Only after explicit user authorization:

1. Confirm working tree clean.
2. Confirm latest full gate passed.
3. Push the intended branch.
4. If deployment is automatic, monitor build/deploy logs.
5. Run `scripts/post_deploy_smoke.ps1` with production frontend/backend URLs.
6. If post-deploy smoke fails, report immediately and do not hide the failure.
7. Write a production deployment note.

## Stop Conditions

Stop and ask the user only if:

- production push/deploy is needed but not explicitly authorized;
- source access is unavailable for the whole data task;
- a data/system change would require a destructive rewrite;
- verification fails and a focused investigation cannot find a safe fix;
- another agent has conflicting edits in the same files and continuing would overwrite work.

Do not stop for:

- routine commits;
- display approval;
- whether to continue to the next phase;
- sparse team evidence;
- reports that reveal "not enough evidence" if they still preserve useful review questions.

## Final Report Format

After each committed phase, report:

- commit hash;
- changed files;
- phase(s) completed;
- verification commands and results;
- data/system changes made;
- accuracy impact or why impact is proposal-only;
- remaining risks;
- next phase Claude will continue with.

When all phases are done, produce a final handoff for Codex:

- exact commits since this spec began;
- current release readiness;
- what changed in simulation behavior, if anything;
- what data was applied, if any;
- what was left as proposal-only and why;
- browser smoke results;
- production deployment state.
