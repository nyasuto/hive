# 🚀 Beehive クイックスタートガイド

Beehiveマルチエージェントシステムを最速で試すためのガイドです。

## 📋 事前準備チェック

```bash
# 必要なツールが揃っているか確認
which tmux && echo "✅ tmux OK" || echo "❌ tmux 必要"
which claude && echo "✅ claude CLI OK" || echo "❌ claude CLI 必要"  
which python3 && echo "✅ Python OK" || echo "❌ Python 3.12+ 必要"
which uv && echo "✅ uv OK" || echo "⚠️ uv 推奨（pip でも可）"
```

## ⚡ 30秒セットアップ

```bash
# Step 1: プロジェクト取得
git clone https://github.com/nyasuto/hive.git
cd hive

# Step 2: 環境構築（自動）
make dev-setup

# Step 3: 🐝 蜂の巣を起動
./beehive.sh init

# ✅ セットアップ完了！
```

## 🎯 初回タスク実行

```bash
# 1. タスクを投入（Queen Beeが受け取り、Worker Beesに分担）
./beehive.sh start-task "シンプルなTODOアプリを作成してください"

# 2. 実行状況をリアルタイム確認
./beehive.sh attach    # tmuxセッションに接続（Ctrl+B → D で抜ける）

# 3. 状態確認
./beehive.sh status    # 各Beeの状況
./beehive.sh logs      # 実行ログ

# 4. 完了後に停止
./beehive.sh stop
```

## 🔧 sender CLI 体験

```bash
# 1. ドライランで送信テスト
python -m bees.cli send beehive 0.0 "Hello Queen Bee!" --dry-run

# 2. 実際にメッセージ送信（tmux起動中のみ）
python -m bees.cli send beehive 0.0 "New task available" --type notification

# 3. 送信履歴確認
python -m bees.cli logs --limit 5

# 4. JSON形式で詳細確認
python -m bees.cli logs --session beehive --format json
```

## 🐛 よくあるトラブル

### 「Claude起動に失敗」
```bash
# Claudeコマンド確認
claude --version
claude --dangerously-skip-permissions --help

# 解決：最新のClaude CLIをインストール
```

### 「tmuxセッションが見つからない」
```bash
# セッション確認
tmux list-sessions

# 解決：まず ./beehive.sh init を実行
```

### 「依存関係エラー」
```bash
# 環境確認
python --version  # 3.12+ 必要
uv --version

# 解決：依存関係を再インストール
make clean && make install
```

## 📊 動作確認コマンド

```bash
# システム全体の健康状態
make check                           # コード品質チェック
python bees/test_tmux_communication.py  # 通信テスト

# データベース確認
sqlite3 hive/hive_memory.db "SELECT * FROM bee_states;"
sqlite3 hive/hive_memory.db "SELECT * FROM send_keys_log LIMIT 3;"

# tmux確認
tmux capture-pane -t beehive:0 -p    # Queen Beeの画面
tmux capture-pane -t beehive:1 -p    # Developer Beeの画面
```

## 🎮 実験的使用方法

### ドライランモードでの実験
```bash
# 環境変数でドライランモード
export BEEHIVE_DRY_RUN=true
./beehive.sh start-task "実験用タスク"  # 実際のsender CLIなしで動作確認

# シェルヘルパーでの実験
source scripts/send_keys_helper.sh
inject_role "beehive" "0.0" "You are Queen Bee" true  # 最後の true でドライラン
```

### 複数タスクの管理
```bash
# Task 1
./beehive.sh start-task "ユーザー認証システム"

# Task 2（前のタスクが進行中でも投入可能）
./beehive.sh start-task "API エンドポイント作成"

# タスク状況確認
sqlite3 hive/hive_memory.db "SELECT id, status, content FROM tasks;"
```

## 🧹 完全リセット

```bash
# 蜂の巣を完全リセット（DB・セッション・ログ削除）
./beehive.sh stop
rm -f hive/hive_memory.db logs/*.log
python bees/init_test_db.py
./beehive.sh init

# 開発環境も含めて完全リセット
make clean
make dev-setup
```

## 📚 次のステップ

1. **詳細ドキュメント**: `README.md` を読む
2. **開発参加**: `CLAUDE.md` で開発フローを確認
3. **カスタマイズ**: `roles/*.md` でBeeの役割をカスタマイズ
4. **拡張開発**: `bees/` でPythonクラスを拡張

---

## 🆘 サポート

- **Issue**: [GitHub Issues](https://github.com/nyasuto/hive/issues)
- **Discussion**: 質問や提案は Issue で
- **Contributing**: プルリクエスト歓迎

**🎯 目標**: 5分以内にマルチエージェント協調システムを体験できること！