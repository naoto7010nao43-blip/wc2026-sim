# Claude Code Paste Prompt: Aggressive Unattended Sprint

以下をClaude Codeへ貼り付ける。

```text
Codexが方針を更新しました。今後は安全な小作業だけでなく、Codexが後でレビューできる形なら、より攻めたシミュレーション精度改善・UI改善も進めてください。

ユーザーは昼12時まで細かい確認をしません。確認待ちで止まらないでください。

まず以下をディスクから読んでください。

- docs/codex/ROLE_SPLIT.md
- docs/codex/HANDOFF_PROTOCOL.md
- docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md
- docs/specs/CURRENT_TASK.md
- docs/specs/010-unattended-site-quality-sprint.md
- docs/codex/PROGRESS.md

現在のActive Claude Code Taskは:

- docs/specs/010-unattended-site-quality-sprint.md

重要:

1. Spec 010は拡張済みです。Phase 1-10まであります。
2. データ品質API/UIだけでなく、シミュレーション精度監査、フォーミュラ改善実験、未マッチロスター候補レポート、試合詳細分析強化まで進めてください。
3. 途中で「続けていいですか」「表示確認してください」「コミットしていいですか」と聞かないでください。
4. 変更はローカルコミットしてください。pushは禁止です。
5. seed選手の追加/削除、根拠なしの選手能力変更、捏造データ投入は禁止です。
6. ただし、Spec 010 Phase 7の範囲内なら、before/afterレポートとテストを付けた小さなシミュレーション式調整は許可されています。
7. 1フェーズが詰まっても、docs/codex/PROGRESS.mdに理由を書いて次の安全なフェーズへ進んでください。
8. 全フェーズが早く終わった場合も、Spec 010 Phase 10の自律ループに従い、次の高インパクト改善を続けてください。

直近のCodex側コミット:

- 9b6d16d Add unattended site quality sprint spec
- f49c819 Expand unattended sprint into simulation audit

完了報告には、commit hash、完了/スキップしたフェーズ、変更ファイル、検証結果、ブラウザ確認、残リスクだけを書いてください。
```
