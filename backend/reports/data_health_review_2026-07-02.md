# WC2026 データ健全性レビュー — 2026-07-02

自律作業セッションでの網羅的監査サマリ。**結論: ローカル監査で検出できる範囲では、seedデータや予測式へ即時反映すべき高確度の破綻は見つかっていない。外部事実の最終確認なしに断定的な能力値・監督・戦術変更へ進むべきではない。** 以下は確認した各次元と所見。

## PASS（ローカル監査上の阻害なし）した監査次元

| 監査 | 結果 |
|---|---|
| ローカルデータ整合性（678選手 / 48チーム） | クリーン（null無し・careerStats欠落無し・重複無し・ID集合一致・外部評価の孤児無し・範囲外評価無し） |
| `audit_real_results_integrity` | PASS |
| `build_lineup_engine_parity_audit` | **mismatch 0 / 48** — lineup builder と simulator が全チームで一致 |
| marquee 完備スクリーン（全48チーム top-3） | 完了（欠落は TUR/COD のみ、両方修正済み） |
| フォーメーション | 全48チームが有効な11人を編成 |
| `audit_text_encoding` | PASS |
| source traceability | PASS |

## 精査したフラグ — いずれも「非問題」と判定

### `audit_fifa_squad_list` の「coach mismatch: 16」→ 全て偽陽性
- **15件**は `officialCoachNameBlock=None`（FIFA公式feed側で監督名を抽出できていないケース）。seed側の監督名は既知情報と大きく矛盾していないように見えるが、反映判断前にはURL付き外部ソースで再確認する。
- **1件（IRN）**は音訳違いの可能性が高い: seed "Amir Ghalenoei" vs FIFA "GHALEHNOY Amir"。現時点では同一人物扱いでよいが、表記統一は別途レビュー対象に残す。

### `source_provenance_audit` のレビューキュー → **レポートが古い**
`clear_later_proposal_candidates`（MEX_Pineda, MEX_Jiménez, CRO_Pašalić, CRO_Kovačić）は `current_overall` が異常に低い（48/51/51/56）とするが、**現行の `playerRatings2026_estimated.json` では全てEA外部値に修正済み**（77/77/80/83）。このレポートは修正前（2026-06-25 の rating_decision_audit）に基づく。**信頼する前に再生成が必要。**

## 残る「オープン」項目 — いずれも soft/subjective/deferred（明確な修正ではない）

- `audit_simulation_accuracy`: NED/BRA/MAR/BEL/MEX/URU の squad 評価が FIFA ランクを「下回る可能性」（キャリブレーション観察であってバグではない）。NED が最大（7 matchup）。
- `build_formation_position_fit_audit`: 約40件の out-of-position XI 割当（テンプレート適合上ほぼ不可避、47チームで平均~1件）。
- `build_squad_rating_gap_review`: POR/MEX/JOR/BIH/AUS/PAR に shallow_seed_roster / stale_seed_review_needed。
- `audit_manager_tactical_data`: 全48チームに `_tactical_profile_basis`（戦術値の出典根拠フィールド）が欠落。CRO/IRN/NED/POR を高優先でフラグ。

これらへの対応は全て**主観的判断**を要し、私の2025-26知識は古い（このセッションで監督4件・低評価4件の「バグ」疑いが全て私の誤りだった）ため、正しい・より新しいデータを退行させるリスクが高い。よって不在中は着手せず記録に留めた。

## ユーザー復帰時の推奨アクション（優先順）

1. **監査レポート群の再生成**（source_provenance / rating_decision / fifa_squad_diff）— 現データに同期させ、将来の監査を正確化。安全（レポートファイルのみ書き込み）。
2. **`_tactical_profile_basis` の実装（要ユーザー判断）** — 真実源 `data/seed/teams2026_official.json` にフィールド追加＋再生成マッピング（`apply_external_factual_updates.py` の `LEGACY_FIELD_FROM_V2`）拡張＋整合性テスト確認＋監督ごとの出典調査。スキーマ・機構変更のため付き添いセッション推奨。
3. **NED の squad 評価の妥当性確認（任意）** — simulation_accuracy が最も強く「下回る可能性」を示唆。ただし NED の主力（Gakpo/Depay/Malen/Weghorst 等）は既に妥当なEA値。深堀りは主観的。

## このセッションでの変更

- **シードデータの変更なし**（＝デプロイ不要、GitHub push 不要）。読み取り専用の監査と、記憶ファイル＋本レポートの作成のみ。
- 記憶に網羅監査の結論を記録（`project_wc2026_thorough_audit_clean_2026-07-02`）— 将来セッションが解決済みリード（coach/provenance）を再追跡しないため。
