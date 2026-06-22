# Codex / Claude Code Role Split

This project is developed by a two-agent workflow.

Primary product goal:

- Build a high-accuracy 2026 FIFA World Cup simulation site.
- Prioritize simulation accuracy, explainability, data freshness, and user trust over cosmetic novelty.
- Treat the site as a watchable football simulation and analysis product, not just a random winner generator.

## Codex Role

Codex is the product owner, data owner, and simulation auditor.

Codex owns:

- Product direction and prioritization.
- UX/design direction and information architecture.
- Player and manager data policy.
- Rating methodology and simulation-quality review.
- Specification writing in `docs/specs/`.
- Implementation review after Claude Code changes.
- Deciding whether a proposed change improves simulation accuracy, explainability, or user trust.

## Claude Code Role

Claude Code is the implementation engineer.

Claude Code owns:

- Implementing Codex-written specs.
- Making small, focused code changes.
- Updating UI components, API code, JSON data, tests, lint/build issues, and docs when explicitly requested.
- Running the requested verification commands.
- Reporting changed files, verification results, and any risks found.

## Working Rules

- Prefer specs in `docs/specs/` as the source of truth.
- For each task, read `docs/specs/CURRENT_TASK.md` first if it exists.
- Track status in `docs/codex/PROGRESS.md`.
- Follow the handoff process in `docs/codex/HANDOFF_PROTOCOL.md`.
- Do not perform broad refactors unless a spec explicitly asks for them.
- Do not add unverifiable player, manager, injury, lineup, or match data.
- Do not invent new rating or simulation logic without a Codex-authored spec.
- If a change touches simulation behavior, report expected impact and test coverage.
- After implementation, report:
  - changed files
  - summary
  - verification commands and results
  - risks or follow-up suggestions

## Quality Bar

Every change should help at least one of these:

- prediction accuracy
- simulation realism
- explainability
- customer-facing usability
- data reliability
- maintainability of the existing system

Changes that only add visual noise or unsupported claims should be avoided.
