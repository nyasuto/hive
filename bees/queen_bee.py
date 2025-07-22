#!/usr/bin/env python3
"""
Queen Bee Class - タスク管理・指示機能
Issue #4: 基本的な自律実行システム

タスクの分解・割り当て・進捗管理を行うQueen Beeクラス
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from .base_bee import BaseBee


class QueenBee(BaseBee):
    """タスク管理と指示を行うQueen Beeクラス"""
    
    def __init__(self, hive_db_path: str = "hive/hive_memory.db"):
        super().__init__("queen", hive_db_path)
        self.available_bees = ["developer", "qa"]
        self.task_assignment_strategy = "balanced"  # balanced, specialized, priority
        
        self.logger.info("Queen Bee initialized - Ready for task management")
    
    def create_task(self, title: str, description: str, priority: str = "medium", 
                    estimated_hours: Optional[float] = None, 
                    parent_task_id: Optional[int] = None) -> int:
        """新しいタスクを作成"""
        with self._get_db_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO tasks 
                (title, description, priority, estimated_hours, parent_task_id, created_by, assigned_to)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, description, priority, estimated_hours, parent_task_id, self.bee_name, self.bee_name))
            
            task_id = cursor.lastrowid
            
            # アクティビティログ
            conn.execute("""
                INSERT INTO task_activity 
                (task_id, bee_name, activity_type, description)
                VALUES (?, ?, ?, ?)
            """, (task_id, self.bee_name, "created", f"Task created: {title}"))
            
            conn.commit()
        
        self.logger.info(f"Task created: {title} (ID: {task_id})")
        return task_id
    
    def decompose_task(self, task_id: int, subtasks: List[Dict[str, Any]]) -> List[int]:
        """タスクをサブタスクに分解"""
        subtask_ids = []
        
        for subtask in subtasks:
            subtask_id = self.create_task(
                title=subtask['title'],
                description=subtask['description'], 
                priority=subtask.get('priority', 'medium'),
                estimated_hours=subtask.get('estimated_hours'),
                parent_task_id=task_id
            )
            subtask_ids.append(subtask_id)
        
        # 親タスクの状態を更新
        self.update_task_status(task_id, "in_progress", f"Decomposed into {len(subtasks)} subtasks")
        self.log_activity(task_id, "decomposed", f"Created {len(subtasks)} subtasks", 
                         {"subtask_ids": subtask_ids})
        
        self.logger.info(f"Task {task_id} decomposed into {len(subtasks)} subtasks")
        return subtask_ids
    
    def assign_task_to_bee(self, task_id: int, target_bee: str, 
                          assignment_reason: str = "") -> bool:
        """指定されたBeeにタスクを割り当て"""
        if target_bee not in self.available_bees:
            self.logger.error(f"Unknown bee: {target_bee}")
            return False
        
        # Bee のワークロードをチェック
        bee_workload = self._get_bee_workload(target_bee)
        if bee_workload > 80:  # 80%以上の場合は警告
            self.logger.warning(f"{target_bee} has high workload: {bee_workload}%")
        
        with self._get_db_connection() as conn:
            # タスクの割り当て
            conn.execute("""
                UPDATE tasks 
                SET assigned_to = ?, status = 'pending', updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (target_bee, task_id))
            
            # 割り当て記録
            conn.execute("""
                INSERT INTO task_assignments 
                (task_id, assigned_to, assigned_by, assignment_type, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (task_id, target_bee, self.bee_name, "primary", assignment_reason))
            
            conn.commit()
        
        # Beeにメッセージで通知
        task_details = self.get_task_details(task_id)
        assignment_message = f"""新しいタスクが割り当てられました

タスク: {task_details['title']}
説明: {task_details['description']}
優先度: {task_details['priority']}
推定時間: {task_details.get('estimated_hours', 'N/A')} 時間

{assignment_reason}

詳細確認: task_id = {task_id}
"""
        
        self.send_message(
            target_bee, 
            "task_update", 
            f"新規タスク割り当て: {task_details['title']}", 
            assignment_message,
            task_id,
            "high"
        )
        
        self.log_activity(task_id, "assigned", f"Assigned to {target_bee}", 
                         {"reason": assignment_reason})
        
        self.logger.info(f"Task {task_id} assigned to {target_bee}")
        return True
    
    def auto_assign_tasks(self) -> int:
        """自動タスク割り当て（未割り当てタスクを適切なBeeに分配）"""
        unassigned_tasks = self._get_unassigned_tasks()
        assigned_count = 0
        
        for task in unassigned_tasks:
            best_bee = self._select_best_bee_for_task(task)
            if best_bee:
                reason = f"Auto-assigned based on {self.task_assignment_strategy} strategy"
                if self.assign_task_to_bee(task['task_id'], best_bee, reason):
                    assigned_count += 1
        
        self.logger.info(f"Auto-assigned {assigned_count} tasks")
        return assigned_count
    
    def _get_unassigned_tasks(self) -> List[Dict[str, Any]]:
        """未割り当てタスクのリストを取得"""
        with self._get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM tasks 
                WHERE assigned_to IS NULL OR assigned_to = ?
                AND status = 'pending'
                ORDER BY priority DESC, created_at ASC
            """, (self.bee_name,))
            return [dict(row) for row in cursor.fetchall()]
    
    def _select_best_bee_for_task(self, task: Dict[str, Any]) -> Optional[str]:
        """タスクに最適なBeeを選択"""
        if self.task_assignment_strategy == "balanced":
            return self._get_least_loaded_bee()
        elif self.task_assignment_strategy == "specialized":
            return self._get_specialized_bee_for_task(task)
        elif self.task_assignment_strategy == "priority":
            if task['priority'] == 'critical':
                return self._get_best_performer_bee()
            else:
                return self._get_least_loaded_bee()
        else:
            return self._get_least_loaded_bee()
    
    def _get_least_loaded_bee(self) -> Optional[str]:
        """最も負荷の少ないBeeを取得"""
        workloads = {}
        for bee in self.available_bees:
            workloads[bee] = self._get_bee_workload(bee)
        
        if workloads:
            return min(workloads, key=workloads.get)
        return None
    
    def _get_specialized_bee_for_task(self, task: Dict[str, Any]) -> str:
        """タスクの種類に基づいて専門Beeを選択"""
        task_title = task['title'].lower()
        task_desc = task['description'].lower()
        
        # キーワードベースの判定（簡易版）
        if any(keyword in task_title + task_desc for keyword in 
               ['test', 'qa', 'quality', 'bug', 'verify', 'check']):
            return "qa"
        elif any(keyword in task_title + task_desc for keyword in 
                ['code', 'implement', 'develop', 'build', 'create', 'fix']):
            return "developer"
        else:
            return self._get_least_loaded_bee()
    
    def _get_best_performer_bee(self) -> Optional[str]:
        """最も性能の高いBeeを取得"""
        with self._get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT bee_name FROM bee_states 
                WHERE bee_name IN (?, ?)
                ORDER BY performance_score DESC
                LIMIT 1
            """, tuple(self.available_bees))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def _get_bee_workload(self, bee_name: str) -> float:
        """指定されたBeeのワークロードを取得"""
        with self._get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT workload_score FROM bee_states WHERE bee_name = ?
            """, (bee_name,))
            row = cursor.fetchone()
            return row[0] if row else 0.0
    
    def review_task_progress(self) -> Dict[str, Any]:
        """タスクの進捗をレビュー"""
        with self._get_db_connection() as conn:
            # 全体の進捗統計
            cursor = conn.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(CAST(actual_hours as REAL)) as avg_hours
                FROM tasks 
                GROUP BY status
            """)
            status_stats = [dict(row) for row in cursor.fetchall()]
            
            # Bee別の作業状況
            cursor = conn.execute("""
                SELECT 
                    assigned_to,
                    COUNT(*) as active_tasks,
                    AVG(workload_score) as avg_workload
                FROM tasks t
                LEFT JOIN bee_states bs ON t.assigned_to = bs.bee_name
                WHERE t.status IN ('pending', 'in_progress')
                GROUP BY assigned_to
            """)
            bee_stats = [dict(row) for row in cursor.fetchall()]
            
            # 遅延タスク
            cursor = conn.execute("""
                SELECT task_id, title, assigned_to, due_date
                FROM tasks 
                WHERE due_date < CURRENT_TIMESTAMP 
                AND status NOT IN ('completed', 'cancelled')
            """)
            overdue_tasks = [dict(row) for row in cursor.fetchall()]
        
        progress_report = {
            "status_statistics": status_stats,
            "bee_statistics": bee_stats,
            "overdue_tasks": overdue_tasks,
            "review_timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"Progress review completed: {len(overdue_tasks)} overdue tasks")
        return progress_report
    
    def _process_message(self, message: Dict[str, Any]):
        """Queen Bee固有のメッセージ処理"""
        message_type = message['message_type']
        from_bee = message['from_bee']
        task_id = message.get('task_id')
        
        self.logger.info(f"Processing {message_type} from {from_bee}")
        
        if message_type == "task_update":
            # Worker Beeからの進捗報告
            self._handle_progress_report(message)
        elif message_type == "request":
            # リソース要求や支援要請
            self._handle_resource_request(message)
        elif message_type == "question":
            # 質問や相談
            self._handle_consultation(message)
        else:
            # 基底クラスの処理を呼び出し
            super()._process_message(message)
    
    def _handle_progress_report(self, message: Dict[str, Any]):
        """進捗報告の処理"""
        task_id = message.get('task_id')
        from_bee = message['from_bee']
        content = message['content']
        
        if task_id:
            # タスクの進捗を記録
            self.log_activity(task_id, "progress_report", 
                            f"Progress report from {from_bee}: {content}")
            
            # 必要に応じて次のアクションを決定
            task_details = self.get_task_details(task_id)
            if task_details and task_details['status'] == 'completed':
                self._handle_task_completion(task_id, from_bee)
        
        # メッセージを処理済みにマーク
        self.mark_message_processed(message['message_id'])
    
    def _handle_task_completion(self, task_id: int, completed_by: str):
        """タスク完了時の処理"""
        self.logger.info(f"Task {task_id} completed by {completed_by}")
        
        # 子タスクがある場合、親タスクの状態をチェック
        parent_task = self._get_parent_task(task_id)
        if parent_task:
            if self._all_subtasks_completed(parent_task['task_id']):
                self.update_task_status(parent_task['task_id'], 'completed', 
                                      "All subtasks completed")
        
        # 新しいタスクの自動割り当て
        self.auto_assign_tasks()
    
    def _get_parent_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """親タスクを取得"""
        with self._get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT p.* FROM tasks p
                JOIN tasks c ON p.task_id = c.parent_task_id
                WHERE c.task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def _all_subtasks_completed(self, parent_task_id: int) -> bool:
        """すべてのサブタスクが完了しているかチェック"""
        with self._get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
                FROM tasks WHERE parent_task_id = ?
            """, (parent_task_id,))
            row = cursor.fetchone()
            return row and row['total'] == row['completed']
    
    def _handle_resource_request(self, message: Dict[str, Any]):
        """リソース要求の処理"""
        # 簡易実装：要求を承認し、必要に応じて他のBeeに協力を要請
        from_bee = message['from_bee']
        
        response = f"Resource request acknowledged. Processing your request."
        self.send_message(from_bee, "response", f"Re: {message['subject']}", response)
        self.mark_message_processed(message['message_id'])
    
    def _handle_consultation(self, message: Dict[str, Any]):
        """相談の処理"""
        from_bee = message['from_bee'] 
        task_id = message.get('task_id')
        
        # 基本的な指導的回答
        response = f"Thank you for consulting me. Please proceed with your best judgment. I trust your expertise as {from_bee}."
        
        if task_id:
            task_details = self.get_task_details(task_id)
            if task_details:
                response += f"\n\nFor task '{task_details['title']}', focus on the core requirements and maintain quality."
        
        self.send_message(from_bee, "response", f"Re: {message['subject']}", response)
        self.mark_message_processed(message['message_id'])