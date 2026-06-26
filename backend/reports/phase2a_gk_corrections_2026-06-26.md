# Phase 2a — 各国の第1ゴールキーパー修正（スタメンGKの現実整合）

日付: 2026-06-26
対象:
- `app/rating_v2/player_rating_model.py`（`compute_starting_probabilities` に手動オーバーライド対応を追加）
- `scripts/rebuild_player_ratings_v2.py`（オーバーライドを伝播）
- `data/seed/manualPlayerOverrides2026.json`（確定スタメンGKの `startingProbability` を明示）
- `data/seed/players2026_official.json` / `externalPlayerRatings2026.json`（鈴木彩艶を新規追加）
- 派生: `players.json` ミラー再生成、`playerRatings2026_estimated.json` 再ビルド

## きっかけ
ユーザー指摘:「日本の第1GKは鈴木彩艶。スタメンが現実と違う国がある」。
表示スタメン（`lineup_builder.build_likely_lineup`）は `startingProbability` の最大値で
各ポジションのスタメンを選ぶ。その `startingProbability` は
`0.45×クラブ出場時間 + 0.30×市場価値 + 0.25×総合` のチーム内コホート相対値で、
「実際に誰がスタメンか」の代理指標にすぎない。結果、現実の第1GKが控え扱いになる例が出ていた。

## 設計（ガバナンス順守・捏造ゼロ）
代理指標より**実観測（2026 W杯の実スタメン）が優先**されるべき、という原則で、
`compute_starting_probabilities` に「手動オーバーライドが明示の `startingProbability` を
持つ場合はそれを verbatim 採用」する分岐を追加。値は出典付き external 事実
（mylineups.app の2026グループステージ＋各種マッチレポート）として記録。
数値（出場時間・市場価値など）の捏造は行っていない。

## 修正したGK（5チーム、いずれも sp=92 に設定しコホート最上位へ）
| code | 旧スタメン(sp) | 新スタメン(sp) | 根拠 |
|---|---|---|---|
| JPN | Hayakawa 67/sp69 | **Zion Suzuki 74/sp92**（新規追加） | 代表に未収録だった現実の第1GKを追加 |
| GER | Baumann 83/sp62 | **Neuer 84/sp92** | 国際引退撤回し正GK復帰 |
| SUI | Sommer 87/sp60 | **Kobel 86/sp92** | Sommer国際引退後の正GK |
| NZL | Sail/Vicelich | **Crocombe 65/sp92** | 正GK争いを制す |
| ESP | Raya 87/sp52 | **Unai Simon 85/sp92** | De la Fuente が Simon を起用（Raya/Garciaより上） |

検証: `build_likely_lineup` で5チームとも GK スロットが上表の選手を選ぶことを確認。

## 鈴木彩艶（新規選手）の出典
- EA SPORTS FC 26 公式: overall 74, GK Reflexes 76 / Handling 72（player 255981）
  https://www.ea.com/en/games/ea-sports-fc/ratings/player-ratings/zion-suzuki/255981
- fcratings.com（FC26）: 上記＋ 190cm, Parma, 23歳を確認
- Transfermarkt: 市場価値 €20.00m（2026-05-29）
- EA は GK Speed を公開していないため `gkSpeed` は省略（コードは欠落を許容、pace のみ既定値）
- dataConfidence="external"（公式FIFA刊行物ではない）

## 検証
- `pytest -q`: 410 passed（`test_seed_file_consistency`・`test_data_quality` 含む）
- `scripts/audit_text_encoding.py`: passed
- 選手総数 669 → 670（鈴木追加）、external 498 → 499 を反映してカウントテスト更新

## 全48チームGK一括監査（実施済み）
ローカルデータで各国の現行第1GK（sp最大）を一覧化し、現実の2026 W杯スタメンと照合。
上記5チーム以外は正しいか、または妥当な範囲。個別確認した例:
- CAN: Crépeau が現行#1 → Marsch が正式にスタメン指名（St. Clairより上）と確認。現状維持で正解。
- URU: Rochet（Musleraより上）、EGY: El Shenawy — いずれも確認済みで現状維持。
- IRN / KSA / PAR / ECU は実際に正GK争いが拮抗。現行の選択は妥当なため、
  強い証拠が出るまで変更しない（推測でのフリップはガバナンス違反）。

## 残課題（Phase 2b 以降）
- アウトフィールドのスタメン精緻化（収集済みの実XIデータを反映）。
  まず日本（ユーザー明示の例）から着手予定。
