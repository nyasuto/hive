#!/usr/bin/env python3
"""
Conversation Logger - beekeeperとbee間会話のDB保存機能
beekeeperからの指示やbee同士の会話を全てdbに保存し、必要に応じてタスクを自動発行
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import BeehiveConfig, get_config
from .exceptions import DatabaseConnectionError, DatabaseOperationError
from .logging_config import get_logger


class ConversationLogger:
    """beekeeperとbee間の会話を記録・管理するクラス"""

    def __init__(self, config: BeehiveConfig | None = None):
        self.config = config or get_config()
        self.hive_db_path = Path(self.config.hive_db_path)
        self.logger = get_logger("conversation_logger", self.config)

        # データベース接続確認
        self._init_database()

    def _init_database(self) -> None:
        """データベース接続を初期化"""
        if not self.hive_db_path.exists():
            raise DatabaseConnectionError(str(self.hive_db_path))

        try:
            with self._get_db_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            self.logger.debug("Conversation logger database connection established")
        except Exception as e:
            raise DatabaseConnectionError(str(self.hive_db_path), e)

    def _get_db_connection(self) -> sqlite3.Connection:
        """データベース接続を取得"""
        try:
            conn = sqlite3.connect(str(self.hive_db_path), timeout=self.config.db_timeout)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            raise DatabaseConnectionError(str(self.hive_db_path), e)

    def log_beekeeper_instruction(
        self,
        instruction: str,
        target_bee: str = "all",
        priority: str = "normal",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """beekeeperからの指示をデータベースに記録

        Args:
            instruction: 指示内容
            target_bee: 対象のbee名（'all'で全bee）
            priority: 優先度 ('low', 'normal', 'high', 'urgent')
            metadata: 追加メタデータ

        Returns:
            int: 作成されたメッセージID
        """
        try:
            conversation_id = str(uuid.uuid4())

            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO bee_messages
                    (from_bee, to_bee, message_type, subject, content, priority,
                     sender_cli_used, conversation_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "beekeeper",
                        target_bee,
                        "instruction",
                        "Beekeeper Instruction",
                        instruction,
                        priority,
                        True,  # beekeeperからの指示は常にsender CLI使用扱い
                        conversation_id,
                        json.dumps(metadata) if metadata else None,
                    ),
                )
                message_id = cursor.lastrowid
                conn.commit()

            self.logger.info(
                f"Beekeeper instruction logged (ID: {message_id}, target: {target_bee}, priority: {priority})"
            )

            # 必要に応じて自動タスク生成を検討
            self._consider_auto_task_creation(instruction, target_bee, conversation_id)

            return message_id

        except sqlite3.Error as e:
            raise DatabaseOperationError(
                operation="log_beekeeper_instruction",
                query="INSERT INTO bee_messages",
                original_error=e,
            )

    def log_bee_conversation(
        self,
        from_bee: str,
        to_bee: str,
        content: str,
        message_type: str = "conversation",
        task_id: str | None = None,
        conversation_id: str | None = None,
        sender_cli_used: bool = True,
    ) -> int:
        """bee間の会話をデータベースに記録

        Args:
            from_bee: 送信元bee名
            to_bee: 送信先bee名
            content: 会話内容
            message_type: メッセージタイプ
            task_id: 関連タスクID（オプション）
            conversation_id: 会話ID（オプション、新規作成される）
            sender_cli_used: sender CLIが使用されたか

        Returns:
            int: 作成されたメッセージID
        """
        try:
            if not conversation_id:
                conversation_id = str(uuid.uuid4())

            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO bee_messages
                    (from_bee, to_bee, message_type, subject, content, task_id,
                     sender_cli_used, conversation_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        from_bee,
                        to_bee,
                        message_type,
                        f"Conversation: {from_bee} → {to_bee}",
                        content,
                        task_id,
                        sender_cli_used,
                        conversation_id,
                    ),
                )
                message_id = cursor.lastrowid
                conn.commit()

            self.logger.info(
                f"Bee conversation logged (ID: {message_id}, {from_bee} -> {to_bee}, CLI: {sender_cli_used})"
            )

            # sender CLI使用チェック
            if not sender_cli_used:
                self.logger.warning(
                    f"Non-CLI communication detected: {from_bee} → {to_bee} (msg_id: {message_id})"
                )

            return message_id

        except sqlite3.Error as e:
            raise DatabaseOperationError(
                operation="log_bee_conversation", query="INSERT INTO bee_messages", original_error=e
            )

    def get_conversation_history(
        self,
        conversation_id: str | None = None,
        bee_name: str | None = None,
        limit: int = 100,
        include_beekeeper: bool = True,
    ) -> list[dict[str, Any]]:
        """会話履歴を取得

        Args:
            conversation_id: 特定の会話ID
            bee_name: 特定のbee名（from_beeまたはto_bee）
            limit: 取得件数制限
            include_beekeeper: beekeeperとの会話を含めるか

        Returns:
            List[Dict[str, Any]]: 会話履歴リスト
        """
        try:
            query_parts = ["SELECT * FROM bee_messages WHERE 1=1"]
            params = []

            if conversation_id:
                query_parts.append("AND conversation_id = ?")
                params.append(conversation_id)

            if bee_name:
                query_parts.append("AND (from_bee = ? OR to_bee = ?)")
                params.extend([bee_name, bee_name])

            if not include_beekeeper:
                query_parts.append("AND from_bee != 'beekeeper' AND to_bee != 'beekeeper'")

            query_parts.append("ORDER BY created_at DESC LIMIT ?")
            params.append(limit)

            query = " ".join(query_parts)

            with self._get_db_connection() as conn:
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            self.logger.error(f"Failed to get conversation history: {e}")
            return []

    def _consider_auto_task_creation(
        self, instruction: str, target_bee: str, conversation_id: str
    ) -> str | None:
        """指示内容に基づいて自動タスク生成を検討

        Args:
            instruction: 指示内容
            target_bee: 対象bee
            conversation_id: 会話ID

        Returns:
            Optional[str]: 生成されたタスクID（生成されなかった場合はNone）
        """
        # タスク生成が必要そうなキーワードをチェック
        task_keywords = [
            "実装",
            "開発",
            "作成",
            "修正",
            "テスト",
            "デバッグ",
            "implement",
            "develop",
            "create",
            "fix",
            "test",
            "debug",
            "作って",
            "直して",
            "書いて",
            "やって",
        ]

        should_create_task = any(keyword in instruction.lower() for keyword in task_keywords)

        if should_create_task:
            try:
                # タスクタイトルを抽出（簡易実装）
                title = self._extract_task_title(instruction)

                # UUIDベースのタスクID生成
                task_id = str(uuid.uuid4())

                with self._get_db_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO tasks
                        (task_id, title, description, priority, assigned_to, created_by, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            task_id,
                            title,
                            instruction,
                            "medium",
                            target_bee if target_bee != "all" else None,
                            "beekeeper",
                            json.dumps(
                                {
                                    "auto_generated": True,
                                    "conversation_id": conversation_id,
                                    "source": "beekeeper_instruction",
                                }
                            ),
                        ),
                    )
                    conn.commit()

                self.logger.info(
                    f"Auto-generated task from beekeeper instruction (ID: {task_id}, title: {title})"
                )

                return task_id

            except Exception as e:
                self.logger.warning(f"Failed to auto-generate task: {e}")

        return None

    def _extract_task_title(self, instruction: str) -> str:
        """指示からタスクタイトルを抽出（簡易実装）

        Args:
            instruction: 指示内容

        Returns:
            str: 抽出されたタイトル
        """
        # 簡易実装：最初の50文字を使用
        title = instruction.strip()
        if len(title) > 50:
            title = title[:47] + "..."

        return title

    def enforce_sender_cli_usage(self) -> list[dict[str, Any]]:
        """sender CLI未使用の通信を検出

        Returns:
            List[Dict[str, Any]]: 違反メッセージのリスト
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM bee_messages
                    WHERE sender_cli_used = FALSE
                    AND from_bee != 'beekeeper'
                    AND to_bee != 'beekeeper'
                    ORDER BY created_at DESC
                    """
                )
                violations = [dict(row) for row in cursor.fetchall()]

            if violations:
                self.logger.warning(f"Detected {len(violations)} sender CLI violations")

            return violations

        except sqlite3.Error as e:
            self.logger.error(f"Failed to check sender CLI usage: {e}")
            return []

    def get_conversation_stats(self) -> dict[str, Any]:
        """会話統計を取得

        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            with self._get_db_connection() as conn:
                # 総メッセージ数
                total_messages = conn.execute("SELECT COUNT(*) FROM bee_messages").fetchone()[0]

                # beekeeperからの指示数
                beekeeper_instructions = conn.execute(
                    "SELECT COUNT(*) FROM bee_messages WHERE from_bee = 'beekeeper'"
                ).fetchone()[0]

                # bee間会話数
                bee_conversations = conn.execute(
                    """
                    SELECT COUNT(*) FROM bee_messages
                    WHERE from_bee != 'beekeeper' AND to_bee != 'beekeeper'
                    """
                ).fetchone()[0]

                # sender CLI使用率
                cli_used = conn.execute(
                    "SELECT COUNT(*) FROM bee_messages WHERE sender_cli_used = TRUE"
                ).fetchone()[0]

                cli_usage_rate = (cli_used / total_messages * 100) if total_messages > 0 else 0

                # アクティブな会話数
                active_conversations = conn.execute(
                    "SELECT COUNT(DISTINCT conversation_id) FROM bee_messages WHERE conversation_id IS NOT NULL"
                ).fetchone()[0]

                return {
                    "total_messages": total_messages,
                    "beekeeper_instructions": beekeeper_instructions,
                    "bee_conversations": bee_conversations,
                    "sender_cli_usage_rate": round(cli_usage_rate, 2),
                    "active_conversations": active_conversations,
                    "timestamp": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            self.logger.error(f"Failed to get conversation stats: {e}")
            return {}
