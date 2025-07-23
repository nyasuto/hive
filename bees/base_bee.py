#!/usr/bin/env python3
"""
Base Bee Class - 基本的な通信機能
Issue #4: 基本的な自律実行システム
Issue #22: コード品質・エラーハンドリング強化

SQLite + tmux sender CLI 通信プロトコルによる自律エージェント基底クラス
"""

import json
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import BeehiveConfig, get_config
from .exceptions import (
    BeeValidationError,
    DatabaseConnectionError,
    DatabaseOperationError,
    TaskExecutionError,
    wrap_database_error,
)
from .logging_config import get_logger


class BaseBee:
    """
    基本的な通信機能を持つBeeクラス

    すべてのBeeの基底クラス。データベース通信、tmux通信、
    エラーハンドリング、構造化ログ機能を提供。

    Args:
        bee_name: Bee名（例: "queen", "developer")
        config: 設定オブジェクト（省略時はデフォルト設定）

    Raises:
        BeeValidationError: Bee名が無効な場合
        DatabaseConnectionError: データベース初期化に失敗した場合
    """

    def __init__(self, bee_name: str, config: BeehiveConfig | None = None):
        # 設定の初期化
        self.config = config or get_config()

        # Bee名の検証
        self._validate_bee_name(bee_name)
        self.bee_name = bee_name

        # パス設定
        self.hive_db_path = Path(self.config.hive_db_path)
        self.session_name = self.config.session_name
        self.pane_map = self.config.pane_mapping
        self.pane_id_map = self.config.pane_id_mapping

        # ログ設定
        self.logger = get_logger(bee_name, self.config)

        # 接続状態の追跡
        self._db_connection_healthy = False
        self._tmux_session_healthy = False

        # 初期化
        try:
            self._init_database()
            self._update_bee_state("idle")
            self.logger.info(f"Bee '{bee_name}' initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize bee '{bee_name}'", error=e)
            raise

    def _validate_bee_name(self, bee_name: str) -> None:
        """
        Bee名の妥当性を検証

        Args:
            bee_name: 検証するBee名

        Raises:
            BeeValidationError: Bee名が無効な場合
        """
        if not bee_name or not isinstance(bee_name, str):
            raise BeeValidationError(
                bee_name="",
                field="bee_name",
                value=bee_name,
                reason="Bee name must be a non-empty string",
            )

        if len(bee_name) > 50:
            raise BeeValidationError(
                bee_name=bee_name,
                field="bee_name",
                value=bee_name,
                reason="Bee name must be 50 characters or less",
            )

        # 有効なBee名のリスト（設定から取得）
        valid_bee_names = (
            list(self.config.pane_id_mapping.keys())
            if hasattr(self.config, "pane_id_mapping")
            else ["queen", "developer", "qa"]
        )
        if bee_name not in valid_bee_names:
            raise BeeValidationError(
                bee_name=bee_name,
                field="bee_name",
                value=bee_name,
                reason=f"Bee name must be one of: {', '.join(valid_bee_names)}",
            )

    def _init_database(self) -> None:
        """
        データベース接続を初期化

        Raises:
            DatabaseConnectionError: データベース接続に失敗した場合
        """
        if not self.hive_db_path.exists():
            error_msg = f"Database not found: {self.hive_db_path}"
            self.logger.error(error_msg)
            raise DatabaseConnectionError(str(self.hive_db_path))

        try:
            # 接続テスト
            with self._get_db_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            self._db_connection_healthy = True
            self.logger.debug(f"Database connection established: {self.hive_db_path}")
        except Exception as e:
            self._db_connection_healthy = False
            raise DatabaseConnectionError(str(self.hive_db_path), e)

    def _get_db_connection(self) -> sqlite3.Connection:
        """
        データベース接続を取得

        Returns:
            sqlite3.Connection: データベース接続

        Raises:
            DatabaseConnectionError: 接続に失敗した場合
        """
        try:
            conn = sqlite3.connect(str(self.hive_db_path), timeout=self.config.db_timeout)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            self._db_connection_healthy = False
            raise DatabaseConnectionError(str(self.hive_db_path), e)

    @wrap_database_error
    def _update_bee_state(self, status: str, task_id: int | None = None, workload: int = 0) -> None:
        """
        Bee状態をデータベースで更新

        Args:
            status: 新しい状態（idle, busy, error等）
            task_id: 現在のタスクID（オプション）
            workload: ワークロード割合（0-100）

        Raises:
            DatabaseOperationError: 状態更新に失敗した場合
            BeeValidationError: ステータス値が無効な場合
        """
        # 状態値の検証
        valid_statuses = ["idle", "busy", "error", "offline", "maintenance"]
        if status not in valid_statuses:
            raise BeeValidationError(
                bee_name=self.bee_name,
                field="status",
                value=status,
                reason=f"Status must be one of: {', '.join(valid_statuses)}",
            )

        if not (0 <= workload <= 100):
            raise BeeValidationError(
                bee_name=self.bee_name,
                field="workload",
                value=workload,
                reason="Workload must be between 0 and 100",
            )

        try:
            with self._get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO bee_states
                    (bee_name, status, current_task_id, last_heartbeat, workload_score, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
                """,
                    (self.bee_name, status, task_id, workload),
                )
                conn.commit()

            self.logger.log_event(
                "bee.state_updated",
                f"State updated: {status}",
                task_id=task_id,
                status=status,
                workload=workload,
            )

        except sqlite3.Error as e:
            raise DatabaseOperationError(
                operation="update_bee_state",
                query="INSERT OR REPLACE INTO bee_states",
                original_error=e,
            )

    def send_message(
        self,
        to_bee: str,
        message_type: str,
        subject: str,
        content: str,
        task_id: int | None = None,
        priority: str = "normal",
    ) -> int:
        """他のBeeにメッセージを送信（tmux sender CLI中心）"""
        # SQLiteにはログとして記録のみ
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO bee_messages
                (from_bee, to_bee, message_type, subject, content, task_id, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (self.bee_name, to_bee, message_type, subject, content, task_id, priority),
            )
            message_id = cursor.lastrowid
            conn.commit()

        # 実際の通信はtmux sender CLIで行う
        self._send_tmux_message(to_bee, message_type, subject, content, task_id)

        self.logger.info(f"Message sent to {to_bee}: {subject} (ID: {message_id})")
        return message_id

    def get_messages(self, processed: bool = False) -> list[dict[str, Any]]:
        """自分宛のメッセージを取得（ログから履歴確認用）"""
        # 注意: 実際の通信はtmux経由のため、これは履歴確認用
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM bee_messages
                WHERE to_bee = ? AND processed = ?
                ORDER BY priority DESC, created_at ASC
            """,
                (self.bee_name, processed),
            )
            messages = [dict(row) for row in cursor.fetchall()]

        return messages

    def mark_message_processed(self, message_id: int):
        """メッセージを処理済みとしてマーク"""
        with self._get_db_connection() as conn:
            conn.execute(
                """
                UPDATE bee_messages
                SET processed = TRUE, processed_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
            """,
                (message_id,),
            )
            conn.commit()

        self.logger.info(f"Message {message_id} marked as processed")

    def get_task_details(self, task_id: int) -> dict[str, Any] | None:
        """タスクの詳細情報を取得"""
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM tasks WHERE task_id = ?
            """,
                (task_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_task_status(self, task_id: int, status: str, notes: str | None = None):
        """タスク状態を更新"""
        with self._get_db_connection() as conn:
            # タスク状態更新
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """,
                (status, task_id),
            )

            # アクティビティログに記録
            conn.execute(
                """
                INSERT INTO task_activity
                (task_id, bee_name, activity_type, description)
                VALUES (?, ?, ?, ?)
            """,
                (
                    task_id,
                    self.bee_name,
                    "status_update",
                    f"Status changed to {status}" + (f": {notes}" if notes else ""),
                ),
            )

            conn.commit()

        self.logger.info(f"Task {task_id} status updated to: {status}")

    def log_activity(
        self, task_id: int, activity_type: str, description: str, metadata: dict | None = None
    ):
        """アクティビティをログに記録"""
        with self._get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO task_activity
                (task_id, bee_name, activity_type, description, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    task_id,
                    self.bee_name,
                    activity_type,
                    description,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            conn.commit()

        self.logger.info(f"Activity logged: {activity_type} - {description}")

    def _send_tmux_message(
        self,
        target_bee: str,
        message_type: str,
        subject: str,
        content: str,
        task_id: int | None = None,
    ):
        """CLI経由でtmux sender CLIメッセージを送信"""
        if target_bee not in self.pane_id_map:
            self.logger.warning(f"Unknown target bee: {target_bee}")
            return

        # bee名前から実際のペインIDを取得
        pane_id = self.pane_id_map[target_bee]

        # 構造化されたメッセージを作成
        message_lines = [
            f"## 📨 MESSAGE FROM {self.bee_name.upper()}",
            "",
            f"**Type:** {message_type}",
            f"**Subject:** {subject}",
            f"**Task ID:** {task_id if task_id else 'N/A'}",
            "",
            "**Content:**",
        ]

        # コンテンツを追加
        message_lines.extend(content.split("\n"))
        message_lines.extend(["", "---", ""])

        # 完全なメッセージを構築
        full_message = "\n".join(message_lines)

        try:
            # CLI経由でsender CLI実行（bee名前を使用）
            target_display_name = self.pane_map.get(target_bee, target_bee)
            cmd = [
                "python",
                "-m",
                "bees.cli",
                "send",
                self.session_name,
                pane_id,
                full_message,
                "--type",
                message_type,
                "--sender",
                self.bee_name,
                "--metadata",
                f'{{"to_bee": "{target_bee}", "to_pane": "{target_display_name}", "subject": "{subject}", "task_id": {task_id}}}',
            ]

            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)

            self.logger.debug(f"Send-keys CLI result: {result.stdout}")
            self.logger.debug(f"tmux message sent to {target_bee}: {subject}")

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to send tmux message via CLI: {e.stderr}")
        except subprocess.TimeoutExpired:
            self.logger.warning("Send-keys CLI command timed out")

    def _send_tmux_notification(self, target_bee: str, message: str):
        """CLI経由で簡単な通知を送信"""
        if target_bee not in self.pane_id_map:
            self.logger.warning(f"Unknown target bee: {target_bee}")
            return

        # bee名前から実際のペインIDを取得
        pane_id = self.pane_id_map[target_bee]

        # 簡単な通知メッセージ構築
        notification = f"\n# {message}\n"

        try:
            # CLI経由でsender CLI実行（bee名前を使用）
            target_display_name = self.pane_map.get(target_bee, target_bee)
            cmd = [
                "python",
                "-m",
                "bees.cli",
                "send",
                self.session_name,
                pane_id,
                notification,
                "--type",
                "notification",
                "--sender",
                self.bee_name,
                "--metadata",
                f'{{"to_bee": "{target_bee}", "to_pane": "{target_display_name}"}}',
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=15)

            self.logger.debug(f"tmux notification sent to {target_bee}")

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to send tmux notification via CLI: {e.stderr}")
        except subprocess.TimeoutExpired:
            self.logger.warning("Notification CLI command timed out")

    def heartbeat(self):
        """生存確認のハートビート"""
        with self._get_db_connection() as conn:
            conn.execute(
                """
                UPDATE bee_states
                SET last_heartbeat = CURRENT_TIMESTAMP
                WHERE bee_name = ?
            """,
                (self.bee_name,),
            )
            conn.commit()

    def get_workload_status(self) -> dict[str, Any]:
        """現在のワークロード状況を取得"""
        with self._get_db_connection() as conn:
            # 自分の状態
            cursor = conn.execute(
                """
                SELECT * FROM bee_states WHERE bee_name = ?
            """,
                (self.bee_name,),
            )
            bee_state = dict(cursor.fetchone() or {})

            # アクティブタスク数
            cursor = conn.execute(
                """
                SELECT COUNT(*) as count FROM tasks
                WHERE assigned_to = ? AND status IN ('pending', 'in_progress')
            """,
                (self.bee_name,),
            )
            active_tasks = cursor.fetchone()[0]

            # 未処理メッセージ数
            cursor = conn.execute(
                """
                SELECT COUNT(*) as count FROM bee_messages
                WHERE to_bee = ? AND processed = FALSE
            """,
                (self.bee_name,),
            )
            unread_messages = cursor.fetchone()[0]

            return {
                "bee_state": bee_state,
                "active_tasks": active_tasks,
                "unread_messages": unread_messages,
                "timestamp": datetime.now().isoformat(),
            }

    def run_communication_loop(self, interval: float = 5.0):
        """通信ループを実行（継続的にハートビート送信）"""
        # 注意: 実際の通信はtmux経由で行われるため、このループは主にハートビート用
        self.logger.info(f"Starting heartbeat loop (interval: {interval}s)")

        while True:
            try:
                # ハートビート
                self.heartbeat()

                # 状態確認（必要に応じてサブクラスで拡張）
                self._periodic_status_check()

                time.sleep(interval)

            except KeyboardInterrupt:
                self.logger.info("Communication loop stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in communication loop: {e}")
                time.sleep(interval)

    def _periodic_status_check(self):
        """定期的な状態チェック（サブクラスでオーバーライド可能）"""
        # 基底クラスでは基本的なチェックのみ
        pass

    def _process_message(self, message: dict[str, Any]):
        """メッセージを処理（サブクラスでオーバーライド）"""
        # 注意: 実際の通信はtmux経由のため、これはログ処理用
        # Claudeが直接受け取ったメッセージに対して手動で呼び出される想定
        self.logger.info(f"Processing message: {message['subject']} from {message['from_bee']}")

        # 基本的な応答例
        if message["message_type"] == "question":
            response = f"Message received: {message['subject']}"
            self.send_message(
                message["from_bee"],
                "response",
                f"Re: {message['subject']}",
                response,
                message.get("task_id"),
            )

        # メッセージを処理済みにマーク
        self.mark_message_processed(message["message_id"])

    def process_tmux_input(self, user_input: str):
        """tmux経由で受信したユーザー入力を処理（Claudeが実際に使用）"""
        # tmux経由でClaudeが受け取った入力を解析
        if user_input.startswith("## 📨 MESSAGE FROM"):
            # 構造化メッセージの処理
            self._parse_structured_message(user_input)
        else:
            # 通常の作業指示として処理
            self._handle_work_instruction(user_input)

    def _parse_structured_message(self, message_text: str) -> dict[str, Any]:
        """
        構造化メッセージを解析（サブクラスでオーバーライド）

        Args:
            message_text: 解析する構造化メッセージテキスト

        Returns:
            Dict[str, Any]: 解析されたメッセージ情報

        Raises:
            TaskExecutionError: メッセージ解析に失敗した場合
        """
        try:
            self.logger.log_event("message.parsing_started", "Parsing structured message via tmux")

            # 基本実装では解析のみ
            lines = message_text.split("\n")
            parsed_data = {
                "message_type": None,
                "subject": None,
                "task_id": None,
                "from_bee": None,
                "timestamp": None,
                "content": [],
            }

            content_started = False

            for line in lines:
                if line.startswith("## 📨 MESSAGE FROM"):
                    # From bee を抽出
                    parsed_data["from_bee"] = line.replace("## 📨 MESSAGE FROM", "").strip()
                elif line.startswith("**Type:**"):
                    parsed_data["message_type"] = line.replace("**Type:**", "").strip()
                elif line.startswith("**Subject:**"):
                    parsed_data["subject"] = line.replace("**Subject:**", "").strip()
                elif line.startswith("**Task ID:**"):
                    task_id_str = line.replace("**Task ID:**", "").strip()
                    if task_id_str != "N/A":
                        try:
                            parsed_data["task_id"] = int(task_id_str)
                        except ValueError:
                            pass
                elif line.startswith("**Timestamp:**"):
                    parsed_data["timestamp"] = line.replace("**Timestamp:**", "").strip()
                elif line.startswith("**Content:**"):
                    content_started = True
                elif content_started and line.strip() and not line.startswith("---"):
                    parsed_data["content"].append(line)

            # コンテンツを文字列に結合
            parsed_data["content"] = "\n".join(parsed_data["content"])

            self.logger.log_event(
                "message.parsing_completed",
                f"Parsed message - Type: {parsed_data['message_type']}, Subject: {parsed_data['subject']}",
                **{k: v for k, v in parsed_data.items() if k not in ["content"]},
            )

            return parsed_data

        except Exception as e:
            self.logger.error(f"Failed to parse structured message: {e}", error=e)
            raise TaskExecutionError(
                task_id=0, bee_name=self.bee_name, stage="message_parsing", original_error=e
            )

    def _handle_work_instruction(self, instruction: str) -> None:
        """
        通常の作業指示を処理（サブクラスでオーバーライド）

        Args:
            instruction: 作業指示テキスト

        Note:
            サブクラスで実際の処理ロジックを実装する
        """
        instruction_preview = instruction[:50] + ("..." if len(instruction) > 50 else "")

        self.logger.log_event(
            "instruction.received",
            f"Received work instruction: {instruction_preview}",
            instruction_length=len(instruction),
            instruction_preview=instruction_preview,
        )

        # 基底クラスでは基本的な応答のみ
        response_msg = f"✅ {self.bee_name} received instruction: {instruction_preview}"
        print(response_msg)

        self.logger.info(response_msg)

    def get_health_status(self) -> dict[str, Any]:
        """
        現在の健全性状態を取得

        Returns:
            Dict[str, Any]: 健全性情報
        """
        return {
            "bee_name": self.bee_name,
            "database_healthy": self._db_connection_healthy,
            "tmux_session_healthy": self._tmux_session_healthy,
            "config_loaded": self.config is not None,
            "timestamp": datetime.now().isoformat(),
        }

    def __enter__(self):
        """コンテキストマネージャー対応"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了処理"""
        try:
            # 最終状態更新
            if exc_type is None:
                self._update_bee_state("idle")
            else:
                self._update_bee_state("error")
        except Exception as e:
            self.logger.warning(f"Failed to update final state: {e}")

    def __str__(self) -> str:
        """文字列表現"""
        return f"BaseBee(name='{self.bee_name}', db_healthy={self._db_connection_healthy}, tmux_healthy={self._tmux_session_healthy})"

    def __repr__(self) -> str:
        """開発者向け文字列表現"""
        return f"BaseBee(bee_name='{self.bee_name}', hive_db_path='{self.hive_db_path}', session_name='{self.session_name}')"
