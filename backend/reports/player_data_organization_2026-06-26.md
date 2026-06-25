# Existing Player Data — Organization & Audit

**Date:** 2026-06-26
**Purpose:** Tidy/verify the existing player data before progressively vetting FC 26 data
into it (per user direction: 既存のデータの整理 → 段階的に fc26 のデータを吟味).

## Inventory

| File | Count | Notes |
|---|---|---|
| `players2026_official.json` | 669 | identity + career stats + market value (source of truth) |
| `playerRatings2026_estimated.json` | 669 | derived ratings (1 per player) |
| `externalPlayerRatings2026.json` | 11 | EA FC 26 sourced (pilot) |
| `manualPlayerOverrides2026.json` | 0 | empty |
| `teams2026_official.json` | 48 | |

## Integrity — CLEAN

- No duplicate playerIds in either players or ratings.
- Perfect 1:1 mapping: every player has exactly one rating; no orphan ratings.
- All 11 external references resolve to a real player.

## Completeness — CLEAN

- 0 players missing name, primaryPosition, or marketValueEur.
- 0 players with zero/absent career appearances.
- 0 players missing sourceCitations.
- The previously-flagged possibly-fabricated entry "Gevero Markus" (Curaçao) is **not
  present** in the v2 data — already removed by earlier cleanup. Curaçao has 15 v2 players.

## The one real problem: rating compression

Overall distribution (estimated layer): mean 54.8, median 53, min 38, max 79 for estimated
players (the only entries ≥85 are the 11 EA-sourced ones, at 85–91). The mass sits at:

```
45-49: 153    65-69:  62
50-54: 182    70-74:   9
55-59: 105    75-79:   2
60-64: 102    85-91:  11  (all EA-sourced)
```

There is a near-empty band at **70–84**: the estimator tops out around 79, then nothing
until the EA island at 85. World-class players who haven't been EA-sourced yet sit 20–30
points low (e.g. Olise est 75 @ €150M, Rice est 62 @ €124M, Pedri est 66 @ €100M).

This is exactly what the staged FC 26 vetting closes.

## Staging order for FC 26 vetting (impact-ranked)

Market value is a clean impact proxy. Each batch takes the next-highest-value estimated
players, confirms the EA slug/id by web search (never guessing values), examines the six
face stats + overall, and appends to `externalPlayerRatings2026.json`. Top of the queue:

1. Olise (€150M, est 75) · Wirtz (€130M, 70) · Rice (€124M, 62) · Vitinha (€120M, 65)
2. Valverde (€100M, 63) · Musiala (€100M, 68) · Dembele (€100M, 77) · Pedri (€100M, 66) · Alvarez (€100M, 69)
3. Saliba (€95M, 68) · Saka (€95M, 68) · Guler (€90M, 66) · J.Neves (€90M, 61) · Doue (€90M, 70) · Cherki (€90M, 67) · Cubarsi (€90M, 69) · Enzo (€90M, 61)
… and so on down the market-value ranking through the 658 estimated players.
