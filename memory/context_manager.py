#!/usr/bin/env python3
"""
Context Manager for Beehive System
Issue #5: 定期的なコンテキストリマインダーシステム

Claudeインスタンスの長時間実行時の役割忘却を防ぐため、
定期的にコンテキストリマインダーを送信する機能を提供
"""

import json
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from bees.config import get_config
from bees.logging_config import get_logger


class ContextManager:
    """コンテキスト管理とリマインダー送信を担当するクラス"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.project_root = Path(__file__).parent.parent
        self.db_path = self.project_root / "hive" / "hive_memory.db"
        self.reminder_interval = 300  # 5分（秒）
        
        # Beeの役割定義
        self.bee_roles = {
            "queen": {
                "emoji": "🐝",
                "pane": "0",
                "role": "Queen Bee",
                "description": "タスクの計画・分解・指示を担当",
                "reminder": "あなたはQueen Beeです。チーム全体をリードし、Developer/QA/Analyst Beeに適切なタスクを割り当て、進捗を管理してください。"
            },
            "developer": {
                "emoji": "💻", 
                "pane": "1",
                "role": "Developer Bee",
                "description": "コードの実装を担当",
                "reminder": "あなたはDeveloper Beeです。Queen Beeからの指示に従い、高品質なコードを実装してください。完了時はQueen Beeに報告してください。"
            },
            "qa": {
                "emoji": "🔍",
                "pane": "2", 
                "role": "QA Bee",
                "description": "テストと品質保証を担当",
                "reminder": "あなたはQA Beeです。実装された機能のテスト・品質確認を行い、結果をQueen Beeに報告してください。"
            },
            "analyst": {
                "emoji": "📊",
                "pane": "3",
                "role": "Analyst Bee", 
                "description": "パフォーマンス分析・品質評価・レポート作成を担当",
                "reminder": "あなたはAnalyst Beeです。システムの分析・評価を行い、改善提案を含むレポートをQueen Beeに報告してください。"
            }
        }
        
        self._ensure_tables()

    def _load_role_definition(self, bee_name: str) -> Optional[str]:
        """rolesファイルから役割定義を読み込み"""
        role_file = self.project_root / "roles" / f"{bee_name}.md"
        
        try:
            if role_file.exists():
                with open(role_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                self.logger.debug(f"Loaded role definition for {bee_name} ({len(content)} chars)")
                return content
            else:
                self.logger.warning(f"Role file not found: {role_file}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to load role definition for {bee_name}: {e}")
            return None

    def _ensure_tables(self) -> None:
        """必要なテーブルを作成"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # リマインダー履歴テーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS reminder_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bee_name TEXT NOT NULL,
                        reminder_type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success INTEGER NOT NULL DEFAULT 1,
                        error_message TEXT
                    )
                """)
                
                # コンテキストスナップショットテーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS context_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bee_name TEXT NOT NULL,
                        current_task TEXT,
                        context_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                self.logger.info("Context manager tables initialized")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize context manager tables: {e}")
            raise

    def send_reminder(self, bee_name: str, custom_message: Optional[str] = None) -> bool:
        """指定されたBeeにリマインダーを送信"""
        if bee_name not in self.bee_roles:
            self.logger.error(f"Unknown bee: {bee_name}")
            return False
            
        bee_config = self.bee_roles[bee_name]
        
        if custom_message:
            message = custom_message
        else:
            # rolesファイルから実際の役割定義を読み込み
            role_content = self._load_role_definition(bee_name)
            if role_content:
                current_time = datetime.now().strftime("%H:%M")
                message = f"""🔔 [定期コンテキストリマインダー - {current_time}]

以下があなたの完全な役割定義です。長時間の作業により忘れてしまった可能性があるため、再確認してください：

{role_content}

──────────────────────────────────────────────────

現在の状況を確認し、上記の役割に従って作業を継続してください。
何か質問や困っていることがあれば、適切なBeeに相談してください。"""
            else:
                # フォールバック: 基本リマインダー
                current_time = datetime.now().strftime("%H:%M")
                message = f"""🔔 [定期リマインダー - {current_time}]

{bee_config['reminder']}

