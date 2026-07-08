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
- `audit_manager_tactical_data`: ~~high優先バンドは未解消のまま残す~~ → **2026-07-09 に解消（下記「実施した対応」参照）**。構造化 `tactical_profile_sources`（verified=true + URL）を46/48チームに整備し、監査は **high=0, medium=15, low=33**。残medium は主に `team_review_band`（ロースター深度/鮮度）や重複戦術値が要因で、根拠欠落ではない。未整備は **KOR/TUN の2チームのみ**（両監督とも大会中に辞任し体制流動中のため意図的に保留）。

`audit_simulation_accuracy` / `build_formation_position_fit_audit` / `build_squad_rating_gap_review` への対応は**主観的判断**を要し、私の2025-26知識は古い（このセッションで監督4件・低評価4件の「バグ」疑いが全て私の誤りだった）ため、正しい・より新しいデータを退行させるリスクが高い。よって不在中は着手せず記録に留めた。

## ユーザー復帰時の推奨アクション（優先順）

1. ~~**戦術根拠候補の構造化レビュー**~~ → **完了（2026-07-09）**。自由文をそのままではなく、各監督をWeb検証のうえ実URLを構造化 `tactical_profile_sources`（verified=true）へ整備。
2. **監査レポート群の再生成**（source_provenance / rating_decision / fifa_squad_diff / manager_tactical_data）— 現データに同期させ、将来の監査を正確化。安全（レポートファイルのみ書き込み）。
3. **NED の squad 評価の妥当性確認（任意）** — simulation_accuracy が最も強く「下回る可能性」を示唆。ただし NED の主力（Gakpo/Depay/Malen/Weghorst 等）は既に妥当なEA値。深堀りは主観的。

## 実施した対応（戦術根拠の整備 — 2026-07-09 完了）

監査が要求する構造化根拠を、**既存の戦術数値（press/possession/line）・フォーメーション・監督名・予測式を一切変えず**に整備した。加算的ドキュメント整備のみ。

**手法（各チーム共通）:**
1. 各監督の実証された戦術的アイデンティティを Web 検証（複数ソースの一致を確認）。
2. 既存の数値と整合することを確認（数値の妥当性を裏付ける根拠として記述。乖離があるケースは数値を変えず透明に橋渡し — 例: SWE Potter の positional 志向 vs 本大会の直線的採用、NZL のOFC予選ポゼッションと本大会ミッドブロックの差、ENG の予選70%ポゼッションと構造優先の poss=62）。
3. 実URLを構造化 `tactical_profile_sources: [{url, verified:true}]` として付与（自由文 `_tactical_profile_basis` は人間可読の根拠ノートとして併存）。

**結果:**
- **46/48チーム**に検証済み構造化ソースを整備（今セッション検証39 + 旧散文8チーム中7を追検証）。監査 **high 5→0**、low 2→33。
- `regenerate_legacy_teams_json()` は LEGACY_FIELD_ORDER 外のキー（`_tactical_profile_basis` / `tactical_profile_sources`）を保持する設計のため、teams.json 直接編集で足り、`test_seed_file_consistency` を含む**フルテスト 481 passed**。
- **KOR/TUN のみ意図的に未整備**: Hong Myung-bo（KOR）は 2026-06-28、Herve Renard（TUN）は 2026-07-04 に**辞任**。辞任監督の体制を現行として検証ソースを付けるのは不適切なため、**現監督のWeb確認と `manager_name` 見直しが先**。これは別軸（監督名の鮮度）の課題として残す。

## このセッションでのその他の変更

- 記憶に網羅監査の結論を記録（`project_wc2026_thorough_audit_clean_2026-07-02`）— 将来セッションが解決済みリード（coach/provenance）を再追跡しないため。
- **注**: teams.json の差分（`_tactical_profile_basis` / `tactical_profile_sources`）はコミット/push未実施（露出トークン不使用の方針）。監査/診断専用フィールドでライブアプリは `teams2026_official.json` からシードするため**サイト挙動に影響せずデプロイ不要**。反映はユーザーのコミット/push、または有効トークン提供後。
