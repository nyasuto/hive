#!/usr/bin/env python3
"""
Worker Bee Class - 作業実行・報告機能
Issue #4: 基本的な自律実行システム

作業実行とQueenへの報告を行うWorker Beeクラス（Developer/QA共通基底）
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any

from .base_bee import BaseBee
from .config import BeehiveConfig, get_config
from .exceptions import (
    DatabaseConnectionError,
    error_handler,
)


class WorkerBee(BaseBee):
    """作業実行と報告を行うWorker Beeクラス"""

    def __init__(self, bee_name: str, specialty: str, config: BeehiveConfig | None = None) -> None:
        """ワーカーBeeを初期化

        Args:
            bee_name: Beeの名前
            specialty: 専門分野 (development, qa, 等)
            config: 設定オブジェクト
        """
        self.config = config or get_config()
        super().__init__(bee_name, self.config)

        # 専門分野の設定
        self.specialty = specialty
        self.current_task_id: str | None = None
        self.work_session_start: datetime | None = None

        # 作業能力の定義
        self.capabilities: list[str] = self._define_capabilities()
        self._update_bee_capabilities()

        self.logger.log_event(
            "worker_initialization",
            f"{specialty.title()} Worker Bee initialized - Ready for task execution",
            "INFO",
            specialty=specialty,
        )

    def _define_capabilities(self) -> list[str]:
        """Bee固有の能力を定義（サブクラスでオーバーライド）

        Returns:
            能力リスト
        """
        return ["general_work", "task_execution", "reporting"]

    @error_handler
    def _update_bee_capabilities(self) -> None:
        """データベースでBeeの能力情報を更新

        Raises:
            DatabaseConnectionError: データベース更新に失敗した場合
        """
        try:
            capabilities_json = json.dumps(self.capabilities)
            with self._get_db_connection() as conn:
                conn.execute(
                    """
                    UPDATE bee_states
                    SET capabilities = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE bee_name = ?
                """,
                    (capabilities_json, self.bee_name),
                )
                conn.commit()
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to update capabilities: {e}") from e

    def accept_task(self, task_id: str) -> bool:
        """タスクを受け入れて作業を開始"""
        task_details = self.get_task_details(task_id)
        if not task_details:
            self.logger.error(f"Task {task_id} not found")
            return False

        # タスクが自分に割り当てられているかチェック
        if task_details["assigned_to"] != self.bee_name:
            self.logger.error(f"Task {task_id} is not assigned to {self.bee_name}")
            return False

        # 現在の作業を確認
        if self.current_task_id:
            self.logger.warning(f"Already working on task {self.current_task_id}")
            return False

        # タスク受け入れ
        self.current_task_id = task_id
        self.work_session_start = datetime.now()

        # データベース状態更新
        self.update_task_status(task_id, "in_progress", "Task accepted and work started")
        self._update_bee_state("busy", task_id, 50)

        # Queen Beeに報告
        self.send_message(
            "queen",
            "task_update",
            f"Task accepted: {task_details['title']}",
            f"Task {task_id} has been accepted and work has started.\n"
            f"Estimated completion: {self._estimate_completion_time(task_details)}",
            task_id,
            "normal",
        )

        self.log_activity(task_id, "accepted", f"Task accepted by {self.bee_name}")
        self.logger.info(f"Task {task_id} accepted: {task_details['title']}")
        return True

    def complete_task(
        self,
        task_id: str,
        result: str,
        deliverables: list[str] | None = None,
        work_summary: str = "",
        quality_notes: str = "",
    ) -> bool:
        """タスクを完了して結果を報告"""
        if task_id != self.current_task_id:
            self.logger.error(f"Task {task_id} is not the current working task")
            return False

        task_details = self.get_task_details(task_id)
        if not task_details:
            self.logger.error(f"Task {task_id} not found")
            return False

        # 作業時間計算
        work_duration = self._calculate_work_duration()

        # タスクを完了状態に更新
        self.update_task_status(task_id, "completed", "Task completed successfully")

        # 作業時間を記録
        with self._get_db_connection() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET actual_hours = ?, completed_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """,
                (work_duration, task_id),
            )
            conn.commit()

        # Queen Beeに完了報告
        completion_report = self._generate_completion_report(
            task_details, result, deliverables, work_summary, quality_notes, work_duration
        )

        self.send_message(
            "queen",
            "task_update",
            f"Task completed: {task_details['title']}",
            completion_report,
            task_id,
            "high",
        )

        # 作業状態をリセット
        self.current_task_id = None
        self.work_session_start = None
        self._update_bee_state("idle", None, 0)

        self.log_activity(
            task_id,
            "completed",
            f"Task completed by {self.bee_name}",
            {
                "work_duration_hours": work_duration,
                "deliverables": deliverables or [],
                "quality_notes": quality_notes,
            },
        )

        self.logger.info(f"Task {task_id} completed in {work_duration:.2f} hours")
        return True

    def report_progress(
        self,
        task_id: str,
        progress_percentage: int,
        status_note: str,
        blocking_issues: list[str] | None = None,
    ) -> bool:
        """作業進捗をQueenに報告"""
        if task_id != self.current_task_id:
            self.logger.warning(f"Reporting progress for non-current task {task_id}")

        task_details = self.get_task_details(task_id)
        if not task_details:
            return False

        # ワークロードスコアを更新
        workload = min(100, max(0, progress_percentage))  # 0-100の範囲に制限
        self._update_bee_state("busy", task_id, workload)

        # 進捗報告メッセージ
        progress_message = f"""Progress Update - {progress_percentage}% complete

Status: {status_note}
Time elapsed: {self._calculate_work_duration():.2f} hours

"""

        if blocking_issues:
            progress_message += "⚠️  Blocking Issues:\n"
            for issue in blocking_issues:
                progress_message += f"- {issue}\n"
            progress_message += "\nAssistance may be needed to resolve these issues."

        self.send_message(
            "queen",
            "task_update",
            f"Progress {progress_percentage}%: {task_details['title']}",
            progress_message,
            task_id,
            "high" if blocking_issues else "normal",
        )

        self.log_activity(
            task_id,
            "progress_update",
            f"{progress_percentage}% complete: {status_note}",
            {"blocking_issues": blocking_issues or []},
        )

        self.logger.info(f"Progress reported for task {task_id}: {progress_percentage}%")
        return True

    def request_assistance(
        self, task_id: str, assistance_type: str, details: str, urgent: bool = False
    ) -> bool:
        """Queenまたは他のBeeに支援を要請"""
        task_details = self.get_task_details(task_id)
        if not task_details:
            return False

        assistance_message = f"""Assistance Request - {assistance_type}

Task: {task_details["title"]}
Request Details: {details}

Current progress: {self._get_current_progress(task_id)}%
Time spent: {self._calculate_work_duration():.2f} hours

Please advise on how to proceed.
"""

        priority = "urgent" if urgent else "high"

        self.send_message(
            "queen",
            "request",
            f"Assistance needed: {assistance_type}",
            assistance_message,
            task_id,
            priority,
        )

        self.log_activity(task_id, "assistance_request", f"Requested {assistance_type}: {details}")

        self.logger.info(f"Assistance requested for task {task_id}: {assistance_type}")
        return True

    def _estimate_completion_time(self, task_details: dict[str, Any]) -> str:
        """タスクの完了予定時間を推定"""
        estimated_hours = task_details.get("estimated_hours", 2.0)
        completion_time = datetime.now() + timedelta(hours=estimated_hours)
        return completion_time.strftime("%Y-%m-%d %H:%M")

    def _calculate_work_duration(self) -> float:
        """現在の作業セッションの時間を計算（時間単位）"""
        if not self.work_session_start:
            return 0.0

        duration = datetime.now() - self.work_session_start
        return duration.total_seconds() / 3600.0  # 時間に変換

    def _get_current_progress(self, task_id: str) -> int:
        """現在のタスク進捗を取得（推定）"""
        # 簡易実装：作業時間から進捗を推定
        work_duration = self._calculate_work_duration()
        task_details = self.get_task_details(task_id)

        if task_details and task_details.get("estimated_hours"):
            estimated_hours = task_details["estimated_hours"]
            progress = min(90, int((work_duration / estimated_hours) * 100))
            return progress

        return 50  # デフォルト値

    def _generate_completion_report(
        self,
        task_details: dict[str, Any],
        result: str,
        deliverables: list[str] | None,
        work_summary: str,
        quality_notes: str,
        work_duration: float,
    ) -> str:
        """完了報告書を生成"""
        report = f"""Task Completion Report

📋 Task: {task_details["title"]}
🎯 Status: COMPLETED
⏱️  Duration: {work_duration:.2f} hours
📅 Completed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

🔍 Result Summary:
{result}

"""

        if work_summary:
            report += f"📝 Work Summary:\n{work_summary}\n\n"

        if deliverables:
            report += "📦 Deliverables:\n"
            for item in deliverables:
                report += f"- {item}\n"
            report += "\n"

        if quality_notes:
            report += f"✅ Quality Notes:\n{quality_notes}\n\n"

        # 効率性評価
        estimated_hours = task_details.get("estimated_hours", work_duration)
        efficiency = (estimated_hours / work_duration * 100) if work_duration > 0 else 100
        report += f"📊 Efficiency: {efficiency:.1f}% (Est: {estimated_hours:.1f}h, Actual: {work_duration:.2f}h)\n"

        return report

    def _process_message(self, message: dict[str, Any]):
        """Worker Bee固有のメッセージ処理"""
        message_type = message["message_type"]
        from_bee = message["from_bee"]
        task_id = message.get("task_id")

        self.logger.info(f"Processing {message_type} from {from_bee}")

        if message_type == "task_update" and from_bee == "queen":
            # Queenからのタスク割り当てや更新
            self._handle_task_assignment(message)
        elif message_type == "request":
            # 協力要請や指示
            self._handle_work_request(message)
        elif message_type == "response" and task_id:
            # 相談や質問への回答
            self._handle_queen_response(message)
        else:
            # 基底クラスの処理
            super()._process_message(message)

    def _handle_task_assignment(self, message: dict[str, Any]):
        """Queenからのタスク割り当てを処理"""
        task_id = message.get("task_id")
        if task_id and not self.current_task_id:
            # 自動的にタスクを受け入れ
            if self.accept_task(task_id):
                self.logger.info(f"Auto-accepted task {task_id}")

        self.mark_message_processed(message["message_id"])

    def _handle_work_request(self, message: dict[str, Any]):
        """作業要請を処理"""
        # 基本的には受け入れる
        from_bee = message["from_bee"]
        response = "Request acknowledged. I will prioritize this work."

        self.send_message(from_bee, "response", f"Re: {message['subject']}", response)
        self.mark_message_processed(message["message_id"])

    def _handle_queen_response(self, message: dict[str, Any]):
        """Queenからの回答を処理"""
        task_id = message.get("task_id")
        if task_id and task_id == self.current_task_id:
            # 指示に基づいて作業を調整
            self.log_activity(
                task_id, "guidance_received", f"Guidance from Queen: {message['content']}"
            )

        self.mark_message_processed(message["message_id"])

    def simulate_work(self, task_id: str, work_steps: list[dict[str, Any]]) -> bool:
        """作業をシミュレート（デモ用）"""
        if not self.accept_task(task_id):
            return False

        self.logger.info(f"Starting simulated work for task {task_id}")

        for i, step in enumerate(work_steps):
            step_name = step.get("name", f"Step {i + 1}")
            duration = step.get("duration", 5)  # seconds
            progress = step.get("progress", (i + 1) * 100 // len(work_steps))

            self.logger.info(f"Executing: {step_name}")
            time.sleep(duration)

            # 進捗報告
            self.report_progress(task_id, progress, f"Completed {step_name}")

        # 作業完了
        result = "Simulated work completed successfully"
        deliverables = [
            f"Deliverable from {step.get('name', f'Step {i + 1}')}"
            for i, step in enumerate(work_steps)
        ]

        return self.complete_task(
            task_id,
            result,
            deliverables,
            "Simulated work execution",
            "All steps completed as planned",
        )