現在の状況を確認し、必要に応じて作業を継続してください。
何か質問や困っていることがあれば、適切なBeeに相談してください。"""

        # sender CLIを使用してリマインダーを送信
        try:
            cmd = [
                "python", "-m", "bees.cli", "send",
                "beehive", bee_config['pane'], 
                message,
                "--type", "role_reminder",
                "--sender", "system"
            ]
            
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            success = result.returncode == 0
            error_message = result.stderr if not success else None
            
            # 履歴をデータベースに記録
            self._save_reminder_history(bee_name, "periodic", message, success, error_message)
            
            if success:
                self.logger.info(f"Reminder sent to {bee_name} successfully")
            else:
                self.logger.error(f"Failed to send reminder to {bee_name}: {error_message}")
                
            return success
            
        except subprocess.TimeoutExpired:
            error_msg = "Reminder send timeout"
            self.logger.error(f"Timeout sending reminder to {bee_name}")
            self._save_reminder_history(bee_name, "periodic", message, False, error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(f"Error sending reminder to {bee_name}: {error_msg}")
            self._save_reminder_history(bee_name, "periodic", message, False, error_msg)
            return False

    def send_all_reminders(self) -> Dict[str, bool]:
        """全Beeにリマインダーを送信"""
        results = {}
        
        self.logger.info("Sending reminders to all bees")
        
        for bee_name in self.bee_roles.keys():
            results[bee_name] = self.send_reminder(bee_name)
            time.sleep(1)  # Beeごとに1秒間隔
            
        # 結果をログ出力
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        self.logger.info(f"Reminder batch completed: {successful}/{total} successful")
        
        return results

    def _save_reminder_history(
        self, 
        bee_name: str, 
        reminder_type: str, 
        message: str, 
        success: bool, 
        error_message: Optional[str] = None
    ) -> None:
        """リマインダー履歴をデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO reminder_history 
                    (bee_name, reminder_type, message, success, error_message)
                    VALUES (?, ?, ?, ?, ?)
                """, (bee_name, reminder_type, message, 1 if success else 0, error_message))
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to save reminder history: {e}")

    def get_reminder_history(self, limit: int = 50) -> List[Dict]:
        """リマインダー履歴を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM reminder_history 
                    ORDER BY sent_at DESC 
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get reminder history: {e}")
            return []

    def save_context_snapshot(self, bee_name: str, current_task: str, context_data: Dict) -> None:
        """コンテキストスナップショットを保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO context_snapshots 
                    (bee_name, current_task, context_data)
                    VALUES (?, ?, ?)
                """, (bee_name, current_task, json.dumps(context_data)))
                conn.commit()
                self.logger.debug(f"Context snapshot saved for {bee_name}")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to save context snapshot: {e}")

    def get_latest_context(self, bee_name: str) -> Optional[Dict]:
        """最新のコンテキストスナップショットを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM context_snapshots 
                    WHERE bee_name = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (bee_name,))
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    result['context_data'] = json.loads(result['context_data'])
                    return result
                return None
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get latest context: {e}")
            return None

    def is_tmux_session_active(self, session_name: str = "beehive") -> bool:
        """tmuxセッションがアクティブかチェック"""
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", session_name],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception) as e:
            self.logger.error(f"Error checking tmux session: {e}")
            return False

    def run_periodic_reminders(self, interval_seconds: Optional[int] = None) -> None:
        """定期リマインダーを実行（デーモンモード）"""
        if interval_seconds is None:
            interval_seconds = self.reminder_interval
            
        self.logger.info(f"Starting periodic reminders (interval: {interval_seconds}s)")
        
        try:
            while True:
                if self.is_tmux_session_active():
                    self.send_all_reminders()
                else:
                    self.logger.warning("tmux session 'beehive' not found, skipping reminders")
                
                self.logger.debug(f"Waiting {interval_seconds} seconds until next reminder cycle")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            self.logger.info("Periodic reminder daemon stopped by user")
        except Exception as e:
            self.logger.error(f"Periodic reminder daemon error: {e}")
            raise


def main():
    """CLI エントリーポイント"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Beehive Context Manager")
    parser.add_argument("--remind-all", action="store_true", help="Send reminders to all bees")
    parser.add_argument("--remind-bee", help="Send reminder to specific bee")
    parser.add_argument("--daemon", action="store_true", help="Run as periodic reminder daemon")
    parser.add_argument("--interval", type=int, default=300, help="Reminder interval in seconds (default: 300)")
    parser.add_argument("--history", action="store_true", help="Show reminder history")
    
    args = parser.parse_args()
    
    context_manager = ContextManager()
    
    if args.history:
        history = context_manager.get_reminder_history()
        print("=== Reminder History ===")
        for entry in history:
            status = "✅" if entry['success'] else "❌"
            print(f"{status} {entry['sent_at']} - {entry['bee_name']} ({entry['reminder_type']})")
            if not entry['success'] and entry['error_message']:
                print(f"   Error: {entry['error_message']}")
    
    elif args.remind_all:
        results = context_manager.send_all_reminders()
        for bee_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {bee_name}")
    
    elif args.remind_bee:
        success = context_manager.send_reminder(args.remind_bee)
        status = "✅" if success else "❌"
        print(f"{status} {args.remind_bee}")
    
    elif args.daemon:
        print(f"Starting reminder daemon (interval: {args.interval}s)")
        context_manager.run_periodic_reminders(args.interval)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()