# Phase 4 (②) — Detailed stats for simulated matches (2026-06-30)

## Goal
The user asked for **detailed match stats on simulated fixtures** (possession,
scorers, etc.). Until now, tournament matches that had *not* been played were
produced by the Poisson statistical model, which outputs **only a scoreline** —
no lineups, no possession, no scorers. Opening such a match showed a bare
"X–Y" with the prediction disclaimer and nothing else. This increment layers a
plausible, clearly-simulated narrative on top of that scoreline.

## What was done

### 1. Narrative builder (`app/prediction/match_narrative.py`, new)
`build_predicted_narrative(...)` takes the two squads, formations, tactical
profiles and the **already-decided** Poisson scoreline, and returns:
- **Starting XIs** for both sides via the shared `build_team_state` selector
  (same 3-pass position/alias/fallback logic the micro-simulator uses), as
  `home_lineup`/`away_lineup` snapshots plus `home_roster`/`away_roster` maps.
- **Possession split** from each side's average starting-XI overall and its
  `possession_style` profile, with a small seeded jitter, clamped to a
  realistic 35–65 band and forced to sum to 100.
- **Shots / shots on target** derived from the Poisson expected goals
  (`lambda`), with on-target between the actual goals scored and total shots.
- **Yellow cards** scaled by each side's `press_intensity`.
- **Goal-scorer events** — exactly `home_score + away_score` `goal` events, each
  attributed to a starting-XI player chosen (with replacement, so braces are
  possible) weighted by **slot goal-propensity × overall** (strikers score
  most, defenders rarely, the keeper effectively never). Minutes are seeded and
  sorted.

The scoreline is **never** altered: the count of goal events always equals the
Poisson result, and every figure is a deterministic function of the match seed,
so re-fetching a match is stable.

### 2. Wired into the predicted-match persister (`app/services/predicted_match.py`)
After sampling the scoreline (and any shootout), `run_and_persist_predicted_match`
now calls the narrative builder and persists the full picture: lineups, rosters,
`home/away_possession_pct`, `home/away_shots`, `home/away_shots_on_target`,
`home/away_yellow_cards`, and the event timeline
(`kickoff` → sorted goals → optional `penalty_shootout` → `fulltime`). The
`data_source` stays **`"poisson-model"`** — these remain predictions, not real data.

### 3. Honest frontend presentation (`frontend/src/pages/MatchDetailPage.tsx`)
Added a distinct `predicted_detail` match kind so the UI never implies these
stats are real or that a full minute-by-minute simulation occurred:
- Badge **`予測スコア＋推定スタッツ`** (distinct from `詳細シミュレーション` and `実結果`).
- Description: *"期待得点モデルが予測したスコアに、選手データから推定したスタッツ
  （ボール保持率・シュート数）と得点者を付加した結果です。スタッツと得点者は推定であり、
  実際の試合ではありません。"*
- The existing StatRow block (possession / shots / on-target / cards) and the
  goal-scorer timeline now render for these matches.

## Validation
- New `tests/test_match_narrative.py` — 6 tests: goal events equal the
  scoreline and map to real XI players; events time-ordered; possession sums to
  100 and favours the stronger side; shots ≥ on-target ≥ goals; full elevens;
  deterministic per seed.
- Full backend suite: **418 passed**.
- End-to-end `run_full_tournament` smoke: a simulated R16 fixture carries
  possession, shots, full 11-vs-11 lineups and goal events equal to its
  scoreline, while the 4 real R32 results stay `is_real`.
- Frontend `tsc -b` clean.

## Honesty notes (data governance)
- All stats here are **simulation estimates**, explicitly labelled as such in
  the UI and kept under `data_source="poisson-model"`. No real-world claim is
  made; no values were fabricated as "official".
- The scoreline (the genuinely predictive part) is untouched; the narrative is
  presentation detail on top of it.
