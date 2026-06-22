# Claude Code Paste Prompt: Unattended Until Noon

以下をClaude Codeへ貼り付ける。

```text
Codexが復帰し、分業方針に沿って次のReadyタスクを作成済みです。

昼12時までユーザーは確認・貼り付け・表示チェックをしません。ここからは、ユーザー確認で止まらない前提で進めてください。

まず以下をディスクから読んでください。

- docs/codex/ROLE_SPLIT.md
- docs/codex/HANDOFF_PROTOCOL.md
- docs/codex/AUTONOMOUS_SPRINT_PROTOCOL.md
- docs/specs/CURRENT_TASK.md
- docs/codex/PROGRESS.md

現在のActive Claude Code Taskは以下です。

- docs/specs/009-official-squad-match-quality.md

実行方針:

1. CURRENT_TASK.mdにあるReadyタスクだけを実装してください。
2. Spec 009の範囲に従い、公式FIFAスカッドの名前マッチング精度を保守的に改善し、read-onlyレポートを再生成してください。
3. ユーザーに「表示は問題ないですか」「コミットしていいですか」などの通常確認をしないでください。
4. Stop条件に該当する場合だけ止まってください。Stop条件は AUTONOMOUS_SPRINT_PROTOCOL.md に従ってください。
5. seed選手の追加・削除、既存seedフィールドの上書き、シミュレーション式・評価式・市場価値・キャリア統計・手動補正の変更は禁止です。
6. 検証コマンドを実行し、合格したらローカルコミットしてください。pushはしないでください。
7. 完了後は、commit hash、変更ファイル、before/afterのunmatched official/seed count、検証結果、残リスクだけを報告してください。

Codex側の最新コミット:

- 0b59fcd Apply safe official squad field updates
- 019eb18 Add official squad match quality spec

この貼り付け以降、昼12時まではユーザー作業を発生させないように進めてください。
```
