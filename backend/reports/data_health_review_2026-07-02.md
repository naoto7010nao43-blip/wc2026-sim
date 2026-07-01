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
- `audit_manager_tactical_data`: 自由文の `_tactical_profile_basis` 候補が追加されたが、Codexレビューで「自由文があるだけでは根拠ありにしない」と判断。`tactical_basis_candidate_review_2026-07-01.json` に候補を退避し、監査側は構造化・URL付き・verified=true の根拠だけを認めるように変更した。high優先バンドは未解消のまま残す。

`audit_simulation_accuracy` / `build_formation_position_fit_audit` / `build_squad_rating_gap_review` への対応は**主観的判断**を要し、私の2025-26知識は古い（このセッションで監督4件・低評価4件の「バグ」疑いが全て私の誤りだった）ため、正しい・より新しいデータを退行させるリスクが高い。よって不在中は着手せず記録に留めた。

## ユーザー復帰時の推奨アクション（優先順）

1. **戦術根拠候補の構造化レビュー** — URLなし候補、403候補、本文未確認候補を分ける。自由文をそのままseed根拠にしない。
2. **監査レポート群の再生成**（source_provenance / rating_decision / fifa_squad_diff / manager_tactical_data）— 現データに同期させ、将来の監査を正確化。安全（レポートファイルのみ書き込み）。
3. **NED の squad 評価の妥当性確認（任意）** — simulation_accuracy が最も強く「下回る可能性」を示唆。ただし NED の主力（Gakpo/Depay/Malen/Weghorst 等）は既に妥当なEA値。深堀りは主観的。

## 実施した対応（戦術根拠候補の安全化）

`audit_manager_tactical_data` がフラグする「戦術プロフィールの根拠情報が無い」ガバナンス欠落に対し、自由文候補を直接採用せず、レビューキューとして扱う方針に変更した。

- 25チームに `_tactical_profile_basis` 候補文が存在し、URLは合計51件。機械到達性では48件が200、3件が403、8チームはURLなし。
- `build_tactical_basis_candidate_review.py` を追加し、候補文を `tactical_basis_candidate_review_*.json` に構造化して退避する。
- `audit_manager_tactical_data` は、自由文 `_tactical_profile_basis` ではなく、将来の `tactical_profile_sources[].verified === true` のような構造化根拠だけを `has_tactical_basis=true` とみなす。
- 既存の戦術数値（press/possession/line）、フォーメーション、監督名、予測式は変更しない。
- これにより、未検証のURL付き文章で監査が「解消済み」に見えるリスクを避ける。

## このセッションでのその他の変更

- 記憶に網羅監査の結論を記録（`project_wc2026_thorough_audit_clean_2026-07-02`）— 将来セッションが解決済みリード（coach/provenance）を再追跡しないため。
- **注**: teams.json の `_tactical_profile_basis` 候補差分はコミット/pushしない。構造化・本文確認・verified判定を経るまでseedには入れない。
