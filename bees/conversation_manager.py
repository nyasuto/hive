#!/usr/bin/env python3
"""
Conversation Manager - 会話管理とsender CLI強制機能
beekeeperとbeeの会話を管理し、すべての通信がsender CLI経由であることを保証
"""

import json
import subprocess
import time
from datetime import datetime
from typing import Any

from .config import BeehiveConfig, get_config
from .conversation_logger import ConversationLogger
from .logging_config import get_logger


class ConversationManager:
    """会話管理とsender CLI強制を行うマネージャークラス"""

    def __init__(self, config: BeehiveConfig | None = None):
        self.config = config or get_config()
        self.logger = get_logger("conversation_manager", self.config)
        self.conversation_logger = ConversationLogger(config)

        # 各beeの通信状態を追跡
        self._bee_communication_states: dict[str, dict[str, Any]] = {}

        self.logger.info("ConversationManager initialized")

    def intercept_beekeeper_input(self, input_text: str, target_bee: str = "all") -> bool:
        """beekeeperからの入力を傍受してログに記録

        Args:
            input_text: beekeeperからの入力テキスト
            target_bee: 対象bee（デフォルトは"all"）

        Returns:
            bool: 処理成功フラグ
        """
        try:
            # 入力の分類
            instruction_type = self._classify_beekeeper_input(input_text)
            priority = self._determine_priority(input_text, instruction_type)

            # データベースに記録
            message_id = self.conversation_logger.log_beekeeper_instruction(
                instruction=input_text,
                target_bee=target_bee,
                priority=priority,
                metadata={
                    "instruction_type": instruction_type,
                    "input_method": "console",
                    "timestamp": datetime.now().isoformat(),
                },
            )

            self.logger.info(
                f"Beekeeper input intercepted and logged (ID: {message_id}, type: {instruction_type}, target: {target_bee})"
            )

            # sender CLI経由でbeeに送信
            if target_bee != "all":
                self._send_via_sender_cli(
                    from_bee="beekeeper",
                    to_bee=target_bee,
                    message_type="instruction",
                    content=input_text,
                    subject="Beekeeper Instruction",
                )
            else:
                # 全beeに送信
                valid_bees = list(self.config.pane_id_mapping.keys())
                for bee_name in valid_bees:
                    self._send_via_sender_cli(
                        from_bee="beekeeper",
                        to_bee=bee_name,
                        message_type="instruction",
                        content=input_text,
                        subject="Beekeeper Instruction",
                    )

            return True

        except Exception as e:
            self.logger.error(f"Failed to intercept beekeeper input: {e}")
            return False

    def monitor_bee_communications(self, interval: float = 2.0) -> None:
        """bee間通信を監視してsender CLI使用を強制

        Args:
            interval: 監視間隔（秒）
        """
        self.logger.info(f"Starting bee communication monitoring (interval: {interval}s)")

        while True:
            try:
                # sender CLI未使用の通信を検出
                violations = self.conversation_logger.enforce_sender_cli_usage()

                if violations:
                    self._handle_sender_cli_violations(violations)

                # 各beeの通信状態をチェック
                self._check_bee_communication_health()

                time.sleep(interval)

            except KeyboardInterrupt:
                self.logger.info("Communication monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in communication monitoring: {e}")
                time.sleep(interval)

    def log_bee_message(
        self,
        from_bee: str,
        to_bee: str,
        content: str,
        message_type: str = "info",
        task_id: str | None = None,
        sender_cli_used: bool = True,
    ) -> int:
        """bee間メッセージをログに記録

        Args:
            from_bee: 送信元bee
            to_bee: 送信先bee
            content: メッセージ内容
            message_type: メッセージタイプ
            task_id: 関連タスクID
            sender_cli_used: sender CLIが使用されたか

        Returns:
            int: メッセージID
        """
        return self.conversation_logger.log_bee_conversation(
            from_bee=from_bee,
            to_bee=to_bee,
            content=content,
            message_type=message_type,
            task_id=task_id,
            sender_cli_used=sender_cli_used,
        )

    def _classify_beekeeper_input(self, input_text: str) -> str:
        """beekeeper入力の分類

        Args:
            input_text: 入力テキスト

        Returns:
            str: 分類結果
        """
        text_lower = input_text.lower()

        # タスク関連キーワード
        if any(
            keyword in text_lower
            for keyword in ["実装", "開発", "作成", "implement", "develop", "create"]
        ):
            return "task_assignment"
        elif any(keyword in text_lower for keyword in ["修正", "デバッグ", "fix", "debug", "bug"]):
            return "bug_fix"
        elif any(keyword in text_lower for keyword in ["テスト", "test", "qa", "品質"]):
            return "testing"
        elif any(keyword in text_lower for keyword in ["状況", "進捗", "status", "progress"]):
            return "status_inquiry"
        elif any(keyword in text_lower for keyword in ["停止", "中止", "stop", "cancel"]):
            return "control_command"
        else:
            return "general_instruction"

    def _determine_priority(self, input_text: str, instruction_type: str) -> str:
        """優先度を決定

        Args:
            input_text: 入力テキスト
            instruction_type: 指示タイプ

        Returns:
            str: 優先度
        """
        text_lower = input_text.lower()

        # 緊急キーワード
        if any(
            keyword in text_lower for keyword in ["緊急", "急", "urgent", "critical", "immediately"]
        ):
            return "urgent"
        elif any(keyword in text_lower for keyword in ["重要", "高", "high", "important"]):
            return "high"
        elif instruction_type in ["bug_fix", "control_command"]:
            return "high"
        elif instruction_type in ["task_assignment", "testing"]:
            return "normal"
        else:
            return "low"

    def _send_via_sender_cli(
        self,
        from_bee: str,
        to_bee: str,
        message_type: str,
        content: str,
        subject: str,
        task_id: str | None = None,
    ) -> bool:
        """sender CLI経由でメッセージ送信

        Args:
            from_bee: 送信元
            to_bee: 送信先
            message_type: メッセージタイプ
            content: 内容
            subject: 件名
            task_id: タスクID

        Returns:
            bool: 送信成功フラグ
        """
        try:
            if to_bee not in self.config.pane_id_mapping:
                self.logger.warning(f"Unknown target bee: {to_bee}")
                return False

            pane_id = self.config.pane_id_mapping[to_bee]

            # 構造化メッセージ作成
            message_lines = [
                f"## 📨 MESSAGE FROM {from_bee.upper()}",
                "",
                f"**Type:** {message_type}",
                f"**Subject:** {subject}",
                f"**Task ID:** {task_id if task_id else 'N/A'}",
                f"**Timestamp:** {datetime.now().isoformat()}",
                "",
                "**Content:**",
            ]

            message_lines.extend(content.split("\n"))
            message_lines.extend(["", "---", ""])

            full_message = "\n".join(message_lines)

            # sender CLI実行
            cmd = [
                "python",
                "-m",
                "bees.cli",
                "send",
                self.config.session_name,
                pane_id,
                full_message,
                "--type",
                message_type,
                "--sender",
                from_bee,
                "--metadata",
                json.dumps(
                    {
                        "to_bee": to_bee,
                        "subject": subject,
                        "task_id": task_id,
                        "sender_cli_enforced": True,
                    }
                ),
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)

            self.logger.debug(f"Sender CLI message sent: {from_bee} → {to_bee}")

            # 送信成功をログに記録
            self.log_bee_message(
                from_bee=from_bee,
                to_bee=to_bee,
                content=content,
                message_type=message_type,
                task_id=task_id,
                sender_cli_used=True,
            )

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Sender CLI command failed: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            self.logger.error("Sender CLI command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Failed to send via sender CLI: {e}")
            return False

    def _handle_sender_cli_violations(self, violations: list[dict[str, Any]]) -> None:
        """sender CLI違反を処理

        Args:
            violations: 違反メッセージリスト
        """
        for violation in violations:
            from_bee = violation["from_bee"]
            to_bee = violation["to_bee"]
            message_id = violation["message_id"]

            self.logger.warning(
                f"Sender CLI violation detected: {from_bee} → {to_bee} (msg_id: {message_id})"
            )

            # 違反beeに警告を送信
            warning_message = f"""
⚠️ COMMUNICATION PROTOCOL VIOLATION ⚠️

Your message (ID: {message_id}) to {to_bee} was sent without using the sender CLI.

All bee-to-bee communication MUST go through the sender CLI system.
Please use the proper communication protocols in future messages.

This violation has been logged for review.
"""

            self._send_via_sender_cli(
                from_bee="system",
                to_bee=from_bee,
                message_type="alert",
                content=warning_message,
                subject="Communication Protocol Violation",
            )

    def _check_bee_communication_health(self) -> None:
        """bee通信の健全性をチェック"""
        try:
            stats = self.conversation_logger.get_conversation_stats()
            cli_usage_rate = stats.get("sender_cli_usage_rate", 0)

            if cli_usage_rate < 95.0:  # 95%未満の場合は警告
                self.logger.warning(f"Low sender CLI usage rate: {cli_usage_rate}%")

                # Queen Beeに通知
                self._send_via_sender_cli(
                    from_bee="system",
                    to_bee="queen",
                    message_type="alert",
                    content=f"System Alert: Sender CLI usage rate is {cli_usage_rate}%. Expected >95%.",
                    subject="Communication Protocol Alert",
                )

        except Exception as e:
            self.logger.error(f"Failed to check communication health: {e}")

    def get_conversation_summary(
        self, bee_name: str | None = None, hours: int = 24
    ) -> dict[str, Any]:
        """会話サマリーを取得

        Args:
            bee_name: 特定のbee名
            hours: 過去何時間分か

        Returns:
            Dict[str, Any]: サマリー情報
        """
        try:
            # 基本統計
            stats = self.conversation_logger.get_conversation_stats()

            # 最近の会話履歴
            recent_conversations = self.conversation_logger.get_conversation_history(
                bee_name=bee_name, limit=50, include_beekeeper=True
            )

            # bee別メッセージ数集計
            bee_message_counts = {}
            for conv in recent_conversations:
                from_bee = conv["from_bee"]
                to_bee = conv["to_bee"]

                if from_bee not in bee_message_counts:
                    bee_message_counts[from_bee] = {"sent": 0, "received": 0}
                if to_bee not in bee_message_counts:
                    bee_message_counts[to_bee] = {"sent": 0, "received": 0}

                bee_message_counts[from_bee]["sent"] += 1
                bee_message_counts[to_bee]["received"] += 1

            return {
                "stats": stats,
                "bee_message_counts": bee_message_counts,
                "recent_conversations_count": len(recent_conversations),
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get conversation summary: {e}")
            return {}

    def shutdown(self) -> None:
        """マネージャーをシャットダウン"""
        self.logger.info("ConversationManager shutting down")

        # 最終統計を出力
        try:
            stats = self.conversation_logger.get_conversation_stats()
            self.logger.info(f"Final conversation stats: {stats}")
        except Exception as e:
            self.logger.warning(f"Failed to get final stats: {e}")
