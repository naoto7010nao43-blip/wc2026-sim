# Data Governance Policy

Purpose: keep the 2026 World Cup simulator accurate, current, and honest while allowing long autonomous work sessions.

This policy applies to player, manager, team, fixture, result, rating, injury, suspension, and tactical data.

## Core Rule

No data value should be silently upgraded from estimated to trusted. Every material data change needs a source tier, a generated report, a review path, and a verification run.

## Source Tiers

### Tier S

Authoritative tournament sources.

Examples:

- FIFA official squad list
- FIFA official fixtures/results
- FIFA official rankings
- federation official squad or medical releases

Allowed use:

- match results
- squad membership
- coach name
- player biographical fields
- caps/goals if present in the official document

### Tier A

High-quality specialist or structured sources, but not the tournament authority.

Examples:

- World Football Elo Ratings
- club/federation sites
- established statistical providers
- Transfermarkt-derived market values when already part of the project provenance

Allowed use:

- secondary calibration inputs
- market-value context
- club affiliation checks
- minutes/form support when the source is fresh

### Tier B

News and editorial reporting.

Allowed use:

- injury/suspension candidates
- likely lineup hints
- tactical trend notes

Restriction:

- must remain labelled as provisional unless confirmed by Tier S/A.

### Tier C

Unstructured fan content, social speculation, unsourced tables, or model-generated claims.

Allowed use:

- never as a direct source for seed data
- can only create a review question for Codex

## Required Import Workflow

1. Generate a read-only report under `backend/reports/`.
2. Include source name, source tier, observed timestamp, generated timestamp, and changed field counts.
3. Separate safe deterministic updates from ambiguous candidates.
4. Apply only safe updates in a later reviewed spec.
5. Regenerate derived reports after application.
6. Run backend tests, frontend lint/build when UI is touched, and `backend/scripts/audit_text_encoding.py`.
7. Update `backend/data/seed/metadata.json` only when a source is actually checked or integrated.

## Field Rules

- Official results override simulation outputs for completed matches.
- Confirmed squad membership must not be inferred from popularity or club stature.
- Player ratings must not be directly copied from market value alone.
- Manager tactical values must not be changed without a source-backed tactical note or Codex-approved calibration spec.
- Injury and suspension data must include freshness; stale availability data should be hidden or labelled stale.
- Formations can be shown as defaults or likely shapes, not guaranteed lineups.

## Confidence Labels

Use these meanings consistently:

- `official`: direct Tier S tournament/federation source.
- `external`: non-FIFA source or imported structured source with provenance.
- `estimated`: model/project estimate, not verified as a current fact.
- `unknown`: no reliable basis yet.

Do not use `official` for derived ratings just because an official roster field contributed to the calculation.

## Autonomous Work Limits

Claude Code may autonomously:

- add read-only diagnostics
- add UI surfaces for uncertainty
- generate candidate reports
- add tests and guardrails

Claude Code must not autonomously:

- apply ambiguous player additions/removals
- change player ratings or manager tactical values
- change model constants
- mark estimated data as official
- import injury/suspension claims from news without a Codex-authored spec

## Codex Review Checklist

Before approving a data-changing spec:

- Is the source tier appropriate for the field?
- Does the report show exact changed fields and counts?
- Are ambiguous candidates excluded from automatic application?
- Did the change update metadata freshness honestly?
- Did downstream predictions change only where intended?
- Is the UI still clear about uncertainty?
