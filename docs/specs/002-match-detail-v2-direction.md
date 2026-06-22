# Spec 002: Match Detail v2 Direction

## Status

Design direction only. Do not implement until Codex writes a concrete task spec.

## Product Goal

Make match detail pages feel like a watchable football simulation and analysis screen.

The customer should understand:

- what happened
- why it happened
- who influenced the result
- how tactics and match state affected the flow
- which information is real, simulated, estimated, or missing

## Priority Order

1. Simulation accuracy and trust.
2. Clear match story.
3. Useful stats and player/manager context.
4. Fast scanning on mobile and desktop.
5. Visual polish that supports analysis.

## Required Content Direction

The match detail experience should eventually expose:

- score, result, round, real-vs-simulated status
- possession, shots, shots on target, cards, penalties
- event timeline with important moments emphasized
- pitch/formation view when lineup data exists
- player ratings and MOM
- scorer and assist information where reliable
- tactical context from manager/team profile
- data confidence labels, such as real result, simulated prediction, estimated, unavailable

## Important Constraints

- Do not fabricate unavailable player-level real-match data.
- Do not imply simulated events are real.
- Do not hide uncertainty.
- Do not add decorative UI that weakens scanability.
- Do not create new simulation formulas in UI code.

## Future Implementation Notes

Potential future tasks:

- Add a compact match header with confidence/source labeling.
- Improve stat rows into a scannable stat panel.
- Group timeline events by match phase.
- Add a tactical summary panel using existing team tactical profiles.
- Show unavailable states cleanly for Poisson-generated tournament matches that have no event log.
- Add expected-goals style output only after backend model support exists.
