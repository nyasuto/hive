# 📚 Beehive ドキュメンテーション

Claude Multi-Agent Development System の包括的ドキュメント体系

## 🎯 ドキュメント概要

このドキュメントコレクションは、Beehive システムの使用者・開発者・運用者のためのガイドです。

### 📖 対象読者別ガイド

#### 🆕 初めてのユーザー
**推奨順序**: 
1. **[チュートリアル](tutorial.md)** - 段階的学習（3-4時間）
2. **[API Reference](api_reference.md)** - 関数・クラス仕様確認

#### 👨‍💻 開発者
**推奨順序**: 
1. **[開発者ガイド](developer_guide.md)** - セットアップから実装まで
2. **[API Reference](api_reference.md)** - 詳細仕様・使用例
3. **[チュートリアル](tutorial.md)** - 実践演習での理解深化

#### 🛠️ 運用者・システム管理者
**推奨順序**: 
1. **[運用ガイド](operations_guide.md)** - 監視・トラブルシューティング
2. **[開発者ガイド](developer_guide.md)** - システム理解のため
3. **[API Reference](api_reference.md)** - 必要時の参照用

---

## 📋 ドキュメント一覧

### 1. 📖 [チュートリアル](tutorial.md)
**対象**: 初心者・新規ユーザー  
**所要時間**: 3-4時間  
**内容**: 段階的学習ガイド

- ✅ 環境構築（tmux, Claude CLI, Python）
- ✅ 基本操作（システム状態、ログ、データベース）
- ✅ タスク管理（作成、割り当て、進捗確認）
- ✅ Bee間通信（メッセージ送受信、プロトコル）
- ✅ 実践演習（TODOアプリ開発）
- ✅ カスタマイズ（独自Bee作成、設定変更）

### 2. 🛠️ [開発者ガイド](developer_guide.md)
**対象**: システム開発者・コントリビューター  
**所要時間**: 2-3時間  
**内容**: 包括的開発ガイド

- ✅ 環境セットアップ（詳細手順）
- ✅ アーキテクチャ理解（通信・データベース・tmux）
- ✅ 開発ワークフロー（Git、テスト、品質管理）
- ✅ 実装ガイドライン（新Beeクラス、エラーハンドリング）
- ✅ テスト戦略（単体・統合・パフォーマンス）
- ✅ デバッグ・トラブルシューティング

### 3. 🛡️ [運用ガイド](operations_guide.md)
**対象**: システム管理者・運用担当者  
**所要時間**: 2時間  
**内容**: 本番運用・監視ガイド

- ✅ システム監視（状態確認、ログ監視、メトリクス）
- ✅ ヘルスチェック（自動診断、リソース監視）
- ✅ パフォーマンス管理（負荷対策、最適化）
- ✅ トラブルシューティング（エラー分析、復旧手順）
- ✅ 運用自動化（バックアップ、アラート設定）
- ✅ セキュリティ対策（監査、アクセス制御）

### 4. 📚 [API Reference](api_reference.md)
**対象**: 全ユーザー（参照用）  
**所要時間**: 必要時参照  
**内容**: 全パブリック API 仕様書

- ✅ コア通信クラス（BaseBee）
- ✅ エージェントクラス（QueenBee, WorkerBee, AnalystBee）
- ✅ 設定・ログクラス（BeehiveConfig, BeehiveLogger）
- ✅ 例外クラス（全例外階層）
- ✅ CLI関数（send, logs コマンド）
- ✅ 使用例・エラーケース

---

## 🚀 クイックスタート

### 30秒で始める

```bash
# 1. リポジトリクローン
git clone https://github.com/nyasuto/hive.git && cd hive

# 2. 環境セットアップ
make dev-setup

# 3. システム起動
./beehive.sh init

# 4. タスク投入
./beehive.sh start-task "Hello World アプリを作成してください"
```

### 詳細な学習パス

#### 完全初心者（推定4-6時間）
1. **前提知識確認** → tmux, Python基礎
2. **[チュートリアル](tutorial.md)** → 全6章を順番に実施
3. **[API Reference](api_reference.md)** → 必要時参照

#### 開発者（推定3-4時間）
1. **[開発者ガイド](developer_guide.md)** → 実装ガイドライン理解
2. **[API Reference](api_reference.md)** → 詳細仕様確認
3. **実践** → カスタムBee作成・貢献

#### 運用者（推定2-3時間）
1. **[運用ガイド](operations_guide.md)** → 監視・運用手順
2. **[開発者ガイド](developer_guide.md)** → アーキテクチャ理解
3. **実践** → 監視システム構築

---

## 🔗 ドキュメント間リンク

### 主要な相互参照

#### 概念理解の流れ
```
チュートリアル → 開発者ガイド → API Reference
    ↓              ↓               ↓
  基本操作      詳細実装        仕様確認
```

#### 運用フローの流れ
```
開発者ガイド → 運用ガイド → API Reference
    ↓            ↓            ↓
  システム理解   運用手順    障害対応時参照
```

### 関連セクション

