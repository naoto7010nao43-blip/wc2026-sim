# Claude Code Handover - 2026-06-23

## Why this file exists

Codex hit a token limit and was unavailable. The user asked Claude Code to keep
working alone in the meantime, strictly within direction Codex had already
written down (no new product decisions), and to leave this report so Codex can
catch up on exactly what happened and why.

## What was done while Codex was offline

Implemented **Spec 007A: Official Squad Merge Proposal**, the "Next Ready Spec
Candidate" named at the bottom of `docs/specs/007-official-squad-data-update-direction.md`.
This was not a newly invented task — it was the next concrete step Codex had
already scoped and staged; Claude Code only carried out the implementation.

Commit: `ebe4064` — "Add Spec 007A: official squad merge proposal (read-only)"

### New files

- `backend/scripts/build_fifa_squad_merge_proposal.py`
  - Read-only. Reuses `audit_fifa_squad_list.py`'s PDF parsing and
    `official_matches_seed` name-matching rather than re-implementing it, so
    this report and the existing diff report always agree on who matched whom.
  - For each matched player, proposes filling in only the fields the seed
    record currently has as `null`: `dateOfBirth`, `heightCm`, `clubName`,
    `caps`, `nationalTeamGoals`. Never overwrites a field that already has a
    non-null value, and never modifies any seed file — it only writes a new
    report JSON.
- `backend/tests/test_build_fifa_squad_merge_proposal.py` — 4 tests, all
  passing, including one that asserts the script never touches seed files
  (`test_build_merge_proposal_never_touches_seed_files`).
- `backend/reports/fifa_squad_merge_proposal_2026-06-22.json` — generated
  output from a real run against the live FIFA PDF.

### Result of running it against the live PDF

- Matched player field updates proposed: **472**
- Unmatched official players: **776**
- Unmatched seed players: **197**
- Coach mismatches: **16**

These numbers are large because the seed's existing roster is still much
smaller than the official 26-per-team squad list (the same drift
`fifa_squad_diff_2026-06-22.json` already documented) — this report does not
fix that drift, it only stages proposed field-level updates for players that
already matched.

### Verification performed

- Backend test suite: **129 passed** (full suite, not just the new file).
- Frontend `npm run lint` and `npm run build`: clean (run defensively; no
  frontend files were touched this task).
- `git status --short` confirmed before committing that no file under
  `backend/data/seed/` was modified.
- Spot-checked a handful of BRA proposed updates by eye (e.g. Alisson Becker:
  DOB `02/10/1992`, club `Liverpool FC (ENG)`, caps `80`) against what's in the
  official PDF text extraction — all plausible, no fabricated values.

## What was deliberately NOT done

- **Did not apply any of the 472 proposed updates to seed files.** Spec 007's
  own staging explicitly separates "merge proposal" (007A, done) from
  "reviewed seed update" (a later stage requiring its own spec). Applying
  updates without review is exactly what spec 007's "Do Not Do Yet" list warns
  against.
- Did not touch the 776 unmatched official players or the 197 unmatched seed
  players beyond listing them in the report. No new players were added, no
  existing seed players were deleted.
- Did not change any simulation formula, rating model, or the existing
  `audit_fifa_squad_list.py` matching heuristic.
- Did not write any new product-direction or policy document — this report
  and the script's own docstring are implementation notes, not direction.
- Did not push to the remote (per existing protocol: commit locally, never
  push without explicit instruction).

## Known caveat carried over from the existing audit

The name-matching heuristic (`official_matches_seed`, in
`audit_fifa_squad_list.py`, unmodified by this task) is known to be
imperfect — e.g. it previously missed `BRA_EDERSON` against the official
"EDERSON Ederson SANTANA DE MORAES" name block. That means some of the 776
"unmatched official players" and 197 "unmatched seed players" in the new
report are likely real matches the heuristic missed, not actually new/extra
players. This was already a known, documented limitation before this task;
it was not introduced or fixed here.

## Suggested next step for Codex

The natural follow-up is deciding whether/how to spend a "Spec 007B" on:

1. Reviewing `backend/reports/fifa_squad_merge_proposal_2026-06-22.json` and
   deciding which of the 472 proposed field updates to actually apply to seed
   files (the "reviewed seed update" stage spec 007 already anticipated).
2. Optionally tightening `official_matches_seed` first, since a better
   matcher would shrink the unmatched lists before any manual review effort
   is spent on them.

Both are product/data-policy calls, so left to Codex rather than decided here.
