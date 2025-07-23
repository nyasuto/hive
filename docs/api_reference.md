# 🐝 Beehive API Reference

Claude Multi-Agent Development System の全パブリッククラス・関数仕様書

## 📋 目次

- [コア通信クラス](#コア通信クラス)
- [エージェントクラス](#エージェントクラス)
- [設定・ログクラス](#設定ログクラス)
- [例外クラス](#例外クラス)
- [CLI関数](#cli関数)
- [使用例](#使用例)

---

## コア通信クラス

### BaseBee

**モジュール**: `bees.base_bee`  
**説明**: すべてのエージェントの基底クラス。SQLite + tmux send-keys通信プロトコルを提供。

#### コンストラクタ

```python
def __init__(self, bee_name: str, config: BeehiveConfig | None = None)
```

**パラメータ**:
- `bee_name` (str): Bee名 ("queen", "developer", "qa", "analyst")
- `config` (BeehiveConfig, optional): 設定オブジェクト

**例外**:
- `BeeValidationError`: Bee名が無効
- `DatabaseConnectionError`: データベース初期化失敗

#### 主要メソッド

##### send_message()

```python
def send_message(
    self,
    to_bee: str,
    message_type: str,
    subject: str,
    content: str,
    task_id: int | None = None,
    priority: str = "normal"
) -> int
```

他のBeeにメッセージを送信（tmux send-keys使用）

**パラメータ**:
- `to_bee` (str): 送信先Bee名
- `message_type` (str): メッセージタイプ
- `subject` (str): 件名
- `content` (str): 本文
- `task_id` (int, optional): 関連タスクID
- `priority` (str): 優先度 ("low", "normal", "high")

**戻り値**: メッセージID (int)

##### get_messages()

```python
def get_messages(self, processed: bool = False) -> list[dict[str, Any]]
```

自分宛のメッセージを取得

**パラメータ**:
- `processed` (bool): 処理済みメッセージを取得するか

**戻り値**: メッセージ辞書のリスト

##### update_task_status()

```python
def update_task_status(self, task_id: int, status: str, notes: str | None = None)
```

タスク状態を更新

**パラメータ**:
- `task_id` (int): タスクID
- `status` (str): 新しい状態
- `notes` (str, optional): 更新ノート

##### get_health_status()

```python
def get_health_status(self) -> dict[str, Any]
```

現在の健全性状態を取得

**戻り値**: 健全性情報辞書

---

## エージェントクラス

### QueenBee

**モジュール**: `bees.queen_bee`  
**継承**: `BaseBee`  
**説明**: タスク管理・計画・Worker Bee調整を担当

#### 主要メソッド

##### create_task()

```python
def create_task(
    self,
    title: str,
    description: str,
    priority: str = "medium",
    requirements: list[str] | None = None,
    dependencies: list[int] | None = None
) -> int
```

新しいタスクを作成

**パラメータ**:
- `title` (str): タスクタイトル
- `description` (str): タスク詳細
- `priority` (str): 優先度 ("low", "medium", "high", "critical")
- `requirements` (list[str], optional): 要件リスト
- `dependencies` (list[int], optional): 依存タスクIDリスト

**戻り値**: 作成されたタスクID (int)

##### assign_task()

```python
def assign_task(self, task_id: int, to_bee: str, notes: str | None = None) -> bool
```

タスクをWorker Beeに割り当て

**パラメータ**:
- `task_id` (int): 割り当てるタスクID
- `to_bee` (str): 割り当て先Bee名
- `notes` (str, optional): 割り当てノート

**戻り値**: 割り当て成功 (bool)

##### get_task_progress()

```python
def get_task_progress(self, task_id: int | None = None) -> dict[str, Any]
```

タスク進捗を取得

**パラメータ**:
- `task_id` (int, optional): 特定タスクID (省略時は全タスク)

**戻り値**: 進捗情報辞書

### WorkerBee

**モジュール**: `bees.worker_bee`  
**継承**: `BaseBee`  
**説明**: 実際の作業実行を担当する基底クラス

#### 主要メソッド

##### accept_task()

```python
def accept_task(self, task_id: int) -> bool
```

タスクを受け入れて実行開始

**パラメータ**:
- `task_id` (int): 受け入れるタスクID

**戻り値**: 受け入れ成功 (bool)

##### report_progress()

```python
def report_progress(
    self,
    task_id: int,
    progress_percentage: int,
    status_message: str,
    deliverables: list[str] | None = None
)
```

作業進捗をQueenに報告

**パラメータ**:
- `task_id` (int): 報告対象タスクID
- `progress_percentage` (int): 進捗率 (0-100)
- `status_message` (str): 状況メッセージ
- `deliverables` (list[str], optional): 成果物リスト

### AnalystBee

**モジュール**: `bees.analyst_bee`  
**継承**: `WorkerBee`  
**説明**: コード分析・品質評価・レポート生成専門エージェント

#### 主要メソッド

##### analyze_code_quality()

```python
def analyze_code_quality(
    self,
    target_path: str,
    analysis_type: str = "comprehensive"
) -> dict[str, Any]
```

コード品質分析を実行

**パラメータ**:
- `target_path` (str): 分析対象パス
- `analysis_type` (str): 分析タイプ ("basic", "comprehensive", "security")

**戻り値**: 分析結果辞書

##### generate_report()

```python
def generate_report(
    self,
    analysis_data: dict[str, Any],
    report_format: str = "markdown",
    output_path: str | None = None
) -> str
```

分析結果レポートを生成

**パラメータ**:
- `analysis_data` (dict): 分析データ
- `report_format` (str): 出力形式 ("markdown", "html", "json")
- `output_path` (str, optional): 出力パス

**戻り値**: 生成されたレポートパス (str)

---

## 設定・ログクラス

### BeehiveConfig

**モジュール**: `bees.config`  
**説明**: システム設定管理クラス

#### 属性

```python
session_name: str = "beehive"
hive_db_path: str = "hive/hive_memory.db"
log_level: str = "INFO"
db_timeout: float = 30.0
pane_mapping: dict[str, str]
pane_id_mapping: dict[str, str]
```

#### 主要メソッド

##### get_config()

```python
def get_config(config_path: str | None = None) -> BeehiveConfig
```

設定オブジェクトを取得

**パラメータ**:
- `config_path` (str, optional): 設定ファイルパス

**戻り値**: BeehiveConfigインスタンス

### BeehiveLogger

**モジュール**: `bees.logging_config`  
**説明**: 構造化ログ機能を提供

#### 主要メソッド

##### log_event()

```python
def log_event(self, event_type: str, message: str, **kwargs)
```

構造化イベントログを記録

**パラメータ**:
- `event_type` (str): イベントタイプ
- `message` (str): ログメッセージ
- `**kwargs`: 追加メタデータ

---

## 例外クラス

### BeehiveError

**モジュール**: `bees.exceptions`  
**説明**: Beehiveシステムの基底例外クラス

#### 継承クラス

- `DatabaseError`: データベース関連エラー
  - `DatabaseConnectionError`: 接続エラー
  - `DatabaseOperationError`: 操作エラー
- `CommunicationError`: 通信関連エラー
  - `TmuxCommandError`: tmux実行エラー
  - `MessageDeliveryError`: メッセージ配信エラー
- `ValidationError`: 検証関連エラー
  - `BeeValidationError`: Bee検証エラー
  - `BeeNotFoundError`: Bee未発見エラー
- `ConfigurationError`: 設定関連エラー
- `WorkflowError`: ワークフロー関連エラー
  - `TaskExecutionError`: タスク実行エラー

#### 使用例

```python
try:
    bee = BaseBee("invalid_name")
except BeeValidationError as e:
    print(f"Validation error: {e.reason}")
except DatabaseConnectionError as e:
    print(f"Database error: {e.db_path}")
```

---

## CLI関数

### send コマンド

**モジュール**: `bees.cli`

```bash
python -m bees.cli send <session_name> <pane_id> <message> [options]
```

**オプション**:
- `--type <type>`: メッセージタイプ
- `--sender <sender>`: 送信者名
- `--metadata <json>`: メタデータ
- `--dry-run`: 実行せずにプレビュー

### logs コマンド

```bash
python -m bees.cli logs [options]
```

**オプション**:
- `--session <name>`: セッション名でフィルタ
- `--limit <n>`: 表示件数制限
- `--format <format>`: 出力形式 ("text", "json")

---

## 使用例

### 基本的なエージェント作成

```python
from bees.queen_bee import QueenBee
from bees.worker_bee import WorkerBee

# Queen Bee初期化
queen = QueenBee("queen")

# Worker Bee初期化
developer = WorkerBee("developer")

# タスク作成
task_id = queen.create_task(
    title="ログイン機能実装",
    description="ユーザー認証システムを作成",
    priority="high",
    requirements=["セキュリティ要件準拠", "テストカバレッジ90%以上"]
)

# タスク割り当て
success = queen.assign_task(task_id, "developer", "優先度高でお願いします")

# 進捗確認
progress = queen.get_task_progress(task_id)
print(f"Progress: {progress}")
```

### メッセージ通信

```python
# メッセージ送信
message_id = queen.send_message(
    to_bee="developer",
    message_type="task_assignment",
    subject="新しいタスクの割り当て",
    content="ログイン機能の実装をお願いします",
    task_id=task_id,
    priority="high"
)

# メッセージ受信
messages = developer.get_messages(processed=False)
for msg in messages:
    print(f"From: {msg['from_bee']}, Subject: {msg['subject']}")
    developer.mark_message_processed(msg['message_id'])
```

### 分析タスク

```python
from bees.analyst_bee import AnalystBee

# Analyst Bee初期化
analyst = AnalystBee("analyst")

# コード品質分析
analysis_result = analyst.analyze_code_quality(
    target_path="./src",
    analysis_type="comprehensive"
)

# レポート生成
report_path = analyst.generate_report(
    analysis_data=analysis_result,
    report_format="markdown",
    output_path="./reports/quality_analysis.md"
)

print(f"Report generated: {report_path}")
```

### エラーハンドリング

```python
from bees.exceptions import BeeValidationError, DatabaseConnectionError

try:
    bee = BaseBee("unknown_bee")
except BeeValidationError as e:
    print(f"Bee name validation failed: {e.reason}")
    print(f"Valid bee names: {', '.join(['queen', 'developer', 'qa', 'analyst'])}")
except DatabaseConnectionError as e:
    print(f"Database connection failed: {e.db_path}")
    print("Please check if database is initialized")
```

### ヘルスチェック

```python
# 個別Beeのヘルスチェック
health = bee.get_health_status()
print(f"Database healthy: {health['database_healthy']}")
print(f"Tmux healthy: {health['tmux_session_healthy']}")

# ワークロード確認
workload = bee.get_workload_status()
print(f"Active tasks: {workload['active_tasks']}")
print(f"Unread messages: {workload['unread_messages']}")
```

---

## 📚 関連ドキュメント

### 📖 学習・理解
- **[チュートリアル](tutorial.md)** - 初心者向け段階的学習（3-4時間）
- **[開発者ガイド](developer_guide.md)** - セットアップから実装まで（2-3時間）

### 🛠️ 実装・開発
- **[開発者ガイド実装ガイドライン](developer_guide.md#実装ガイドライン)** - 新Beeクラス作成
- **[開発者ガイドテスト戦略](developer_guide.md#テスト戦略)** - テスト実装方法
- **[チュートリアル第6章](tutorial.md#第6章-カスタマイズ)** - カスタマイズ例

### 🛡️ 運用・監視
- **[運用ガイド](operations_guide.md)** - システム監視・トラブルシューティング（2時間）
- **[運用ガイドヘルスチェック](operations_guide.md#ヘルスチェック)** - 監視用API活用

### 🔗 ナビゲーション
- **[ドキュメント目次](README.md)** - 全ドキュメント概要・学習パス

---

**🔄 最終更新**: 2025-07-23  
**📋 対象バージョン**: v1.0.0  
**✅ カバレッジ**: 全パブリック API 100%