# 🎓 Beehive チュートリアル

Claude Multi-Agent Development System の初心者向け段階的学習ガイド

## 📋 目次

- [このチュートリアルについて](#このチュートリアルについて)
- [第1章: 環境構築](#第1章-環境構築)
- [第2章: 基本操作](#第2章-基本操作)
- [第3章: タスク管理](#第3章-タスク管理)
- [第4章: Bee間通信](#第4章-bee間通信)
- [第5章: 実践演習](#第5章-実践演習)
- [第6章: カスタマイズ](#第6章-カスタマイズ)

---

## このチュートリアルについて

### 対象読者
- Beehiveシステムを初めて使用する開発者
- マルチエージェントシステムに興味がある方
- Claude CLI を活用した開発を学びたい方

### 前提知識
- 基本的なコマンドライン操作
- Python の基礎知識
- tmux の基本概念（推奨）

### 学習時間
- **全体**: 約3-4時間
- **各章**: 30-45分程度

### 必要なもの
- macOS / Linux 環境
- Python 3.12以上
- Claude CLI アカウント
- tmux >= 3.0

---

## 第1章: 環境構築

### 1.1 前提ツールのインストール

#### tmux のインストール

```bash
# macOS (Homebrew)
brew install tmux

# Ubuntu/Debian
sudo apt install tmux

# 確認
tmux -V
# tmux 3.4 などと表示されればOK
```

#### Claude CLI のインストール

```bash
# Claude CLI をインストール（公式手順に従ってください）
# https://claude.ai/cli

# インストール確認
claude --version

# 認証設定
claude configure
```

#### uv のインストール

```bash
# uvをインストール（Pythonパッケージマネージャー）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 確認
uv --version
```

### 1.2 Beehive のセットアップ

#### リポジトリの取得

```bash
# 1. プロジェクトをクローン
git clone https://github.com/nyasuto/hive.git
cd hive

# 2. 必要なツールの確認
make help
```

#### 依存関係のインストール

```bash
# 3. 開発環境セットアップ（全自動）
make dev-setup

# 期待する出力:
# 📦 Setting up Beehive environment...
# ✅ Environment ready
# 🐝 Beehive PoC ready!
# 🚀 Development environment fully configured!
```

#### 初期化の確認

```bash
# 4. データベースの確認
ls -la hive/hive_memory.db

# 5. システム初期化
./beehive.sh init

# 期待する出力:
# 🚀 Initializing Beehive system...
# ✅ tmux session 'beehive' created
# ✅ All agents initialized and ready
```

### 1.3 動作確認

```bash
# システム状態確認
./beehive.sh status

# 期待する出力例:
# 🐝 Beehive System Status
# ===========================
# Session: beehive ✅ Active
# Queen Bee (0.0): ✅ Ready
# Developer Bee (0.1): ✅ Ready
# QA Bee (0.2): ✅ Ready
# Analyst Bee (0.3): ✅ Ready
```

**🎉 第1章完了！** 環境構築ができました。

---

## 第2章: 基本操作

### 2.1 tmux セッションの理解

#### セッション構造の確認

```bash
# tmux セッション一覧
tmux list-sessions

# ペイン一覧
tmux list-panes -t beehive

# 出力例:
# beehive:0.0: Queen Bee (80x24)
# beehive:0.1: Developer Bee (80x24)
# beehive:0.2: QA Bee (80x24)
# beehive:0.3: Analyst Bee (80x24)
```

#### セッションへの接続

```bash
# Beehive セッションに接続
./beehive.sh attach

# または直接tmuxで
tmux attach-session -t beehive
```

**tmux 基本操作**:
- `Ctrl+B` + `0/1/2/3`: ペイン切り替え
- `Ctrl+B` + `d`: セッションから切り離し
- `Ctrl+B` + `"`: ペイン分割（水平）
- `Ctrl+B` + `%`: ペイン分割（垂直）

### 2.2 データベースの確認

#### SQLite データベースの構造

```bash
# データベース接続
sqlite3 hive/hive_memory.db

# テーブル一覧表示
.tables

# 期待する出力:
# bee_messages    bee_states      send_keys_log
# task_activity   tasks
```

#### 基本クエリの実行

```sql
-- Bee状態確認
SELECT bee_name, status, last_heartbeat FROM bee_states;

-- テーブル構造確認
.schema tasks

-- 終了
.quit
```

### 2.3 ログシステムの理解

#### ログファイルの確認

```bash
# ログディレクトリ
ls -la logs/

# リアルタイムログ監視
tail -f logs/beehive.log

# JSON形式でログを整形表示
tail -f logs/beehive.log | jq .
```

#### ログの種類

```json
// 一般的なログエントリの例
{
  "timestamp": "2025-07-23T09:00:00.000000",
  "level": "INFO",
  "logger": "beehive.queen",
  "message": "Task created successfully",
  "module": "queen_bee",
  "function": "create_task",
  "line": 123,
  "extra": {
    "task_id": 1,
    "bee_name": "queen"
  }
}
```

**🎉 第2章完了！** 基本操作を理解しました。

---

## 第3章: タスク管理

### 3.1 最初のタスク作成

#### 簡単なタスクを開始

```bash
# タスク投入（Queen Bee がタスクを受け取り処理開始）
./beehive.sh start-task "Hello World アプリケーションを作成してください"

# 実行例:
# 🐝 Submitting task to Queen Bee...
# 📝 Task: Hello World アプリケーションを作成してください
# ✅ Task submitted successfully
```

#### タスクの進行状況を確認

```bash
# システム状態を定期的に確認
./beehive.sh status

# ログで詳細確認
./beehive.sh logs | tail -20
```

### 3.2 Python API を使ったタスク管理

#### Queen Bee との直接操作

```python
# Python対話モードで実行
python3

# Queen Bee インスタンス作成
from bees.queen_bee import QueenBee
queen = QueenBee("queen")

# タスク作成
task_id = queen.create_task(
    title="サンプルAPI作成",
    description="FastAPIでHello WorldのAPIエンドポイントを作成",
    priority="medium"
)

print(f"作成されたタスクID: {task_id}")

# タスク詳細確認
task_details = queen.get_task_details(task_id)
print(f"タスク詳細: {task_details}")
```

#### タスクの割り当て

```python
# Developer Bee にタスクを割り当て
success = queen.assign_task(
    task_id=task_id,
    to_bee="developer",
    notes="API実装をお願いします"
)

print(f"割り当て結果: {success}")

# 進捗確認
progress = queen.get_task_progress(task_id)
print(f"進捗状況: {progress}")
```

### 3.3 タスクライフサイクルの理解

#### タスクの状態遷移

```python
# タスク状態の確認
import sqlite3

conn = sqlite3.connect("hive/hive_memory.db")
cursor = conn.execute("""
    SELECT task_id, title, status, assigned_to, created_at
    FROM tasks 
    ORDER BY created_at DESC 
    LIMIT 5
""")

for row in cursor:
    print(f"ID: {row[0]}, Title: {row[1]}, Status: {row[2]}, Assigned: {row[3]}")

conn.close()
```

#### 状態遷移のパターン

1. **pending** → タスク作成直後
2. **in_progress** → Bee が作業開始
3. **completed** → 作業完了
4. **failed** → エラーにより失敗

**🎉 第3章完了！** タスク管理の基本を習得しました。

---

## 第4章: Bee間通信

### 4.1 メッセージ送信の基本

#### CLI を使った通信

```bash
# Queen Bee から Developer Bee へメッセージ送信
python -m bees.cli send beehive 0.1 "Hello, Developer Bee! 作業状況はいかがですか？" \
    --type greeting \
    --sender queen

# 期待する出力:
# ✅ Message sent to beehive:0.1
```

#### メッセージ送信の確認

```bash
# send-keys ログで通信履歴を確認
sqlite3 hive/hive_memory.db "
SELECT timestamp, session_name, pane_id, substr(message_content, 1, 50) as preview
FROM send_keys_log 
ORDER BY timestamp DESC 
LIMIT 5;
"
```

### 4.2 Python API を使った通信

#### Worker Bee の作成と通信

```python
# Developer Bee インスタンス作成
from bees.worker_bee import WorkerBee
developer = WorkerBee("developer")

# Queen Bee にメッセージ送信
message_id = developer.send_message(
    to_bee="queen",
    message_type="status_report",
    subject="作業進捗報告",
    content="Hello Worldアプリの実装が50%完了しました",
    priority="normal"
)

print(f"送信されたメッセージID: {message_id}")
```

#### メッセージ受信と処理

```python
# 受信メッセージの確認
messages = developer.get_messages(processed=False)
print(f"未処理メッセージ数: {len(messages)}")

for msg in messages:
    print(f"From: {msg['from_bee']}")
    print(f"Subject: {msg['subject']}")
    print(f"Content: {msg['content'][:50]}...")
    
    # メッセージを処理済みにマーク
    developer.mark_message_processed(msg['message_id'])
```

### 4.3 構造化メッセージの理解

#### tmux 経由で送信されるメッセージ形式

```markdown
## 📨 MESSAGE FROM QUEEN

**Type:** task_assignment
**Subject:** 新しいタスクの割り当て
**Task ID:** 123

**Content:**
Hello World アプリケーションの実装をお願いします。
- FastAPI を使用してください
- ポート8000で起動するように設定
- /health エンドポイントも追加

---
```

#### メッセージタイプの種類

- `task_assignment`: タスク割り当て
- `status_report`: 進捗報告
- `question`: 質問・相談
- `response`: 回答・応答
- `notification`: 通知
- `error_report`: エラー報告

**🎉 第4章完了！** Bee間通信をマスターしました。

---

## 第5章: 実践演習

### 5.1 演習1: TODOアプリの作成

#### 課題内容

**目標**: シンプルなTODOアプリケーションをBeehiveで作成

**要件**:
- FastAPI バックエンド
- TODO項目のCRUD操作
- SQLite データベース使用
- 基本的なフロントエンド（HTML）

#### 実践手順

```bash
# 1. タスク投入
./beehive.sh start-task "TODOアプリケーションを作成してください。FastAPIとSQLiteを使用し、CRUD操作ができるWebアプリを実装してください。"

# 2. 進行状況の監視
watch -n 5 './beehive.sh status'
```

#### 進行中の観察ポイント

1. **Queen Bee**: タスクの分解・計画
2. **Developer Bee**: コード実装
3. **QA Bee**: テスト実行・品質確認
4. **Analyst Bee**: コード品質分析

### 5.2 演習2: 手動介入による学習

#### ワーカービーとの直接対話

```bash
# tmux セッションに接続
./beehive.sh attach

# Developer Bee ペインに切り替え（Ctrl+B, 1）
# 直接指示を入力:
```

#### Developer Bee への追加指示例

```markdown
## 追加要求: API仕様の改善

以下の機能を追加実装してください：
1. TODO項目の優先度設定（high, medium, low）
2. 期限日の設定機能
3. 完了日時の記録
4. フィルタリング機能（状態・優先度別）

実装後、QAに完了報告をお願いします。
```

### 5.3 演習3: エラー対応の学習

#### 意図的なエラーを発生させる

```python
# Python で意図的にエラーを発生
from bees.queen_bee import QueenBee
queen = QueenBee("queen")

# 無効なタスクデータでエラーを発生
try:
    task_id = queen.create_task("", "", "invalid_priority")
except Exception as e:
    print(f"期待通りエラーが発生: {e}")
```

#### エラーログの分析

```bash
# エラーログの確認
grep -i "error" logs/beehive.log | tail -5

# データベースのエラー状態確認
sqlite3 hive/hive_memory.db "
SELECT bee_name, status FROM bee_states WHERE status = 'error';
"
```

#### エラーからの復旧

```python
# Bee状態の手動リセット
from bees.base_bee import BaseBee
bee = BaseBee("developer")
bee._update_bee_state("idle")

print("✅ Bee状態をリセットしました")
```

**🎉 第5章完了！** 実践的な使用方法を習得しました。

---

## 第6章: カスタマイズ

### 6.1 カスタムBeeの作成

#### 新しい専門Beeクラスの実装

```python
# bees/designer_bee.py を作成
from .worker_bee import WorkerBee
from typing import Any, Dict

class DesignerBee(WorkerBee):
    """UI/UXデザイン専門のBee"""
    
    def __init__(self, bee_name: str = "designer", config=None):
        super().__init__(bee_name, config)
        self.design_tools = ["figma", "sketch", "adobe_xd"]
    
    def create_wireframe(self, requirements: Dict[str, Any]) -> str:
        """ワイヤーフレーム作成"""
        # ワイヤーフレーム作成ロジック
        wireframe_path = f"designs/wireframe_{requirements['feature_name']}.html"
        
        # 実装例（簡略化）
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>{requirements['feature_name']} Wireframe</title></head>
        <body>
            <h1>{requirements['feature_name']} - ワイヤーフレーム</h1>
            <div class="container">
                <!-- ワイヤーフレーム内容 -->
            </div>
        </body>
        </html>
        """
        
        with open(wireframe_path, 'w') as f:
            f.write(html_content)
        
        return wireframe_path
    
    def _handle_work_instruction(self, instruction: str) -> None:
        """デザイン指示の処理"""
        if "ワイヤーフレーム" in instruction or "wireframe" in instruction.lower():
            # ワイヤーフレーム作成タスク
            self.logger.info("ワイヤーフレーム作成タスクを受信")
            # 実装ロジック
        else:
            super()._handle_work_instruction(instruction)
```

### 6.2 設定のカスタマイズ

#### カスタム設定ファイルの作成

```python
# custom_config.py
from bees.config import BeehiveConfig

class CustomBeehiveConfig(BeehiveConfig):
    """カスタム設定クラス"""
    
    def __init__(self):
        super().__init__()
        # カスタムペイン構成
        self.pane_mapping.update({
            "designer": "0.4",
            "devops": "0.5"
        })
        
        self.pane_id_mapping.update({
            "designer": "0.4",
            "devops": "0.5"
        })
        
        # カスタムログレベル
        self.log_level = "DEBUG"
        
        # カスタムデータベースパス
        self.hive_db_path = "custom/my_hive.db"
```

#### カスタム設定の使用

```python
# カスタム設定でBeeを作成
from custom_config import CustomBeehiveConfig
from bees.designer_bee import DesignerBee

config = CustomBeehiveConfig()
designer = DesignerBee("designer", config)
```

### 6.3 ワークフローのカスタマイズ

#### カスタムワークフロークラス

```python
# custom_workflow.py
from bees.queen_bee import QueenBee
from bees.designer_bee import DesignerBee
from bees.worker_bee import WorkerBee

class DesignDrivenWorkflow:
    """デザイン駆動開発ワークフロー"""
    
    def __init__(self):
        self.queen = QueenBee("queen")
        self.designer = DesignerBee("designer")
        self.developer = WorkerBee("developer")
        self.qa = WorkerBee("qa")
    
    def execute_design_first_development(self, project_requirements: str):
        """デザインファースト開発の実行"""
        
        # 1. デザインタスク作成
        design_task_id = self.queen.create_task(
            title="UI/UXデザイン作成",
            description=f"要件: {project_requirements}",
            priority="high"
        )
        
        # 2. デザイン実行
        self.queen.assign_task(design_task_id, "designer")
        
        # 3. デザイン完了後、開発タスク作成
        # (実際はイベント駆動で実装)
        dev_task_id = self.queen.create_task(
            title="フロントエンド実装",
            description="デザインに基づいてUI実装",
            priority="high"
        )
        
        # 4. 開発とテストの並行実行
        self.queen.assign_task(dev_task_id, "developer")
        
        return {
            "design_task_id": design_task_id,
            "dev_task_id": dev_task_id
        }
```

### 6.4 監視ダッシュボードの作成

#### 簡単な Web ダッシュボード

```python
# dashboard.py
from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def dashboard():
    """メインダッシュボード"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """システム状態API"""
    conn = sqlite3.connect("hive/hive_memory.db")
    
    # Bee状態取得
    cursor = conn.execute("SELECT bee_name, status, last_heartbeat FROM bee_states")
    bee_states = [{"name": row[0], "status": row[1], "heartbeat": row[2]} 
                  for row in cursor.fetchall()]
    
    # アクティブタスク数取得
    cursor = conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    task_counts = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "bee_states": bee_states,
        "task_counts": task_counts
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

#### ダッシュボード HTML テンプレート

```html
<!-- templates/dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Beehive Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .status-card { border: 1px solid #ccc; padding: 10px; margin: 10px; border-radius: 5px; }
        .status-healthy { border-color: green; }
        .status-error { border-color: red; }
    </style>
</head>
<body>
    <h1>🐝 Beehive System Dashboard</h1>
    
    <div id="bee-status"></div>
    <div id="task-chart">
        <canvas id="taskCanvas" width="400" height="200"></canvas>
    </div>

    <script>
        // 定期的に状態を更新
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateBeeStatus(data.bee_states);
                    updateTaskChart(data.task_counts);
                });
        }
        
        function updateBeeStatus(beeStates) {
            const container = document.getElementById('bee-status');
            container.innerHTML = '<h2>Bee Status</h2>';
            
            beeStates.forEach(bee => {
                const card = document.createElement('div');
                card.className = `status-card status-${bee.status === 'idle' ? 'healthy' : 'error'}`;
                card.innerHTML = `
                    <h3>${bee.name}</h3>
                    <p>Status: ${bee.status}</p>
                    <p>Last Heartbeat: ${bee.heartbeat}</p>
                `;
                container.appendChild(card);
            });
        }
        
        // 5秒ごとに更新
        setInterval(updateStatus, 5000);
        updateStatus(); // 初回実行
    </script>
</body>
</html>
```

**🎉 第6章完了！** カスタマイズの基本を習得しました。

---

## 🏆 チュートリアル完了！

### 習得したスキル

✅ **環境構築**: tmux, Claude CLI, Python環境のセットアップ  
✅ **基本操作**: システム状態確認、ログ監視、データベース操作  
✅ **タスク管理**: タスク作成、割り当て、進捗確認  
✅ **Bee間通信**: メッセージ送信・受信、通信プロトコル理解  
✅ **実践演習**: 実際のアプリケーション開発体験  
✅ **カスタマイズ**: 独自Bee作成、設定変更、ワークフロー定義  

### 次のステップ

#### 🆕 初級者向け（完了後すぐ）
1. **[API Reference](api_reference.md)** - 今学んだ機能の詳細仕様を確認
2. **実践プロジェクト**: 複数のAPIエンドポイントを持つWebアプリ作成
3. **エラー体験学習**: 意図的なエラーを発生させて対応スキル向上

#### 🛠️ 中級者向け（1-2週間後）
1. **[開発者ガイド](developer_guide.md)** - 本格的な開発ワークフロー・テスト戦略を習得
2. **カスタムBee開発**: [第6章カスタマイズ](tutorial.md#第6章-カスタマイズ)を参考に特定ドメイン向けBee作成
3. **ワークフロー最適化**: プロジェクトに合わせた独自フローの構築

#### 🏗️ 上級者向け（1ヶ月後）
1. **[運用ガイド](operations_guide.md)** - 本番運用・監視システムの実装
2. **パフォーマンス最適化**: 大規模タスクでの効率化手法
3. **セキュリティ強化**: 本番環境での安全な運用・脆弱性対策

### 🔗 継続学習リソース
- **[ドキュメント目次](README.md)** - 対象読者別学習パス
- **[開発者ガイド実装ガイドライン](developer_guide.md#実装ガイドライン)** - プロダクション品質のコード作成
- **[運用ガイドトラブルシューティング](operations_guide.md#トラブルシューティング)** - 実際の問題解決スキル

### よくある質問と回答

#### Q: Beeが応答しなくなった場合は？

```bash
# 1. 状態確認
./beehive.sh status

# 2. 個別Bee再起動
tmux send-keys -t beehive:0.1 C-c
python -m bees.cli send beehive 0.1 "$(cat roles/developer.md)" --type role_injection

# 3. システム全体再起動
./beehive.sh stop
./beehive.sh init
```

#### Q: データベースが破損した場合は？

```bash
# 1. 整合性チェック
sqlite3 hive/hive_memory.db "PRAGMA integrity_check;"

# 2. バックアップから復元
cp backups/latest_backup.db hive/hive_memory.db

# 3. 新規作成（最終手段）
rm hive/hive_memory.db
python bees/init_test_db.py
```

#### Q: 独自の開発フローを作りたい場合は？

```python
# カスタムワークフロークラスを作成
class MyCustomWorkflow:
    def __init__(self):
        self.queen = QueenBee("queen")
        # カスタムBeeを追加
        
    def execute_my_flow(self, requirements):
        # 独自のタスク分解・割り当てロジック
        pass
```

### コミュニティ・サポート

- **GitHub Issues**: [https://github.com/nyasuto/hive/issues](https://github.com/nyasuto/hive/issues)
- **Discussions**: プロジェクト議論・質問
- **Pull Requests**: 機能改善・バグ修正の貢献

### フィードバックのお願い

このチュートリアルを完了された方は、ぜひフィードバックをお聞かせください：

1. **難易度**: 適切でしたか？
2. **内容**: 不足している部分はありますか？
3. **実用性**: 実際の開発で役立ちそうですか？

---

## 🎉 おめでとうございます！

あなたは Beehive Claude Multi-Agent Development System の基本から応用まで幅広くマスターしました。

この知識を活用して、効率的でスケーラブルな開発プロジェクトを成功させてください！

---

**🔄 最終更新**: 2025-07-23  
**📋 対象バージョン**: v1.0.0  
**🎯 完了時間**: 約3-4時間  
**✨ 次回**: 実践プロジェクトでの活用