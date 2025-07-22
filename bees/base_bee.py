#!/usr/bin/env python3
"""
Base Bee Class - 基本的な通信機能
Issue #4: 基本的な自律実行システム

SQLite + tmux send-keys 通信プロトコルによる自律エージェント基底クラス
"""

import json
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging


class BaseBee:
    """基本的な通信機能を持つBeeクラス"""
    
    def __init__(self, bee_name: str, hive_db_path: str = "hive/hive_memory.db"):
        self.bee_name = bee_name
        self.hive_db_path = Path(hive_db_path)
        self.session_name = "beehive"
        self.pane_map = {
            "queen": "0.0",
            "developer": "0.1", 
            "qa": "0.2"
        }
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(f"bee.{bee_name}")
        
        # データベース初期化
        self._init_database()
        self._update_bee_state("idle")
        
    def _init_database(self):
        """データベース接続を初期化"""
        if not self.hive_db_path.exists():
            self.logger.error(f"Database not found: {self.hive_db_path}")
            raise FileNotFoundError(f"Hive database not found: {self.hive_db_path}")
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """データベース接続を取得"""
        conn = sqlite3.connect(str(self.hive_db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _update_bee_state(self, status: str, task_id: Optional[int] = None, workload: int = 0):
        """Bee状態をデータベースで更新"""
        with self._get_db_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO bee_states 
                (bee_name, status, current_task_id, last_heartbeat, workload_score, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
            """, (self.bee_name, status, task_id, workload))
            conn.commit()
        
        self.logger.info(f"State updated: {status} (task: {task_id}, workload: {workload}%)")
    
    def send_message(self, to_bee: str, message_type: str, subject: str, content: str, 
                     task_id: Optional[int] = None, priority: str = "normal") -> int:
        """他のBeeにメッセージを送信（tmux send-keys中心）"""
        # SQLiteにはログとして記録のみ
        with self._get_db_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO bee_messages 
                (from_bee, to_bee, message_type, subject, content, task_id, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.bee_name, to_bee, message_type, subject, content, task_id, priority))
            message_id = cursor.lastrowid
            conn.commit()
        
        # 実際の通信はtmux send-keysで行う
        self._send_tmux_message(to_bee, message_type, subject, content, task_id)
        
        self.logger.info(f"Message sent to {to_bee}: {subject} (ID: {message_id})")
        return message_id
    
    def get_messages(self, processed: bool = False) -> List[Dict[str, Any]]:
        """自分宛のメッセージを取得（ログから履歴確認用）"""
        # 注意: 実際の通信はtmux経由のため、これは履歴確認用
        with self._get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM bee_messages 
                WHERE to_bee = ? AND processed = ?
                ORDER BY priority DESC, created_at ASC
            """, (self.bee_name, processed))
            messages = [dict(row) for row in cursor.fetchall()]
        
        return messages
    
    def mark_message_processed(self, message_id: int):
        """メッセージを処理済みとしてマーク"""
        with self._get_db_connection() as conn:
            conn.execute("""
                UPDATE bee_messages 
                SET processed = TRUE, processed_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
            """, (message_id,))
            conn.commit()
        
        self.logger.info(f"Message {message_id} marked as processed")
    
    def get_task_details(self, task_id: int) -> Optional[Dict[str, Any]]:
        """タスクの詳細情報を取得"""
        with self._get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM tasks WHERE task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_task_status(self, task_id: int, status: str, notes: Optional[str] = None):
        """タスク状態を更新"""
        with self._get_db_connection() as conn:
            # タスク状態更新
            conn.execute("""
                UPDATE tasks 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (status, task_id))
            
            # アクティビティログに記録
            conn.execute("""
                INSERT INTO task_activity 
                (task_id, bee_name, activity_type, description)
                VALUES (?, ?, ?, ?)
            """, (task_id, self.bee_name, "status_update", 
                  f"Status changed to {status}" + (f": {notes}" if notes else "")))
            
            conn.commit()
        
        self.logger.info(f"Task {task_id} status updated to: {status}")
    
    def log_activity(self, task_id: int, activity_type: str, description: str, 
                     metadata: Optional[Dict] = None):
        """アクティビティをログに記録"""
        with self._get_db_connection() as conn:
            conn.execute("""
                INSERT INTO task_activity 
                (task_id, bee_name, activity_type, description, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (task_id, self.bee_name, activity_type, description, 
                  json.dumps(metadata) if metadata else None))
            conn.commit()
        
        self.logger.info(f"Activity logged: {activity_type} - {description}")
    
    def _send_tmux_message(self, target_bee: str, message_type: str, subject: str, 
                          content: str, task_id: Optional[int] = None):
        """tmux経由でメッセージを送信（メイン通信手段）"""
        if target_bee not in self.pane_map:
            self.logger.warning(f"Unknown target bee: {target_bee}")
            return
        
        pane = self.pane_map[target_bee]
        
        # 構造化されたメッセージを作成
        message_header = f"## 📨 MESSAGE FROM {self.bee_name.upper()}"
        message_details = [
            "",
            f"**Type:** {message_type}",
            f"**Subject:** {subject}",
            f"**Task ID:** {task_id if task_id else 'N/A'}",
            "",
            "**Content:**"
        ]
        
        # コンテンツを行に分割
        content_lines = content.split('\n')
        
        try:
            # ヘッダー送信
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session_name}:{pane}",
                "", "Enter",
                message_header, "Enter"
            ], check=True, capture_output=True, text=True)
            
            # 詳細情報送信
            for line in message_details:
                subprocess.run([
                    "tmux", "send-keys", "-t", f"{self.session_name}:{pane}",
                    line, "Enter"
                ], check=True, capture_output=True, text=True)
            
            # コンテンツ送信
            for line in content_lines:
                subprocess.run([
                    "tmux", "send-keys", "-t", f"{self.session_name}:{pane}",
                    line, "Enter"
                ], check=True, capture_output=True, text=True)
            
            # フッター
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session_name}:{pane}",
                "", "Enter",
                "---", "Enter",
                "", "Enter"
            ], check=True, capture_output=True, text=True)
            
            self.logger.debug(f"tmux message sent to {target_bee}: {subject}")
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to send tmux message: {e}")
    
    def _send_tmux_notification(self, target_bee: str, message: str):
        """tmux経由で簡単な通知を送信"""
        if target_bee not in self.pane_map:
            self.logger.warning(f"Unknown target bee: {target_bee}")
            return
        
        pane = self.pane_map[target_bee]
        try:
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session_name}:{pane}",
                f"", "Enter",  # 空行
                f"# {message}", "Enter",
                f"", "Enter"   # 空行
            ], check=True, capture_output=True, text=True)
            
            self.logger.debug(f"tmux notification sent to {target_bee}")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to send tmux notification: {e}")
    
    def heartbeat(self):
        """生存確認のハートビート"""
        with self._get_db_connection() as conn:
            conn.execute("""
                UPDATE bee_states 
                SET last_heartbeat = CURRENT_TIMESTAMP
                WHERE bee_name = ?
            """, (self.bee_name,))
            conn.commit()
    
    def get_workload_status(self) -> Dict[str, Any]:
        """現在のワークロード状況を取得"""
        with self._get_db_connection() as conn:
            # 自分の状態
            cursor = conn.execute("""
                SELECT * FROM bee_states WHERE bee_name = ?
            """, (self.bee_name,))
            bee_state = dict(cursor.fetchone() or {})
            
            # アクティブタスク数
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM tasks 
                WHERE assigned_to = ? AND status IN ('pending', 'in_progress')
            """, (self.bee_name,))
            active_tasks = cursor.fetchone()[0]
            
            # 未処理メッセージ数
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM bee_messages 
                WHERE to_bee = ? AND processed = FALSE
            """, (self.bee_name,))
            unread_messages = cursor.fetchone()[0]
            
            return {
                "bee_state": bee_state,
                "active_tasks": active_tasks,
                "unread_messages": unread_messages,
                "timestamp": datetime.now().isoformat()
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
    
    def _process_message(self, message: Dict[str, Any]):
        """メッセージを処理（サブクラスでオーバーライド）"""
        # 注意: 実際の通信はtmux経由のため、これはログ処理用
        # Claudeが直接受け取ったメッセージに対して手動で呼び出される想定
        self.logger.info(f"Processing message: {message['subject']} from {message['from_bee']}")
        
        # 基本的な応答例
        if message['message_type'] == 'question':
            response = f"Message received: {message['subject']}"
            self.send_message(
                message['from_bee'], 
                'response', 
                f"Re: {message['subject']}", 
                response,
                message.get('task_id')
            )
        
        # メッセージを処理済みにマーク
        self.mark_message_processed(message['message_id'])
    
    def process_tmux_input(self, user_input: str):
        """tmux経由で受信したユーザー入力を処理（Claudeが実際に使用）"""
        # tmux経由でClaudeが受け取った入力を解析
        if user_input.startswith("## 📨 MESSAGE FROM"):
            # 構造化メッセージの処理
            self._parse_structured_message(user_input)
        else:
            # 通常の作業指示として処理
            self._handle_work_instruction(user_input)
    
    def _parse_structured_message(self, message_text: str):
        """構造化メッセージを解析（サブクラスでオーバーライド）"""
        self.logger.info("Received structured message via tmux")
        # 基本実装では解析のみ
        lines = message_text.split('\n')
        for line in lines:
            if line.startswith("**Type:**"):
                message_type = line.replace("**Type:**", "").strip()
            elif line.startswith("**Subject:**"):
                subject = line.replace("**Subject:**", "").strip()
            elif line.startswith("**Task ID:**"):
                task_id = line.replace("**Task ID:**", "").strip()
        
        self.logger.info(f"Parsed message - Type: {message_type}, Subject: {subject}")
    
    def _handle_work_instruction(self, instruction: str):
        """通常の作業指示を処理（サブクラスでオーバーライド）"""
        self.logger.info(f"Received work instruction: {instruction[:50]}...")
        # 基底クラスでは基本的な応答のみ
        print(f"✅ {self.bee_name} received instruction: {instruction[:50]}...")