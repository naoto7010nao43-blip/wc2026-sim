# Source Provenance Audit - 2026-06-23

## Purpose

This audit prevents weak or ambiguous source text from flowing into future player-rating changes. It is a read-only gate around the Spec 014 rating review workbench and the Codex decision audit.

No seed data, ratings, formulas, or prediction behavior were changed.

## Added Artifacts

- `backend/scripts/build_source_provenance_audit.py`
- `backend/reports/source_provenance_audit_2026-06-23.json`
- `GET /api/model-diagnostics/source-provenance-audit`
- Backend schema/service/API tests for the new diagnostic endpoint
- Japanese-copy guard coverage for the new user-facing diagnostic fields

## Current Findings

Seed-wide source risk:

- Seed players scanned: 669
- Players with source-risk markers: 59
- Main marker families: EA FC / FC26, Fotmob, WC2026 / World Cup 2026, hat trick, Wikipedia

Rating-decision candidate risk:

- Decision candidates scanned: 80
- Clear later-proposal candidates: 9
- Source-review candidates: 8

## Product Judgment

The 9 clear later-proposal candidates are still not approved rating edits. They are only clean enough to move into a future bounded proposal draft. Every numeric change must still pass:

- direct evidence review;
- the rating update proposal validator;
- benchmark comparison against `prediction_benchmark_baseline_2026-06-23.json`;
- Codex review before any seed file is changed.

The 8 source-review candidates must be checked first because their citations include game-rating calibration, secondary stats sources, or future/near-tournament claims. These can be useful breadcrumbs, but they should not be treated as direct evidence.

## Why This Matters

The simulator's credibility depends more on disciplined data governance than on simply adding more data. This audit makes the next rating update smaller, reviewable, and reversible: it narrows a noisy 80-player candidate list into a small set that can be defended before it affects match probabilities.

