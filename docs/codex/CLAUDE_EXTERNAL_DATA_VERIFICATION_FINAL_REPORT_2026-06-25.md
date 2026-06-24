# 外部データ検証リサーチ 最終報告書（Claude Code作成）

作成日: 2026-06-25
作成者: Claude Code（このセッションで実施した読み取り専用調査の最終まとめ）
対象読者: ユーザー（naoto7010nao43）、および引き継ぎ先のCodex

---

## 1. このタスクの経緯と指示内容

ユーザーから受けた指示（要約）:

1. 選手能力値・監督フォーメーション・戦術・選手交代・国としての能力について、実データで検証してほしい。プログラム/シードファイルは変更せず、別ファイルでの調査結果としてCodexに提供する形でよい。
2. Claude自身でも幅広く・深く調査し、得られる知見を加えてほしい。
3. Codexが別作業中（usage limit等）の間、選手交代の実データ調査と、残り40ヶ国の調査の両方を、確認を減らして自律的に進めてほしい。
4. セッション制限に複数回ぶつかったが、その都度「再開して」の指示で継続。
5. 全ての活動が終わったら、詳細な報告書をファイルにまとめること（本ドキュメント）。

すでにCodex側は、Claudeが先行して作成した16ヶ国分の調査結果（ARG, ESP, ENG, FRA, POR, CRO, NED, MEX, BRA, MAR, BEL, GER, URU, COL, USA, JPN）を検証・採用し、JSON検証スキーマ（`validate_external_data_verification_report.py`）と、出典URLの追跡可能性を見るゲート（`audit_external_source_traceability.py`）、判断キュー生成（`build_external_data_decision_queue.py`）を整備していました。Claudeはこの仕組みに乗って、残り32ヶ国の調査を5バッチ（各8ヶ国）に分けて完了させました。

---

## 2. 実施内容のまとめ

### 調査範囲: 全48ヶ国（ワールドカップ2026出場国フル）

| バッチ | 国 | コミット |
|---|---|---|
| 既存（Codex採用済み） | ARG, ESP, ENG, FRA, POR, CRO, NED, MEX, BRA, MAR, BEL, GER, URU, COL, USA, JPN | `cd7d1e8`（Codex側） |
| バッチ2 | SEN, SUI, IRN, TUR, ECU, KOR, AUT, SWE | `9eceddd` |
| バッチ3 | NOR, AUS, ALG, EGY, CAN, PAN, SCO, TUN | `50e9731` |
| バッチ4 | CIV, CZE, PAR, QAT, KSA, UZB, IRQ, COD | `a760ccc` |
| バッチ5（最終） | RSA, JOR, BIH, CPV, GHA, CUW, HAI, NZL | `cf50c5b` |

各国について、以下4分野を実際のWeb検索（試合結果、公式発表、移籍ニュース、戦術分析記事など）で調査しました:

1. 監督・フォーメーション・戦術プロファイル（press_intensity / possession_style / defensive_line_height）
2. 主力選手3名の現在所属クラブ・負傷状況・フォーム・代表での役割
3. 選手交代の傾向（タイミング、同ポジション交代か戦術的交代か、典型的な交代数）
4. 直近の代表戦績（W杯本大会のグループステージ結果を含む）

### 出力フォーマットの変化

調査開始時、Codexが「出典URLを直接解決できる形（`https://...`）で記録しないと、seed/能力値/戦術値の変更候補としては使えない」というゲート（`audit_external_source_traceability.py`）を整備していたことが判明しました。そのため、バッチ2以降は全てのリサーチエージェントに「主張ごとに実在するクリック可能なURLを明示すること」を必須要件として指示し、構造化JSON（`backend/reports/external_data_verification_candidates_2026-06-24.json`）の各candidateに `sources: [{name, url, tier, observedDate}]` を付与する形に統一しました。

結果として、このファイルの候補件数とURL付与率は以下のように成長しました:

| 時点 | 総候補数 | URL付与済み候補数 | カバー国数 |
|---|---|---|---|
| Codex採用時（バッチ1完了） | 121 | 0（0%） | 16 |
| バッチ2完了後 | 181 | 60（33%） | 24 |
| バッチ3完了後 | 234 | 113（48%） | 32 |
| バッチ4完了後 | 291 | 170（58%） | 40 |
| バッチ5完了後（最終） | **346** | **225（65%）** | **48（全国）** |

