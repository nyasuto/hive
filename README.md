# 🐝 Beehive - Claude Multi-Agent Development System

AIエージェントが協調して開発タスクを遂行する、tmuxベースのマルチエージェントシステム（PoC版）

## 🚀 クイックスタート

### 前提条件
```bash
# 必要なツール
- tmux >= 3.0
- Python 3.12+
- claude CLI
- uv (推奨) or pip
```

### 30秒セットアップ
```bash
# 1. リポジトリクローン
git clone https://github.com/nyasuto/hive.git
cd hive

# 2. 依存関係インストール
make install

# 3. データベース初期化  
python bees/init_test_db.py

# 4. 蜂の巣を起動
./beehive.sh init

# 5. タスク投入（マルチエージェント実行開始）
./beehive.sh start-task "TODO アプリを作成してください"

# 6. 実行状況確認
./beehive.sh status
./beehive.sh attach  # tmuxセッションに接続

# 7. 停止
./beehive.sh stop
```

## 🎯 システム概要

### アーキテクチャ
```
👤 Human → 🐝 Queen Bee → 🔨 Worker Bees (Developer/QA)
              ↓               ↓
          📊 Task Planning  💻 Implementation
              ↓               ↓  
          🗄️ SQLite ← tmux send-keys → 📝 Progress Reports
```

### 通信方式
- **リアルタイム**: tmux send-keys（Claude間直接通信）
- **永続化**: SQLite（タスク状態・進捗・ログ管理）
- **CLI**: Python CLI（send-keys透過保存）

## 🛠️ 主要機能

### 1. マルチエージェント協調
- **Queen Bee**: タスク計画・分解・指示
- **Developer Bee**: コード実装
- **QA Bee**: テスト・品質保証

### 2. 自律実行システム
```python
# Python Beeクラスによる自動化
from bees.queen_bee import QueenBee
from bees.worker_bee import WorkerBee

queen = QueenBee()
task_id = queen.create_task("Create auth system")
queen.assign_task_to_bee(task_id, "developer")
```

### 3. 透過的ログ管理
```bash
# send-keys CLI（全通信を自動記録）
python -m bees.cli send beehive 0.0 "Hello Queen!" --type notification
python -m bees.cli logs --session beehive --limit 10
```

## 📂 プロジェクト構造

```
hive/
├── beehive.sh              # メインオーケストレーター
├── Makefile                # 開発用コマンド
├── bees/                   # Python自律システム
│   ├── cli.py             # send-keys CLI（透過保存）
│   ├── base_bee.py        # 基底Beeクラス
│   ├── queen_bee.py       # Queen Bee（タスク管理）
│   └── worker_bee.py      # Worker Bee（実行）
├── scripts/
│   ├── send_keys_helper.sh # Shell用ヘルパー
│   ├── init_hive.sh       # tmuxセッション作成
│   └── inject_roles.sh    # 役割注入
├── roles/                 # Bee役割定義
│   ├── queen.md
│   ├── developer.md
│   └── qa.md
└── workspaces/           # 各Beeの作業ディレクトリ
    ├── queen/
    ├── developer/
    └── qa/
```

## 🔧 使用方法

### 基本コマンド
```bash
# システム管理
./beehive.sh init                    # 蜂の巣を初期化
./beehive.sh start-task "タスク内容"  # タスク投入
./beehive.sh status                  # 状態確認
./beehive.sh attach                  # tmux接続
./beehive.sh stop                    # システム停止

# 開発用
make check                           # 品質チェック
make test                           # テスト実行
make dev-setup                      # 開発環境セットアップ
```

### send-keys CLI
```bash
# 基本送信
python -m bees.cli send beehive 0.0 "メッセージ" --type notification

# 役割注入
python -m bees.cli send beehive 0.0 "You are Queen Bee" --type role_injection

# ログ確認
python -m bees.cli logs --session beehive --limit 10
python -m bees.cli logs --format json

# ドライラン
python -m bees.cli send beehive 0.0 "test" --dry-run
```

### Shell ヘルパー
```bash
# ヘルパー関数を読み込み
source scripts/send_keys_helper.sh

# 便利関数
inject_role "beehive" "0.0" "You are Queen Bee"
assign_task "beehive" "0.1" "Implement feature X"
send_notification "beehive" "0.2" "Tests completed"
show_send_keys_logs "beehive" 10
```

## 🧪 テスト・デバッグ

### テスト実行
```bash
# Python Beeクラステスト
python bees/test_tmux_communication.py

# send-keys CLIテスト
python -m bees.cli send test_session 0.0 "test" --dry-run

# 統合テスト
make test
```

### デバッグ
```bash
# SQLite確認
sqlite3 hive/hive_memory.db "SELECT * FROM bee_states;"
sqlite3 hive/hive_memory.db "SELECT * FROM send_keys_log ORDER BY created_at DESC LIMIT 5;"

# tmux確認
tmux list-sessions
tmux list-panes -t beehive
tmux capture-pane -t beehive:0 -p
```

## 🎯 実装状況

### ✅ 完了機能
- [x] tmuxベースマルチエージェント環境
- [x] Python Beeクラス自律実行システム
- [x] Queen→Worker タスク割り当て・管理
- [x] Worker→Queen 進捗報告・完了通知
- [x] SQLite永続化（タスク・状態・通信ログ）
- [x] send-keys CLI化・透過保存
- [x] Shell用ヘルパー関数
- [x] CI/CD パイプライン
- [x] 品質チェック・テスト自動化

### 🔄 進行中・予定
- [ ] 忘却対策システム（定期リマインダー）
- [ ] エラーリカバリー・例外処理強化
- [ ] 専門Beeクラス拡張
- [ ] 実行状態可視化
- [ ] パフォーマンス最適化

## 🚨 トラブルシューティング

### よくある問題
```bash
# Claude起動失敗
which claude && claude --version

# tmuxセッション確認
tmux list-sessions | grep beehive

# データベース確認
ls -la hive/hive_memory.db

# 権限確認
chmod +x beehive.sh scripts/*.sh
```

### リセット手順
```bash
# 完全リセット
./beehive.sh stop
rm -f hive/hive_memory.db
python bees/init_test_db.py
./beehive.sh init
```

## 📖 詳細ドキュメント

- **開発ガイド**: `CLAUDE.md`（開発標準・ワークフロー）
- **役割定義**: `roles/*.md`（各Bee詳細仕様）
- **アーキテクチャ**: `bees/README.md`（Python実装詳細）

---

## 🔗 関連リンク

- **Issue Tracker**: [GitHub Issues](https://github.com/nyasuto/hive/issues)
- **CI/CD**: [GitHub Actions](https://github.com/nyasuto/hive/actions)
- **Releases**: [GitHub Releases](https://github.com/nyasuto/hive/releases)

**🎯 現在の実装フェーズ**: PoC（概念実証）完了、本格運用向け機能拡張中