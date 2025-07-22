#!/usr/bin/env python3
"""
Beehive CLI Tool
Issue #25: send-keys処理のCLI化とSQLite透過保存

tmux send-keysの処理を集約し、SQLiteでの透過的ログ保存を提供
"""

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import get_config
from .exceptions import DatabaseOperationError, TmuxCommandError, ValidationError
from .logging_config import get_logger


class SendKeysCLI:
    """send-keys処理のCLI化クラス"""

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
                    CREATE TABLE IF NOT EXISTS send_keys_log (
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

    def send_keys(
        self,
        session_name: str,
        target_pane: str,
        message: str,
        message_type: str | None = None,
        sender: str | None = None,
        metadata: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> bool:
        """
        tmux send-keysコマンドを実行し、SQLiteにログを保存

        Args:
            session_name: tmuxセッション名
            target_pane: 対象ペイン（例: "0.0", "0.1"）
            message: 送信するメッセージ
            message_type: メッセージタイプ（role_injection, task_assignment等）
            sender: 送信者名
            metadata: 追加メタデータ
            dry_run: ドライランモード

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

        try:
            if not dry_run:
                # tmux send-keysコマンドを実行
                target = f"{session_name}:{target_pane}"

                # メッセージを行ごとに分割して送信
                lines = message.strip().split("\n")
                for line in lines:
                    if line.strip():  # 空行でない場合
                        cmd = ["tmux", "send-keys", "-t", target, line, "Enter"]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                        if result.returncode != 0:
                            success = False
                            error_message = f"tmux send-keys failed: {result.stderr}"
                            break
                    else:
                        # 空行は改行のみ送信
                        cmd = ["tmux", "send-keys", "-t", target, "Enter"]
                        subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                self.logger.info(f"Send-keys executed: {target} <- {message[:50]}...")
            else:
                self.logger.info(
                    f"[DRY-RUN] Send-keys: {session_name}:{target_pane} <- {message[:50]}..."
                )

        except subprocess.TimeoutExpired:
            success = False
            error_message = "tmux send-keys command timed out"
        except subprocess.CalledProcessError as e:
            success = False
            error_message = f"tmux send-keys failed: {e.stderr}"
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
            self.logger.error(f"Failed to save send-keys log to database: {e}")
            # ログ保存失敗してもsend-keys処理は継続

        if not success and error_message:
            raise TmuxCommandError(
                f"send-keys to {session_name}:{target_pane}", Exception(error_message)
            )

        return success

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
                    INSERT INTO send_keys_log (
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
            raise DatabaseOperationError("save_send_keys_log", "INSERT", e)

    def get_recent_logs(self, limit: int = 50) -> list:
        """最近のsend-keysログを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM send_keys_log
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
                    SELECT * FROM send_keys_log
                    WHERE session_name = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (session_name, limit),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseOperationError("get_logs_by_session", "SELECT", e)


def main():
    """CLI エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="Beehive send-keys CLI tool with SQLite logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 基本的なメッセージ送信
  beehive send-keys beehive 0.0 "Hello, Worker Bee!"

  # 役割注入
  beehive send-keys beehive 0.0 "You are Queen Bee" --type role_injection --sender system

  # タスク割り当て
  beehive send-keys beehive 0.1 "Task: Implement feature X" --type task_assignment --sender queen

  # ログ表示
  beehive send-keys --logs --limit 20
  beehive send-keys --logs --session beehive --limit 10

  # ドライラン
  beehive send-keys beehive 0.0 "test message" --dry-run
        """,
    )

    # サブコマンドの設定
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # send-keysサブコマンド
    send_parser = subparsers.add_parser("send", help="Send keys to tmux pane")
    send_parser.add_argument("session_name", help="tmux session name")
    send_parser.add_argument("target_pane", help="Target pane (e.g., 0.0, 0.1)")
    send_parser.add_argument("message", help="Message to send")
    send_parser.add_argument("--type", help="Message type (role_injection, task_assignment, etc.)")
    send_parser.add_argument("--sender", help="Sender identifier")
    send_parser.add_argument("--metadata", help="Additional metadata as JSON string")
    send_parser.add_argument(
        "--dry-run", action="store_true", help="Dry run mode (no actual send-keys)"
    )

    # ログ表示サブコマンド
    logs_parser = subparsers.add_parser("logs", help="Show send-keys logs")
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
        cli = SendKeysCLI()

        if args.command == "send":
            metadata = None
            if args.metadata:
                try:
                    metadata = json.loads(args.metadata)
                except json.JSONDecodeError:
                    print(f"Error: Invalid JSON in --metadata: {args.metadata}", file=sys.stderr)
                    sys.exit(1)

            success = cli.send_keys(
                session_name=args.session_name,
                target_pane=args.target_pane,
                message=args.message,
                message_type=args.type,
                sender=args.sender,
                metadata=metadata,
                dry_run=args.dry_run,
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
                    print("No send-keys logs found.")
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