すべてのバッチで `validate_external_data_verification_report.py` の検証は `valid: true`、エラー0件、全チームが `signalBand: strong` を達成しています。

---

## 3. 最も重要な発見（優先度順）

### 最優先: 監督の身元情報が完全に古い（5ヶ国）

シードデータの監督名が、すでに解任・後任に代わっている事例が5件見つかりました。これは戦術・采配の推論すべてに影響する、単なる「やや古い」レベルを超えた重大な誤りです。

| 国 | シードの監督 | 実際の監督 | 経緯 |
|---|---|---|---|
| チュニジア | Sami Trabelsi | **Sabri Lamouchi** | 2026年1月、AFCON2025 ラウンド16敗退（マリ戦PK負け）直後に解任 |
| サウジアラビア | Herve Renard | **Georgios Donis** | 2026年4月17日、親善試合2連敗（エジプト0-4、セルビア1-2）後に解任 |
| ウズベキスタン | Srecko Katanec | **Fabio Cannavaro** | 2025年1月、健康問題で辞任。暫定指揮後、2025年10月にカナバーロ就任 |
| チェコ | Ivan Hasek | **Miroslav Koubek** | 2025年10月15日、フェロー諸島戦敗戦（予選）を受けて解任 |
| ガーナ | Otto Addo | **Carlos Queiroz** | 2026年3月31日、強化試合4連敗（オーストリア5-1、ドイツ2-1等）を受けて解任。本大会はケイロスが指揮 |

### 2番目に重大: シード選手が実在しない可能性（キュラソー）

キュラソー代表の「Gevero Markus（CB, overall 52）」という選手が、FIFA登録の26人本大会メンバーのどこにも見当たりませんでした。実際のCB登録選手8名（Sambo, Gaari, van Eijma, Floranus, Obispo, Brenet, Bazoer, Fonville）の中に該当者がいません。これは単なる情報の古さではなく、**シードデータ生成時に架空の選手名が紛れ込んだ可能性**を示しており、データの出自そのものを調査する必要がある最重要フラグです。

### その他の主要な不一致パターン

- **default_formationの不一致（16ヶ国）**: 例えばイングランド（4-3-3→実際4-2-3-1）、日本・韓国（4-2-3-1→3-4-2-1）、スウェーデン（3-4-3→Gyokeres+Isakの2トップ）、カナダ（4-2-3-1→実際は4-4-2 "Maplepressing"）、パナマ（5-4-1→実際3-4-3）、スコットランド（3-5-2→4-4-2/4-2-3-1）など。
- **クラブ移籍・負傷情報の陳腐化（全48ヶ国で確認）**: ほぼ全チームで、シードのクラブ表記が現在の所属と異なる、または負傷で出場できない選手が「主力」として扱われている可能性。
- **FIFAランクの不一致（6ヶ国、双方向）**: ノルウェー（16→27）、カナダ（27→30）、コートジボワール（41→30-33）、カタール（42→56）、DRコンゴ（60→43-46）、ガーナ（61→65）。これらは単一の低信頼ソースに基づくため「要確認の疑問」扱いとし、確定情報とはしていません。
- **キャプテンの取り違え（3ヶ国）**: カタール（実際はAl-Haydos、Afifではない）、ガーナ（実際はJordan Ayew、Kudus/Parteyではない）、南アフリカ（実際はGK Ronwen Williams）。
- **選手の能力値が実態より明らかに低い（5ヶ国）**: Haaland 84→EA公式90、Odegaard 76→87、Sorloth 68→84（いずれもノルウェー）、McTominay 68→85、Tierney 60→77、Adams 58→77（スコットランド）、Salah 78→91、Marmoush 66→84（エジプト）、Caicedo 62→約87相当（エクアドル）、Guler 66（トルコ）。
- **選手のポジション登録ミス**: ボスニアのKenan Piricは実際はGK（CB/CDMではない）、ヨルダンのAl-Rawabdehは実際はMF（CBではない）、カーボベルデのStopiraは実際は左SB（CBではない）。
- **個別の重大な選手状況**: ヨルダンのAl-NaimatはACL断裂で本大会出場ゼロ、ガーナのPartey は性的暴行容疑で訴追中・カナダ入国拒否で1試合欠場、コートジボワールのHallerは本大会メンバー外（負傷からの出場機会不足）。

