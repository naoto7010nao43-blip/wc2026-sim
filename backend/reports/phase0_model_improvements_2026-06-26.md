# Phase 0 — モデル側の精度改善（③ 出場可能性ウェイト + ② Dixon-Coles 低スコア補正）

日付: 2026-06-26
対象: `app/prediction/*`（モデル本体のみ。選手データ・FIFAランクは固定）
評価データ: 実際に行われた2026 W杯グループステージ40試合（`data/seed/real_results/*.json`）

## 背景
EA FC 26 由来の選手データ拡充（498名 external 化）は完了したが、予測モデルは
FIFAランク 75% 依存かつ EA 由来チャンネルの重みが小さいため、データ充填だけでは
精度向上が頭打ちになっていた。そこで「データ穴埋め → モデル側改善」へ移行。

## 変更点
### ③ 出場可能性ウェイト（ratings.py）
各選手の `startingProbability`（8〜92）と `availability` を使った `_playing_factor`
を導入。攻撃・守備・スカッド総合の各レーティングで、控え選手や負傷中のスター選手が
チーム評価を不当に押し上げないよう、`overall × 出場可能性` で重み付け・選抜するように
変更。データが無い場合は中立定数にフォールバックするため既存テストは不変。

### ② Dixon-Coles 低スコア補正（poisson_model.py ほか）
独立ポアソンが構造的に過小評価する引き分け・低スコア（0-0, 1-1）を補正する
Dixon-Coles(1997) の tau 補正を `score_distribution` に追加。`ModelConfig.dixon_coles_rho`
で制御し、`monte_carlo.py` / `predicted_match.py` の全呼び出しに伝播。
model_version: `poisson-v2-rank75` → `poisson-v3-dc-startprob`。

## 結果（40試合、本番レーティング）
| 構成 | hit | RPS | Brier | LogLoss | xG MAE |
|---|---|---|---|---|---|
| ベースライン（旧モデル, rho 0, ③なし） | 0.625 | 0.1581 | 0.5475 | 0.9253 | 1.580 |
| ③のみ（rho 0） | 0.625 | 0.1576 | 0.5453 | 0.9236 | 1.580 |
| ③+②（rho −0.10, **採用**） | 0.625 | 0.1566 | 0.5393 | 0.9085 | 1.580 |

確率較正指標（RPS / Brier / LogLoss）が全て一貫して改善。1X2 的中率は変化なし
（DC補正・出場ウェイトは argmax ではなく確率の質を改善するため。40試合の小標本では
的中の入れ替わりは出にくい）。

## rho の選定
sweep は単調（rho を負に振るほど指標改善）だが、40試合への過適合を避け、
Dixon-Coles 文献の慣用域内である **rho = −0.10** を採用。利得の大半を確保しつつ
標本依存を抑える保守的な選択。

## 検証
- `pytest -q`: 410 passed
- `scripts/audit_text_encoding.py`: passed
- `scripts/benchmark_model_improvements.py phase0_final`: 上表を再現
