# Handoff Protocol

This document defines how Codex, the user, and Claude Code coordinate work.

## Key Principle

The user should not need to monitor Claude Code in detail.

Codex writes task specs and reviews outcomes. Claude Code implements the current spec. The user should mainly review finished product behavior, not routine intermediate approvals.

For longer runs with fewer user interruptions, use `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`.

## What Codex Can Do

Codex can:

- analyze product direction, data quality, simulation accuracy, and UX
- write or update specs in `docs/specs/`
- update `docs/specs/CURRENT_TASK.md`
- update progress notes in `docs/codex/PROGRESS.md`
- review code changes after Claude Code finishes
- write the next Claude Code prompt for the user to paste when needed

Codex cannot directly operate Claude Code's chat session unless the user forwards the trigger message.

## User Workflow

When Codex says a task is ready, the user can paste a short message to Claude Code:

```text
Read docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md and docs/specs/CURRENT_TASK.md from disk.
Implement, verify, and commit the Ready task. Ask the user only if a protocol Stop condition applies.
```

For review, the user can paste Claude Code's final report back to Codex, or simply tell Codex that Claude finished. Codex will inspect the repository directly.

If Claude Code has committed changes locally, Codex can inspect the commit and working tree directly.

## User Requests

The user should send new requests to Codex in this chat.

Codex will decide whether to:

- answer directly
- update specs
- create a new implementation task for Claude Code
- review current code
- change the roadmap or quality policy

## Claude Code Output Requirements

After each task, Claude Code should report:

- commit hash
- changed files
- summary of changes
- commands run
- results
- risks or follow-up suggestions

Claude Code should not ask "is this okay to commit?" when the autonomous commit policy is satisfied.

## Current Source Of Truth

- Current implementation task: `docs/specs/CURRENT_TASK.md`
- Progress log: `docs/codex/PROGRESS.md`
- Role split: `docs/codex/ROLE_SPLIT.md`
- Autonomous rules: `docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md`
