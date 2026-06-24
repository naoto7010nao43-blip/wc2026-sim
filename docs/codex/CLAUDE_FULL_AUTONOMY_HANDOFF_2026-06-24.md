# Claude Full Autonomy Handoff - 2026-06-24

## User Paste Prompt For Claude Code

```text
Read these files from disk:

- docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md
- docs/codex/DATA_GOVERNANCE_POLICY.md
- docs/specs/CURRENT_TASK.md
- docs/specs/017-external-data-verification-expansion.md
- docs/specs/018-claude-full-delivery-sprint.md

Codex is currently unavailable, and the user wants you to continue autonomously.

Important: if backend/reports/external_data_verification_candidates_2026-06-24.json is already modified, treat it as your in-progress research. Do not reset or discard it.

Finish Spec 017, then continue directly into Spec 018. Work in long batches, run the required verification, commit locally when each coherent phase passes, and continue to the next phase without asking for routine approval. Ask the user only if a Stop condition applies, or if production push/deploy is needed.

Do not push or deploy unless the user explicitly authorizes production push/deploy.

After each committed phase, report commit hash, changed files, verification results, data/system changes, risks, and the next phase you will continue with.
```

## Why Claude Is Taking Over Temporarily

The user wants the project to keep moving while Codex is usage-limited. Claude Code should now own the implementation sprint, local verification, local commits, and release-candidate preparation. Codex will return later for review, simulation audit, and aftercare.

## What Must Happen First

1. Preserve the current working tree.
2. Continue the modified `backend/reports/external_data_verification_candidates_2026-06-24.json` if present.
3. Complete all 48-team external verification.
4. Add URL-backed citations for material current-field candidates.
5. Regenerate validation, source-traceability, decision-queue, and release-readiness reports.

## Current Red Flag

The existing 121 external candidates are useful, but all currently lack resolvable source URLs. They must not be applied to seed/rating/tactical data until URL-backed citations are added.

This is not a reason to delete them. It is a routing rule:

- URL-backed and high-quality -> possible current-field review candidate.
- No URL -> provisional context or review question.
- Substitution tendency -> future-engine candidate unless the engine feature is implemented.

## Claude's Implementation Authority

Claude may implement everything explicitly described in `docs/specs/018-claude-full-delivery-sprint.md`, including:

- source-backed proposal reports;
- deterministic apply scripts for safe data updates;
- bounded simulation-system features such as a manager substitution profile if evidence supports it;
- diagnostics and UI surfaces;
- release-candidate notes.

Claude must keep data confidence honest and must not push/deploy without explicit user authorization.

## Codex Aftercare Plan

When Codex returns, review:

1. commits since `2f4e578`;
2. final `backend/reports/release_readiness_2026-06-24.json`;
3. any applied data-change reports;
4. any simulation behavior changes;
5. benchmark deltas before/after;
6. `/data-review`, `/simulate`, `/tournament`, `/teams/BRA`, and match detail pages;
7. whether production push/deploy was performed;
8. unresolved risks and proposal-only items.

Codex should then decide whether to:

- approve the release candidate;
- request more source repair;
- revert or narrow any data/system change;
- write a follow-up spec;
- support production deployment if not already done.