---

## 4. 既存の検証パイプラインとの関係

Codexが構築した3つの読み取り専用スクリプトを、各バッチごとに必ず実行し、結果を確認した上でコミットしました:

1. `scripts/validate_external_data_verification_report.py` — JSONスキーマ検証、エラー/警告/信号強度の判定
2. `scripts/audit_external_source_traceability.py` — 出典URLの追跡可能性監査（severity: pass / review_required / blocking_for_data_changes）
3. `scripts/build_external_data_decision_queue.py` — 候補を「現行フィールド反映候補」「警告保留」「将来エンジン候補」「暫定文脈」の4キューに分類

最終状態（48ヶ国完了後）:

```
valid: true / errors: 0 / warnings: 18
candidates: 346 / coveredTeams: 48 / signalBand: strong (48/48)
traceability severity: review_required（121/346件がURL未解決。バッチ1で採用された16ヶ国分の旧データが主因）
decision queue: currentFieldReview=216, warningHold=18, futureEngineQueue=37, provisionalContext=75
```

選手交代（substitution）に関する知見は、現行エンジン（`backend/app/engine/management.py`の`maybe_substitute`）に対応フィールドが存在しないため、すべて`future-engine candidate`として保留し、現行データへの直接反映はしていません。これは「将来、監督別の選手交代傾向パラメータを実装する」という、より大きなspec（Spec 018 Phase 5で言及）に向けた素材として残しています。

---

## 5. 今回やらなかったこと（意図的な線引き）

Codexが用意した`docs/specs/018-claude-full-delivery-sprint.md`は、外部データ検証の完了（Phase 1）の先に、URL補完（Phase 2）、データ変更提案書の作成（Phase 3）、安全な範囲でのデータ反映（Phase 4）、選手交代モデルの実装（Phase 5）、UI改善（Phase 7）、リリース準備（Phase 8）まで広く許可していますが、今回はユーザーから明示的に依頼された「外部データの調査」の範囲（Phase 1相当）に専念し、以下は実施していません:

- seed/能力値/戦術値/フォーメーションへの直接反映（Codexの確認・判断を経るべき領域のため）
- 選手交代エンジンの実装変更
- UI/フロントエンドの変更
- 既存16ヶ国分のURL未解決候補へのURL補完作業（Phase 2、今回未着手）
- リリース判定・本番デプロイ関連の作業

これは元々のユーザー・Codex間の役割分担（Claudeは読み取り専用調査、Codexがデータ変更の最終判断者）を維持する判断です。Codexが復帰した際、本報告書と`backend/reports/external_data_decision_queue_2026-06-24.json`を起点に、どの候補を実際のデータ変更に進めるか判断できる状態になっています。

---

## 6. 次にCodexが見るべきファイル

- `backend/reports/external_data_verification_candidates_2026-06-24.json` — 全48ヶ国・346件の生候補データ（出典URL付き）
- `backend/reports/external_data_verification_validation_2026-06-24.json` — スキーマ検証結果
- `backend/reports/external_source_traceability_audit_2026-06-24.json` — 出典追跡可能性監査
- `backend/reports/external_data_decision_queue_2026-06-24.json` — 反映判断用の4分類キュー
- 本ファイル（`docs/codex/CLAUDE_EXTERNAL_DATA_VERIFICATION_FINAL_REPORT_2026-06-25.md`）— 全体サマリーと優先度

---

## 7. コミット履歴（このセッション分）

```
9eceddd  Expand external data verification to 8 more teams (SEN, SUI, IRN, TUR, ECU, KOR, AUT, SWE)
50e9731  Expand external data verification to 8 more teams (NOR, AUS, ALG, EGY, CAN, PAN, SCO, TUN)
a760ccc  Expand external data verification to 8 more teams (CIV, CZE, PAR, QAT, KSA, UZB, IRQ, COD)
cf50c5b  Complete external data verification for all 48 World Cup teams (final batch: RSA, JOR, BIH, CPV, GHA, CUW, HAI, NZL)
```

いずれもローカルコミットのみで、リモートへのpushは行っていません（ユーザー指示・標準ルールに従う）。
