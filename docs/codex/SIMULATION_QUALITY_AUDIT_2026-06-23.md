# Simulation Quality Audit - 2026-06-23

## Scope

Codex-side audit while Claude Code implements `docs/specs/006-overnight-data-trust-sprint.md`.

This audit does not change formulas. It records current simulation-quality signals and the next highest-value accuracy work.

## Current Baseline

Command run:

```bash
cd backend
.\venv\Scripts\python.exe scripts/analyze_simulation_quality.py
```

Aggregate output across 10 representative matchups and 60 seeds each:

- Average goals per match: `2.55`
- Draw rate: `25.0%`
- Home win rate: `45.2%`
- Away win rate: `29.8%`
- Average absolute possession deviation from 50%: `4.5`
- Combined shots per match: `19.8`
- Goals per shot on target: `0.35`
- Yellow cards per match: `4.02`

## Read

The micro-simulator is broadly plausible on headline distribution:

- Goals are inside the stated World Cup benchmark band of roughly `2.5-2.8`.
- Draw rate is inside the group-stage benchmark band of roughly `20-27%`.
- Card volume is close to the stated benchmark of roughly `3-4`.
- Goals per shot on target is close enough to the stated target around `0.30`.

The main visible weakness is shot volume:

- Combined shots are `19.8`, below the script's benchmark of roughly `22-26`.
- This may make match detail pages feel slightly sparse even when scores are plausible.

## Calibration Risk

The skill-gap calibration table is directionally reasonable for very large mismatches, but noisy in close and mid-tier matchups:

- Big favourite examples around `+12.5` to `+16.9` average overall gap produce `75-83%` favourite win rates, which is plausible.
- Several small or mid gaps do not order smoothly. Example: a `+3.69` home overall gap still produced a `41.7%` away win rate in the sampled set.

This is not automatically a bug because the sample size is small (`60` seeds per matchup), home/away context matters, and tactical profiles can move outcomes. But it is a signal that future calibration should use a larger, repeatable benchmark suite.

## Data/Model Honesty Risk

The prediction model config explicitly says the Poisson weights have not been backtested. That is currently acceptable only if the UI keeps model disclaimers and data-confidence labels visible.

Highest-risk missing data:

- current injuries and suspensions
- national-team minutes/caps
- confirmed squads/lineups
- recent club form
- calibrated FIFA/Elo blend
- manager tactical changes by opponent

Spec 006 is therefore the right next implementation task: it exposes uncertainty before changing formulas.

## Next Accuracy Work

Recommended next specs after Spec 006:

1. Calibration Harness V1
   - Increase matchup sample size.
   - Separate micro-simulator calibration from Poisson calibration.
   - Produce JSON/Markdown reports checked into `backend/reports/`.
   - Track goals, draws, shots, cards, favourite win rate by rating gap bucket.

2. Data Freshness Dashboard
   - Surface seed metadata age and source tiers in the UI.
   - Mark unavailable injury/suspension data explicitly.
   - Add a "last updated" view for player ratings and team data.

3. Shot Volume Tuning Proposal
   - Do not tune immediately.
   - First inspect whether low shots come from event duration, action choice, shot probability, or possession turnover rates.
   - Any formula change should include before/after audit output.

4. Manager Model V2
   - Current manager model exposes only press intensity, possession style, and defensive line height.
   - Add richer axes only when evidence exists; otherwise keep them labelled as estimated.

## Current Decision

Do not change simulation formulas tonight.

Focus tonight on:

- data trust visibility
- readable explanations
- audit artifacts
- preserving test coverage
