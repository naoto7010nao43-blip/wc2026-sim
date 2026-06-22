# Autonomous Sprint Protocol

This protocol reduces user involvement during Claude Code implementation.

## Goal

The user should not need to approve every small implementation step.

Claude Code may work through Codex-authored tasks, run verification, and commit when the task meets its acceptance criteria.

Default behavior: do not ask the user for routine approval. If the spec is clear and verification passes, commit and report.

## Authority

Claude Code may proceed autonomously only when:

- the task is listed in `docs/specs/CURRENT_TASK.md`
- the task spec says `Status: Ready for Claude Code implementation`
- the task has clear acceptance criteria and verification commands

## Stop Conditions

Claude Code must stop and ask for guidance only if:

- it needs new unverifiable player, manager, injury, lineup, or match data
- it would change simulation formulas or rating methodology without an explicit Codex spec
- it would perform a broad refactor not requested by the spec
- tests fail and the cause is unclear after a focused investigation
- implementation requires deleting or replacing large parts of the system
- production deployment or push is requested but local verification fails

Claude Code should not stop for:

- "Does this look okay?" checks after a small UI task
- "May I commit?" checks when the commit policy is satisfied
- asking the user to inspect pages when verification and smoke checks pass
- routine wording, layout, or loading-state choices already covered by the spec

## Self-Verification For UI Tasks

For UI tasks, Claude Code should self-verify with the best available local checks:

- run the required lint/build commands
- inspect the relevant code path for stale-state, empty-state, and loading regressions
- use existing local APIs/pages when available
- check at least the main states named in the spec
- note any unverified visual risk in the final report

## Commit Policy

Claude Code may commit completed work without asking the user again when all are true:

- the work matches the current spec
- the working tree only contains files related to the spec or Codex docs
- required verification commands pass
- the commit message summarizes the spec implemented

If these conditions are met, commit first, then report. Do not ask the user to choose "commit / do not commit."

Claude Code should not push to remote unless the current spec explicitly says pushing is allowed.

## Reporting Policy

After committing, Claude Code should report:

- commit hash
- changed files
- summary
- verification results
- risks or follow-up suggestions

The report should be final-state oriented. Avoid asking the user for another confirmation unless a Stop condition is active.

## Preferred User Prompt

The user may paste this once:

```text
Read docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md and docs/specs/CURRENT_TASK.md from disk.
Implement the Ready task in CURRENT_TASK.md, run the required verification, and commit when the spec passes.
Do not ask the user for routine display approval or commit approval. Ask only if a Stop condition in the protocol applies.
After committing, report commit hash, changed files, verification results, and risks.
```

## Codex Review

After Claude Code reports completion, Codex will inspect the repository, rerun important checks when needed, update progress, and decide the next task.
