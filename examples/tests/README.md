# テストスクリプト

## 概要

このディレクトリには、新アーキテクチャシステムの動作確認用テストスクリプトが含まれています。

## 利用可能なテスト

### `protocols_test.py`
新プロトコルシステムの包括的なテストスクリプト

**実行方法:**
```bash
python examples/tests/protocols_test.py
```

**テスト内容:**
- 基本プロトコル動作確認
- メッセージタイプバリデーション
- 統合レイヤー機能テスト
- システムアラート・ハートビート機能テスト

**期待される出力:**
```
🎉 全テスト成功！新プロトコルシステムは正常に動作しています。
```

## 使用タイミング

1. **新プロトコルシステム初期確認**: 分散環境起動後
2. **トラブルシューティング**: Issue解決デモ失敗時
3. **システム健全性確認**: 定期的な動作確認

## 関連ドキュメント

- [新アーキテクチャ Issue解決ガイド](../../docs/new_architecture_issue_guide.md)
- [PoC実装ガイド](../../docs/poc-guide.md)