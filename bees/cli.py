#!/usr/bin/env python3
"""
Beehive Sender CLI Tool
Issue #25: sender CLI処理のCLI化とSQLite透過保存

tmux sender CLIの処理を集約し、SQLiteでの透過的ログ保存を提供
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import get_config
from .exceptions import DatabaseOperationError, TmuxCommandError, ValidationError
from .logging_config import get_logger


class SenderCLI:
    """sender CLI処理のCLI化クラス"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.db_path = Path(self.config.db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """必要なテーブルを作成"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sender_cli_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        session_name TEXT NOT NULL,
                        target_pane TEXT NOT NULL,
                        message TEXT NOT NULL,
                        message_type TEXT,
                        sender TEXT,
                        metadata TEXT,
                        success INTEGER NOT NULL DEFAULT 1,
                        error_message TEXT,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseOperationError("create_tables", "CREATE TABLE", e)

    def send_message(
        self,
        session_name: str,
        target_pane: str,
        message: str,
        message_type: str | None = None,
        sender: str | None = None,
        metadata: dict[str, Any] | None = None,
        dry_run: bool = False,
        chunk_size: int = 4000,  # 大容量テキスト分割サイズ
        include_sender_header: bool = True,  # sender情報をメッセージ先頭に含める
    ) -> bool:
        """
        tmux sender CLIコマンドを実行し、SQLiteにログを保存

        Args:
            session_name: tmuxセッション名
            target_pane: 対象ペイン（例: "0.0", "0.1"）
            message: 送信するメッセージ
            message_type: メッセージタイプ（role_injection, task_assignment等）
            sender: 送信者名
            metadata: 追加メタデータ
            dry_run: ドライランモード
            chunk_size: 大容量テキスト分割サイズ（文字数）
            include_sender_header: sender情報をメッセージ先頭に含める

        Returns:
            bool: 成功時True
        """
        timestamp = datetime.now().isoformat()
        success = True
        error_message = None

        # 入力検証
        if not session_name or not target_pane or not message:
            raise ValidationError(
                "session_name, target_pane, message",
                f"{session_name}, {target_pane}, {message}",
                "All parameters are required",
            )

        # Sender情報をメッセージに含める処理
        formatted_message = self._format_message_with_sender(
            message, sender, message_type, include_sender_header
        )

        try:
            if not dry_run:
                # tmux sender CLIコマンドを実行
                # ペインIDが%で始まる場合は特別な形式を使用
                if target_pane.startswith("%"):
                    target = target_pane  # %0形式の場合はそのまま使用
                else:
                    target = f"{session_name}:{target_pane}"  # 従来の形式

                # メッセージサイズチェックと分割送信
                if len(formatted_message) > chunk_size:
                    self.logger.info(
                        f"Large message detected ({len(formatted_message)} chars), splitting into chunks of {chunk_size}"
                    )
                    success = self._send_large_message(
                        session_name, target, formatted_message, chunk_size
                    )
                    if not success:
                        error_message = (
                            f"Failed to send large message ({len(formatted_message)} chars)"
                        )
                else:
                    # 通常サイズの一括送信
                    success = self._send_single_message(session_name, target, formatted_message)
                    if not success:
                        error_message = f"Failed to send message ({len(formatted_message)} chars)"

                # 必ず最後に1秒待ってEnterを送信
                # tmuxで大量メッセージ送信後の確定処理として必要
                time.sleep(1)
                cmd = ["tmux", "send-keys", "-t", target, "Enter"]
                subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                self.logger.info(f"Sender CLI executed: {target} <- {formatted_message[:50]}...")
            else:
                # ドライランでも同様の待機時間をシミュレート
                time.sleep(1)
                self.logger.info(
                    f"[DRY-RUN] Sender CLI: {session_name}:{target_pane} <- {formatted_message[:50]}... + Enter (1s delay)"
                )

        except subprocess.TimeoutExpired:
            success = False
            error_message = "tmux sender CLI command timed out"
        except subprocess.CalledProcessError as e:
            success = False
            error_message = f"tmux sender CLI failed: {e.stderr}"
        except Exception as e:
            success = False
            error_message = f"Unexpected error: {str(e)}"

        # SQLiteにログ保存
        try:
            self._save_to_database(
                timestamp=timestamp,
                session_name=session_name,
                target_pane=target_pane,
                message=message,
                message_type=message_type,
                sender=sender,
                metadata=metadata,
                success=success,
                error_message=error_message,
            )
        except Exception as e:
            self.logger.error(f"Failed to save sender CLI log to database: {e}")
            # ログ保存失敗してもsender CLI処理は継続

        if not success and error_message:
            raise TmuxCommandError(
                f"sender CLI to {session_name}:{target_pane}", Exception(error_message)
            )

        return success

    def _format_message_with_sender(
        self,
        message: str,
        sender: str | None,
        message_type: str | None,
        include_sender_header: bool,
    ) -> str:
        """
        メッセージにsender情報を含める

        Args:
            message: 元のメッセージ
            sender: 送信者名
            message_type: メッセージタイプ
            include_sender_header: sender情報を含めるかどうか

        Returns:
            str: sender情報を含むフォーマット済みメッセージ
        """
        if not include_sender_header or not sender:
            return message

        # Bee名に対応する絵文字マッピング
        sender_emojis = {
            "queen": "🐝",
            "developer": "💻",
            "qa": "🔍",
            "analyst": "📊",
            "system": "⚙️",
            "beekeeper": "🧑‍🌾",
        }

        # message_typeに対応する絵文字マッピング
        type_emojis = {
            "task_assignment": "🎯",
            "analysis_request": "📊",
            "test_request": "🧪",
            "progress_report": "📈",
            "quality_report": "🔍",
            "role_injection": "🔔",
            "status_check": "❓",
            "notification": "📢",
            "question": "❓",
            "task_completed": "✅",
        }

        # Sender情報のヘッダーを作成
        sender_emoji = sender_emojis.get(sender.lower(), "👤")
        type_emoji = type_emojis.get(message_type, "💬") if message_type else "💬"

        # 送信者表示名を整形
        sender_display = sender.replace("_", " ").title()

        # ヘッダー行を作成
        header = f"📨 **From: {sender_emoji} {sender_display}** {type_emoji}"
        if message_type:
            type_display = message_type.replace("_", " ").title()
            header += f" [{type_display}]"

        # 区切り線
        separator = "─" * 50

        # メッセージ全体を組み立て
        formatted_message = f"{header}\n{separator}\n\n{message}"

        return formatted_message

    def _save_to_database(
        self,
        timestamp: str,
        session_name: str,
        target_pane: str,
        message: str,
        message_type: str | None,
        sender: str | None,
        metadata: dict[str, Any] | None,
        success: bool,
        error_message: str | None,
    ) -> None:
        """ログをデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO sender_cli_log (
                        timestamp, session_name, target_pane, message,
                        message_type, sender, metadata, success, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        timestamp,
                        session_name,
                        target_pane,
                        message,
                        message_type,
                        sender,
                        json.dumps(metadata) if metadata else None,
                        1 if success else 0,
                        error_message,
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseOperationError("save_sender_cli_log", "INSERT", e)

    def get_recent_logs(self, limit: int = 50) -> list:
        """最近のsender CLIログを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM sender_cli_log
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseOperationError("get_recent_logs", "SELECT", e)

    def get_logs_by_session(self, session_name: str, limit: int = 50) -> list:
        """セッション別のログを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM sender_cli_log
                    WHERE session_name = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (session_name, limit),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseOperationError("get_logs_by_session", "SELECT", e)

    def _send_single_message(self, session_name: str, target: str, message: str) -> bool:
        """単一メッセージの送信（一括送信）"""
        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp_file:
                temp_file.write(message)
                temp_file_path = temp_file.name

            try:
                # tmux load-bufferでテキストを読み込み
                load_cmd = ["tmux", "load-buffer", "-t", session_name, temp_file_path]
                result = subprocess.run(load_cmd, capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    self.logger.error(
                        f"Load-buffer failed (file size: {len(message)} chars): {result.stderr}"
                    )
                    return False

                self.logger.debug(f"Load-buffer successful for {len(message)} characters")

                # tmux paste-bufferでペインに貼り付け
                paste_cmd = ["tmux", "paste-buffer", "-t", target]
                result = subprocess.run(paste_cmd, capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    self.logger.error(f"Paste-buffer failed (target: {target}): {result.stderr}")
                    return False

                self.logger.debug(f"Paste-buffer successful to target: {target}")
                return True

            finally:
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass

        except Exception as e:
            self.logger.error(f"Error in single message send: {e}")
            return False

    def _send_large_message(
        self, session_name: str, target: str, message: str, chunk_size: int
    ) -> bool:
        """大容量メッセージの分割送信"""
        try:
            chunks = []
            for i in range(0, len(message), chunk_size):
                chunk = message[i : i + chunk_size]
                chunks.append(chunk)

            self.logger.info(f"Splitting message into {len(chunks)} chunks")

            for i, chunk in enumerate(chunks):
                self.logger.debug(f"Sending chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)")

                if not self._send_single_message(session_name, target, chunk):
                    self.logger.error(f"Failed to send chunk {i + 1}/{len(chunks)}")
                    return False

                # 小さな待機時間を挟む
                if i < len(chunks) - 1:  # 最後のチャンク以外
                    time.sleep(1)

            self.logger.info(f"Successfully sent all {len(chunks)} chunks")
            return True

        except Exception as e:
            self.logger.error(f"Error in large message send: {e}")
            return False


def main():
    """CLI エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="Beehive sender CLI tool with SQLite logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 基本的なメッセージ送信
  beehive sender beehive 0.0 "Hello, Worker Bee!"

  # 役割注入
  beehive sender beehive 0.0 "You are Queen Bee" --type role_injection --sender system

  # タスク割り当て
  beehive sender beehive 0.1 "Task: Implement feature X" --type task_assignment --sender queen

  # ログ表示
  beehive sender --logs --limit 20
  beehive sender --logs --session beehive --limit 10

  # ドライラン
  beehive sender beehive 0.0 "test message" --dry-run
        """,
    )

    # サブコマンドの設定
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # sender CLIサブコマンド
    send_parser = subparsers.add_parser("send", help="Send message to tmux pane")
    send_parser.add_argument("session_name", help="tmux session name")
    send_parser.add_argument("target_pane", help="Target pane (e.g., 0.0, 0.1)")
    send_parser.add_argument("message", help="Message to send")
    send_parser.add_argument("--type", help="Message type (role_injection, task_assignment, etc.)")
    send_parser.add_argument("--sender", help="Sender identifier")
    send_parser.add_argument("--metadata", help="Additional metadata as JSON string")
    send_parser.add_argument(
        "--dry-run", action="store_true", help="Dry run mode (no actual sender CLI)"
    )
    send_parser.add_argument(
        "--no-sender-header", action="store_true", help="Disable sender info header in message"
    )

    # ログ表示サブコマンド
    logs_parser = subparsers.add_parser("logs", help="Show sender CLI logs")
    logs_parser.add_argument("--session", help="Filter by session name")
    logs_parser.add_argument("--limit", type=int, default=50, help="Limit number of results")
    logs_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # 引数なしの場合はhelpを表示
    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()

    try:
        cli = SenderCLI()

        if args.command == "send":
            metadata = None
            if args.metadata:
                try:
                    metadata = json.loads(args.metadata)
                except json.JSONDecodeError:
                    print(f"Error: Invalid JSON in --metadata: {args.metadata}", file=sys.stderr)
                    sys.exit(1)

            success = cli.send_message(
                session_name=args.session_name,
                target_pane=args.target_pane,
                message=args.message,
                message_type=args.type,
                sender=args.sender,
                metadata=metadata,
                dry_run=args.dry_run,
                include_sender_header=not args.no_sender_header,
            )

            if success:
                print(f"✅ Message sent to {args.session_name}:{args.target_pane}")
            else:
                print("❌ Failed to send message", file=sys.stderr)
                sys.exit(1)

        elif args.command == "logs":
            if args.session:
                logs = cli.get_logs_by_session(args.session, args.limit)
            else:
                logs = cli.get_recent_logs(args.limit)

            if args.format == "json":
                print(json.dumps(logs, indent=2, ensure_ascii=False))
            else:
                # テーブル形式で表示
                if not logs:
                    print("No sender CLI logs found.")
                    return

                print(f"{'Timestamp':<20} {'Session':<10} {'Pane':<6} {'Type':<15} {'Message':<50}")
                print("-" * 100)
                for log in logs:
                    timestamp = log["timestamp"][:19] if log["timestamp"] else ""
                    message = (
                        (log["message"][:47] + "...")
                        if len(log["message"]) > 50
                        else log["message"]
                    )
                    message_type = log["message_type"] or ""
                    print(
                        f"{timestamp:<20} {log['session_name']:<10} {log['target_pane']:<6} "
                        f"{message_type:<15} {message}"
                    )

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