#### 環境構築
- **[チュートリアル第1章](tutorial.md#第1章-環境構築)** - 初心者向け段階的手順
- **[開発者ガイド環境セットアップ](developer_guide.md#環境セットアップ)** - 詳細設定・IDE設定

#### アーキテクチャ理解
- **[チュートリアル第2章](tutorial.md#第2章-基本操作)** - 基本概念
- **[開発者ガイドアーキテクチャ](developer_guide.md#アーキテクチャ理解)** - 詳細設計
- **[API Reference コアクラス](api_reference.md#コア通信クラス)** - 技術仕様

#### タスク管理
- **[チュートリアル第3章](tutorial.md#第3章-タスク管理)** - 基本操作
- **[API Reference QueenBee](api_reference.md#queenbee)** - タスク管理API
- **[開発者ガイド実装例](developer_guide.md#実装ガイドライン)** - カスタムタスク実装

#### 通信システム
- **[チュートリアル第4章](tutorial.md#第4章-bee間通信)** - 通信の基本
- **[API Reference BaseBee](api_reference.md#basebee)** - 通信API詳細
- **[開発者ガイド通信パターン](developer_guide.md#アーキテクチャ理解)** - 実装パターン

#### 運用・監視
- **[運用ガイド全体](operations_guide.md)** - 包括的運用手順
- **[開発者ガイドデバッグ](developer_guide.md#デバッグトラブルシューティング)** - 開発時トラブル対応
- **[API Reference ヘルスチェック](api_reference.md#get_health_status)** - 監視API

---

## 🎯 用途別レファレンス

### 開発作業時のドキュメント活用

#### 新機能開発
1. **[開発者ガイド実装ガイドライン](developer_guide.md#実装ガイドライン)** - 実装パターン確認
2. **[API Reference](api_reference.md)** - 使用するクラス・メソッドの仕様確認
3. **[チュートリアル第6章](tutorial.md#第6章-カスタマイズ)** - カスタマイズ例参考

#### バグ修正
1. **[開発者ガイドデバッグ](developer_guide.md#デバッグトラブルシューティング)** - 調査手順
2. **[運用ガイドトラブルシューティング](operations_guide.md#トラブルシューティング)** - 一般的問題と対処
3. **[API Reference 例外クラス](api_reference.md#例外クラス)** - エラー種別確認

#### テスト作成
1. **[開発者ガイドテスト戦略](developer_guide.md#テスト戦略)** - テスト実装例
2. **[API Reference](api_reference.md)** - テスト対象API仕様
3. **[チュートリアル第5章演習](tutorial.md#第5章-実践演習)** - テストのある実装例

### 運用作業時のドキュメント活用

#### 日常監視
1. **[運用ガイドシステム監視](operations_guide.md#システム監視)** - 監視手順・コマンド
2. **[API Reference ヘルスチェック](api_reference.md#get_health_status)** - 監視用API

#### 障害対応
1. **[運用ガイド緊急対応](operations_guide.md#緊急対応手順)** - 復旧手順
2. **[開発者ガイドデバッグ](developer_guide.md#デバッグトラブルシューティング)** - 詳細調査
3. **[API Reference](api_reference.md)** - エラー情報の解釈

#### パフォーマンス改善
1. **[運用ガイドパフォーマンス管理](operations_guide.md#パフォーマンス管理)** - 測定・分析手順
2. **[開発者ガイド実装ガイドライン](developer_guide.md#実装ガイドライン)** - 効率的な実装方法

---

## 🔄 ドキュメント更新情報

### 最新版情報
- **作成日**: 2025-07-23
- **対象バージョン**: v1.0.0
- **作成者**: Analyst Bee (issue #23対応)

### 品質保証
- ✅ **完全性**: 全パブリックAPI網羅
- ✅ **正確性**: 実装と仕様の一致確認済み
- ✅ **実用性**: 実際の使用シナリオに基づく構成
- ✅ **保守性**: 継続的更新が容易な構造

### 更新履歴
| 日付 | 版 | 更新内容 | 担当 |
|------|----|---------|----- |
| 2025-07-23 | 1.0.0 | 初版作成（全ドキュメント） | Analyst Bee |

---

## 📞 サポート・フィードバック

### 質問・問題報告
- **GitHub Issues**: [https://github.com/nyasuto/hive/issues](https://github.com/nyasuto/hive/issues)
- **ラベル**: `documentation`, `question`, `bug` を適切に選択

### 改善提案
- **Pull Requests**: ドキュメント改善のPRは大歓迎
- **Discussions**: 機能要望・アイデア議論

### ドキュメント品質向上
以下の観点でフィードバックをお待ちしています：
- ❓ **不明瞭な説明**: どの部分が理解しにくいか
- 📚 **不足情報**: 追加すべき内容・例
- 🔗 **リンク不備**: 参照しにくい箇所
- 🎯 **実用性**: 実際の作業で役立つか

---

## 📚 関連リソース

### プロジェクト情報
- **メインリポジトリ**: [GitHub - nyasuto/hive](https://github.com/nyasuto/hive)
- **README**: [プロジェクト概要](../README.md)
- **CLAUDE.md**: [Claude開発ガイド](../CLAUDE.md)

### 技術情報
- **Python公式**: [Python.org](https://python.org)
- **tmux**: [tmux GitHub](https://github.com/tmux/tmux)
- **Claude CLI**: [Claude CLI Documentation](https://claude.ai/cli)

---

**🎯 このドキュメント体系があなたのBeehive活用を最大化することを願っています！**

---

*📝 最終更新: 2025-07-23 | 📋 対象バージョン: v1.0.0 | ✨ 品質: AAA級*