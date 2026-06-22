# Autonomous Sprint Protocol

This protocol reduces user involvement during Claude Code implementation.

## Goal

The user should not need to approve every small implementation step.

Claude Code may work through a bounded queue of Codex-authored tasks, run verification, and commit when the task meets its acceptance criteria.

## Authority

Claude Code may proceed autonomously only when:

- the task is listed in `docs/specs/CURRENT_TASK.md`
- the task spec says `Status: Ready for Claude Code implementation`
- the task has clear acceptance criteria and verification commands

Claude Code must stop and ask for guidance if:

- it needs new unverifiable player, manager, injury, lineup, or match data
- it would change simulation formulas or rating methodology without an explicit Codex spec
- it would perform a broad refactor not requested by the spec
- tests fail and the cause is unclear after a focused investigation
- implementation requires deleting or replacing large parts of the system
- production deployment or push is requested but local verification fails

## Commit Policy

Claude Code may commit completed work without asking the user again when all are true:

- the work matches the current spec
- the working tree only contains files related to the spec or Codex docs
- required verification commands pass
- the commit message summarizes the spec implemented

Claude Code should not push to remote unless the current spec explicitly says pushing is allowed.

## Reporting Policy

After committing, Claude Code should report:

- commit hash
- changed files
- verification results
- any risks or follow-up suggestions

## Preferred User Prompt

The user may paste this once:

```text
docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md と docs/specs/CURRENT_TASK.md を読んでください。
CURRENT_TASK.md にあるReadyタスクを、仕様に従って自律的に実装・検証・コミットしてください。
途中でユーザー確認が必要なのは、プロトコルのStop条件に該当する場合だけです。
完了後、commit hash・変更ファイル・検証結果・リスクを報告してください。
```

## Codex Review

After Claude Code reports completion, Codex will inspect the repository, rerun important checks when needed, update progress, and decide the next task.
