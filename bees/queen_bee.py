#!/usr/bin/env python3
"""
Queen Bee Class - タスク管理・指示機能
Issue #4: 基本的な自律実行システム

タスクの分解・割り当て・進捗管理を行うQueen Beeクラス
"""

from datetime import datetime
from typing import Any

from .base_bee import BaseBee
from .config import BeehiveConfig, get_config
from .exceptions import (
    BeeNotFoundError,
    DatabaseConnectionError,
    TaskValidationError,
    WorkflowError,
    error_handler,
)


class QueenBee(BaseBee):
    """タスク管理と指示を行うQueen Beeクラス

    Queen Beeはタスクの作成、分解、割り当て、進捗管理を担当します。
    複数のWorker Beeを統括し、効率的なタスク配分を行います。
    """

    def __init__(self, config: BeehiveConfig | None = None) -> None:
        """Queen Beeを初期化

        Args:
            config: Beehive設定オブジェクト。Noneの場合はデフォルト設定を使用

        Raises:
            BeehiveError: 初期化に失敗した場合
        """
        self.config = config or get_config()
        super().__init__("queen", self.config)

        # 設定から利用可能なBeeリストを取得
        self.available_bees: list[str] = self.config.available_bees.copy()
        self.task_assignment_strategy: str = self.config.task_assignment_strategy
        self.max_tasks_per_bee: int = self.config.max_tasks_per_bee

        self.logger.log_event(
            "initialization", "Queen Bee initialized - Ready for task management", "INFO"
        )
        self._validate_initial_state()

    def _validate_initial_state(self) -> None:
        """初期状態を検証

        Raises:
            WorkflowError: 初期状態が無効な場合
        """
        if not self.available_bees:
            raise WorkflowError("No available bees configured")

        if self.task_assignment_strategy not in ["balanced", "specialized", "priority"]:
            raise WorkflowError(
                f"Invalid task assignment strategy: {self.task_assignment_strategy}"
            )

        if self.max_tasks_per_bee <= 0:
            raise WorkflowError(f"Invalid max_tasks_per_bee: {self.max_tasks_per_bee}")

    def _validate_task_input(
        self,
        title: str,
        description: str,
        priority: str,
        estimated_hours: float | None,
        parent_task_id: str | int | None,
    ) -> None:
        """タスク入力値を検証

        Args:
            title: タスクタイトル
            description: タスク説明
            priority: 優先度
            estimated_hours: 推定作業時間
            parent_task_id: 親タスクID

        Raises:
            TaskValidationError: 入力値が無効な場合
        """
        if not title or not isinstance(title, str) or len(title.strip()) == 0:
            raise TaskValidationError("Task title cannot be empty")

        if len(title) > self.config.max_title_length:
            raise TaskValidationError(
                f"Task title too long: {len(title)} > {self.config.max_title_length}"
            )

        if not description or not isinstance(description, str) or len(description.strip()) == 0:
            raise TaskValidationError("Task description cannot be empty")

        if len(description) > self.config.max_description_length:
            raise TaskValidationError(
                f"Task description too long: {len(description)} > {self.config.max_description_length}"
            )

        valid_priorities = ["critical", "high", "medium", "low"]
        if priority not in valid_priorities:
            raise TaskValidationError(
                f"Invalid priority '{priority}'. Valid options: {valid_priorities}"
            )

        if estimated_hours is not None:
            if not isinstance(estimated_hours, int | float) or estimated_hours < 0:
                raise TaskValidationError(f"Invalid estimated_hours: {estimated_hours}")
            if estimated_hours > self.config.max_estimated_hours:
                raise TaskValidationError(
                    f"Estimated hours too high: {estimated_hours} > {self.config.max_estimated_hours}"
                )

        if parent_task_id is not None:
            if not isinstance(parent_task_id, int | str) or (
                isinstance(parent_task_id, int) and parent_task_id <= 0
            ):
                raise TaskValidationError(f"Invalid parent_task_id: {parent_task_id}")

    @error_handler
    def create_task(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        estimated_hours: float | None = None,
        parent_task_id: str | int | None = None,
    ) -> int:
        """新しいタスクを作成

        Args:
            title: タスクのタイトル
            description: タスクの詳細説明
            priority: タスクの優先度 (critical, high, medium, low)
            estimated_hours: 推定作業時間（時間単位）
            parent_task_id: 親タスクのID（サブタスクの場合）

        Returns:
            作成されたタスクのID

        Raises:
            TaskValidationError: タスクの入力値が無効な場合
            DatabaseConnectionError: データベース操作に失敗した場合
        """
        # 入力値検証
        self._validate_task_input(title, description, priority, estimated_hours, parent_task_id)

        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO tasks
                    (title, description, priority, estimated_hours, parent_task_id, created_by, assigned_to)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        title,
                        description,
                        priority,
                        estimated_hours,
                        parent_task_id,
                        self.bee_name,
                        self.bee_name,
                    ),
                )

                task_id = cursor.lastrowid
                if not task_id:
                    raise DatabaseConnectionError("Failed to create task: no ID returned")

                # アクティビティログ
                conn.execute(
                    """
                    INSERT INTO task_activity
                    (task_id, bee_name, activity_type, description)
                    VALUES (?, ?, ?, ?)
                """,
                    (task_id, self.bee_name, "created", f"Task created: {title}"),
                )

                conn.commit()

            self.logger.log_event(
                "task_created",
                f"Task created: {title}",
                "INFO",
                task_id=task_id,
                priority=priority,
                estimated_hours=estimated_hours,
            )
            return task_id

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to create task '{title}': {e}") from e

    @error_handler
    def decompose_task(self, task_id: str | int, subtasks: list[dict[str, Any]]) -> list[int]:
        """タスクをサブタスクに分解

        Args:
            task_id: 分解するタスクのID
            subtasks: サブタスクのリスト。各要素は'title'、'description'を含む辞書

        Returns:
            作成されたサブタスクIDのリスト

        Raises:
            TaskValidationError: タスクIDが無効またはサブタスクデータが無効な場合
            WorkflowError: タスク分解処理に失敗した場合
        """
        # 入力値検証
        if not isinstance(task_id, int | str) or (isinstance(task_id, int) and task_id <= 0):
            raise TaskValidationError(f"Invalid task_id: {task_id}")

        if not subtasks or not isinstance(subtasks, list):
            raise TaskValidationError("Subtasks must be a non-empty list")

        if len(subtasks) > self.config.max_subtasks_per_task:
            raise TaskValidationError(
                f"Too many subtasks: {len(subtasks)} > {self.config.max_subtasks_per_task}"
            )

        # 親タスクの存在確認
        parent_task = self.get_task_details(task_id)
        if not parent_task:
            raise TaskValidationError(f"Parent task {task_id} not found")

        # サブタスクデータ検証
        for i, subtask in enumerate(subtasks):
            if not isinstance(subtask, dict):
                raise TaskValidationError(f"Subtask {i} must be a dictionary")
            if "title" not in subtask or "description" not in subtask:
                raise TaskValidationError(
                    f"Subtask {i} missing required fields: title, description"
                )

        subtask_ids = []
        failed_subtasks = []

        try:
            for i, subtask in enumerate(subtasks):
                try:
                    subtask_id = self.create_task(
                        title=subtask["title"],
                        description=subtask["description"],
                        priority=subtask.get("priority", "medium"),
                        estimated_hours=subtask.get("estimated_hours"),
                        parent_task_id=task_id,
                    )
                    subtask_ids.append(subtask_id)
                except Exception as e:
                    failed_subtasks.append((i, str(e)))
                    self.logger.log_event(
                        "subtask_creation_failed",
                        f"Failed to create subtask {i}: {e}",
                        "ERROR",
                        parent_task_id=task_id,
                        subtask_index=i,
                        error=str(e),
                    )

            if failed_subtasks:
                raise WorkflowError(
                    f"Failed to create {len(failed_subtasks)} subtasks: {failed_subtasks}"
                )

            # 親タスクの状態を更新
            self.update_task_status(
                task_id, "in_progress", f"Decomposed into {len(subtasks)} subtasks"
            )
            self.log_activity(
                task_id,
                "decomposed",
                f"Created {len(subtasks)} subtasks",
                {"subtask_ids": subtask_ids},
            )

            self.logger.log_event(
                "task_decomposed",
                f"Task {task_id} decomposed into {len(subtasks)} subtasks",
                "INFO",
                task_id=task_id,
                subtask_count=len(subtasks),
                subtask_ids=subtask_ids,
            )
            return subtask_ids

        except Exception as e:
            raise WorkflowError(f"Task decomposition failed: {e}") from e

    @error_handler
    def assign_task_to_bee(
        self, task_id: str | int, target_bee: str, assignment_reason: str = ""
    ) -> bool:
        """指定されたBeeにタスクを割り当て

        Args:
            task_id: 割り当てるタスクのID
            target_bee: 割り当て先のBee名
            assignment_reason: 割り当て理由

        Returns:
            割り当てが成功した場合True

        Raises:
            TaskValidationError: タスクIDが無効な場合
            BeeNotFoundError: 指定されたBeeが存在しない場合
            WorkflowError: ワークロードが上限を超えている場合
        """
        # 入力値検証
        if not isinstance(task_id, int | str) or (isinstance(task_id, int) and task_id <= 0):
            raise TaskValidationError(f"Invalid task_id: {task_id}")

        if not target_bee or not isinstance(target_bee, str):
            raise BeeNotFoundError(f"Invalid target_bee: {target_bee}")

        if target_bee not in self.available_bees:
            raise BeeNotFoundError(f"Unknown bee: {target_bee}. Available: {self.available_bees}")

        # タスクの存在確認
        task_details = self.get_task_details(task_id)
        if not task_details:
            raise TaskValidationError(f"Task {task_id} not found")

        # Bee のワークロードをチェック
        bee_workload = self._get_bee_workload(target_bee)
        if bee_workload > self.config.max_workload_threshold:
            if self.config.strict_workload_enforcement:
                raise WorkflowError(f"{target_bee} workload too high: {bee_workload}%")
            else:
                self.logger.log_event(
                    "high_workload_warning",
                    f"{target_bee} has high workload: {bee_workload}%",
                    "WARNING",
                    bee_name=target_bee,
                    workload=bee_workload,
                )

        try:
            with self._get_db_connection() as conn:
                # タスクの割り当て
                conn.execute(
                    """
                    UPDATE tasks
                    SET assigned_to = ?, status = 'pending', updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                """,
                    (target_bee, task_id),
                )

                # 割り当て記録
                conn.execute(
                    """
                    INSERT INTO task_assignments
                    (task_id, assigned_to, assigned_by, assignment_type, notes)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (task_id, target_bee, self.bee_name, "primary", assignment_reason),
                )

                conn.commit()

        except Exception as e:
            raise DatabaseConnectionError(
                f"Failed to assign task {task_id} to {target_bee}: {e}"
            ) from e

        # Beeにメッセージで通知
        assignment_message = f"""新しいタスクが割り当てられました

タスク: {task_details["title"]}
説明: {task_details["description"]}
優先度: {task_details["priority"]}
推定時間: {task_details.get("estimated_hours", "N/A")} 時間

{assignment_reason}

詳細確認: task_id = {task_id}
"""

        self.send_message(
            target_bee,
            "task_update",
            f"新規タスク割り当て: {task_details['title']}",
            assignment_message,
            task_id,
            "high",
        )

        self.log_activity(
            task_id, "assigned", f"Assigned to {target_bee}", {"reason": assignment_reason}
        )

        self.logger.log_event(
            "task_assigned",
            f"Task {task_id} assigned to {target_bee}",
            "INFO",
            task_id=task_id,
            target_bee=target_bee,
            reason=assignment_reason,
        )
        return True

    @error_handler
    def auto_assign_tasks(self) -> int:
        """自動タスク割り当て（未割り当てタスクを適切なBeeに分配）

        Returns:
            割り当てが成功したタスク数

        Raises:
            WorkflowError: 自動割り当て処理に失敗した場合
        """
        try:
            unassigned_tasks = self._get_unassigned_tasks()
            assigned_count = 0
            failed_assignments = []

            for task in unassigned_tasks:
                try:
                    best_bee = self._select_best_bee_for_task(task)
                    if best_bee:
                        reason = f"Auto-assigned based on {self.task_assignment_strategy} strategy"
                        if self.assign_task_to_bee(task["task_id"], best_bee, reason):
                            assigned_count += 1
                    else:
                        failed_assignments.append(task["task_id"])
                        self.logger.log_event(
                            "assignment_failed",
                            f"No suitable bee found for task {task['task_id']}",
                            "WARNING",
                            task_id=task["task_id"],
                        )
                except Exception as e:
                    failed_assignments.append(task["task_id"])
                    self.logger.log_event(
                        "assignment_error",
                        f"Failed to assign task {task['task_id']}: {e}",
                        "ERROR",
                        task_id=task["task_id"],
                        error=str(e),
                    )

            self.logger.log_event(
                "auto_assignment_completed",
                f"Auto-assigned {assigned_count} tasks, {len(failed_assignments)} failed",
                "INFO",
                assigned_count=assigned_count,
                failed_count=len(failed_assignments),
            )
            return assigned_count

        except Exception as e:
            raise WorkflowError(f"Auto assignment process failed: {e}") from e

    @error_handler
    def _get_unassigned_tasks(self) -> list[dict[str, Any]]:
        """未割り当てタスクのリストを取得

        Returns:
            未割り当てタスクのリスト

        Raises:
            DatabaseConnectionError: データベースアクセスに失敗した場合
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM tasks
                    WHERE assigned_to IS NULL OR assigned_to = ?
                    AND status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                """,
                    (self.bee_name,),
                )
                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to get unassigned tasks: {e}") from e

    @error_handler
    def _select_best_bee_for_task(self, task: dict[str, Any]) -> str | None:
        """タスクに最適なBeeを選択

        Args:
            task: タスク情報を含む辞書

        Returns:
            最適なBee名、見つからない場合はNone

        Raises:
            TaskValidationError: タスクデータが無効な場合
        """
        if not isinstance(task, dict) or "task_id" not in task:
            raise TaskValidationError("Task data must be a dictionary with task_id")

        try:
            if self.task_assignment_strategy == "balanced":
                return self._get_least_loaded_bee()
            elif self.task_assignment_strategy == "specialized":
                return self._get_specialized_bee_for_task(task)
            elif self.task_assignment_strategy == "priority":
                if task.get("priority") == "critical":
                    return self._get_best_performer_bee()
                else:
                    return self._get_least_loaded_bee()
            else:
                # フォールバック戦略
                self.logger.log_event(
                    "unknown_strategy_fallback",
                    f"Unknown strategy {self.task_assignment_strategy}, using balanced",
                    "WARNING",
                )
                return self._get_least_loaded_bee()

        except Exception as e:
            self.logger.log_event(
                "bee_selection_failed",
                f"Failed to select bee: {e}",
                "ERROR",
                task_id=task.get("task_id"),
                error=str(e),
            )
            return None

    @error_handler
    def _get_least_loaded_bee(self) -> str | None:
        """最も負荷の少ないBeeを取得

        Returns:
            最も負荷の少ないBee名、利用可能なBeeがない場合はNone

        Raises:
            WorkflowError: ワークロード取得に失敗した場合
        """
        if not self.available_bees:
            self.logger.log_event(
                "no_available_bees", "No available bees for assignment", "WARNING"
            )
            return None

        try:
            workloads = {}
            for bee in self.available_bees:
                workloads[bee] = self._get_bee_workload(bee)

            if workloads:
                least_loaded = min(workloads, key=workloads.get)
                self.logger.log_event(
                    "least_loaded_selected",
                    f"Selected {least_loaded} with workload {workloads[least_loaded]}%",
                    "DEBUG",
                    selected_bee=least_loaded,
                    workload=workloads[least_loaded],
                )
                return least_loaded
            return None

        except Exception as e:
            raise WorkflowError(f"Failed to find least loaded bee: {e}") from e

    @error_handler
    def _get_specialized_bee_for_task(self, task: dict[str, Any]) -> str | None:
        """タスクの種類に基づいて専門Beeを選択

        Args:
            task: タスク情報を含む辞書

        Returns:
            専門Bee名、適切なBeeが見つからない場合は最も負荷の少ないBee

        Raises:
            TaskValidationError: タスクデータが無効な場合
        """
        if not task.get("title") or not task.get("description"):
            raise TaskValidationError("Task must have title and description for specialization")

        task_title = task["title"].lower()
        task_desc = task["description"].lower()
        task_text = task_title + " " + task_desc

        # Analyst関連キーワード
        analyst_keywords = [
            "analysis",
            "analyze",
            "metrics",
            "performance",
            "report",
            "assessment",
            "evaluate",
            "measure",
            "profile",
            "benchmark",
        ]
        if any(keyword in task_text for keyword in analyst_keywords):
            if "analyst" in self.available_bees:
                self.logger.log_event(
                    "specialized_assignment",
                    "Assigned to analyst based on keywords",
                    "DEBUG",
                    task_id=task.get("task_id"),
                    specialization="analyst",
                )
                return "analyst"

        # QA関連キーワード
        qa_keywords = ["test", "qa", "quality", "bug", "verify", "check", "validation", "review"]
        if any(keyword in task_text for keyword in qa_keywords):
            if "qa" in self.available_bees:
                self.logger.log_event(
                    "specialized_assignment",
                    "Assigned to QA based on keywords",
                    "DEBUG",
                    task_id=task.get("task_id"),
                    specialization="qa",
                )
                return "qa"

        # 開発関連キーワード
        dev_keywords = [
            "code",
            "implement",
            "develop",
            "build",
            "create",
            "fix",
            "refactor",
            "optimize",
        ]
        if any(keyword in task_text for keyword in dev_keywords):
            if "developer" in self.available_bees:
                self.logger.log_event(
                    "specialized_assignment",
                    "Assigned to developer based on keywords",
                    "DEBUG",
                    task_id=task.get("task_id"),
                    specialization="developer",
                )
                return "developer"

        # フォールバック: 最も負荷の少ないBee
        self.logger.log_event(
            "specialization_fallback",
            "No specialization found, using least loaded",
            "DEBUG",
            task_id=task.get("task_id"),
        )
        return self._get_least_loaded_bee()

    @error_handler
    def _get_best_performer_bee(self) -> str | None:
        """最も性能の高いBeeを取得

        Returns:
            最高性能のBee名、見つからない場合はNone

        Raises:
            DatabaseConnectionError: データベースアクセスに失敗した場合
        """
        if not self.available_bees:
            return None

        try:
            with self._get_db_connection() as conn:
                # 利用可能なBeeの数に応じてプレースホルダーを動的に生成
                placeholders = ", ".join(["?"] * len(self.available_bees))
                cursor = conn.execute(
                    f"""
                    SELECT bee_name, performance_score FROM bee_states
                    WHERE bee_name IN ({placeholders})
                    ORDER BY performance_score DESC
                    LIMIT 1
                """,
                    tuple(self.available_bees),
                )
                row = cursor.fetchone()

                if row:
                    self.logger.log_event(
                        "best_performer_selected",
                        f"Selected {row[0]} with performance score {row[1]}",
                        "DEBUG",
                        selected_bee=row[0],
                        performance_score=row[1],
                    )
                    return row[0]
                else:
                    # パフォーマンススコアがない場合は最も負荷の少ないBeeを使用
                    return self._get_least_loaded_bee()

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to get best performer bee: {e}") from e

    @error_handler
    def _get_bee_workload(self, bee_name: str) -> float:
        """指定されたBeeのワークロードを取得

        Args:
            bee_name: ワークロードを取得するBeeの名前

        Returns:
            ワークロードスコア（0.0-100.0）

        Raises:
            BeeNotFoundError: Bee名が無効な場合
            DatabaseConnectionError: データベースアクセスに失敗した場合
        """
        if not bee_name or not isinstance(bee_name, str):
            raise BeeNotFoundError(f"Invalid bee_name: {bee_name}")

        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT workload_score FROM bee_states WHERE bee_name = ?
                """,
                    (bee_name,),
                )
                row = cursor.fetchone()
                return row[0] if row else 0.0

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to get workload for {bee_name}: {e}") from e

    @error_handler
    def review_task_progress(self) -> dict[str, Any]:
        """タスクの進捗をレビュー

        Returns:
            進捗レビューレポートを含む辞書

        Raises:
            DatabaseConnectionError: データベースアクセスに失敗した場合
        """
        try:
            with self._get_db_connection() as conn:
                # 全体の進捗統計
                cursor = conn.execute(
                    """
                    SELECT
                        status,
                        COUNT(*) as count,
                        AVG(CAST(actual_hours as REAL)) as avg_hours
                    FROM tasks
                    GROUP BY status
                """
                )
                status_stats = [dict(row) for row in cursor.fetchall()]

                # Bee別の作業状況
                cursor = conn.execute(
                    """
                    SELECT
                        assigned_to,
                        COUNT(*) as active_tasks,
                        AVG(workload_score) as avg_workload
                    FROM tasks t
                    LEFT JOIN bee_states bs ON t.assigned_to = bs.bee_name
                    WHERE t.status IN ('pending', 'in_progress')
                    GROUP BY assigned_to
                """
                )
                bee_stats = [dict(row) for row in cursor.fetchall()]

                # 遅延タスク
                cursor = conn.execute(
                    """
                    SELECT task_id, title, assigned_to, due_date
                    FROM tasks
                    WHERE due_date < CURRENT_TIMESTAMP
                    AND status NOT IN ('completed', 'cancelled')
                """
                )
                overdue_tasks = [dict(row) for row in cursor.fetchall()]

            progress_report = {
                "status_statistics": status_stats,
                "bee_statistics": bee_stats,
                "overdue_tasks": overdue_tasks,
                "review_timestamp": datetime.now().isoformat(),
                "total_overdue": len(overdue_tasks),
            }

            self.logger.log_event(
                "progress_review_completed",
                f"Progress review completed: {len(overdue_tasks)} overdue tasks",
                "INFO",
                overdue_count=len(overdue_tasks),
                total_bees=len(bee_stats),
            )
            return progress_report

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to review task progress: {e}") from e

    @error_handler
    def _process_message(self, message: dict[str, Any]) -> None:
        """Queen Bee固有のメッセージ処理

        Args:
            message: 処理するメッセージデータ

        Raises:
            TaskValidationError: メッセージデータが無効な場合
        """
        if not isinstance(message, dict) or "message_type" not in message:
            raise TaskValidationError("Invalid message format")

        message_type = message["message_type"]
        from_bee = message["from_bee"]
        task_id = message.get("task_id")

        self.logger.log_event(
            "message_processing",
            f"Processing {message_type} from {from_bee}",
            "INFO",
            message_type=message_type,
            from_bee=from_bee,
            task_id=task_id,
        )

        try:
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

        except Exception as e:
            self.logger.log_event(
                "message_processing_error",
                f"Failed to process message: {e}",
                "ERROR",
                message_id=message.get("message_id"),
                error=str(e),
            )
            raise

    @error_handler
    def _handle_progress_report(self, message: dict[str, Any]) -> None:
        """進捗報告の処理

        Args:
            message: 進捗報告メッセージ

        Raises:
            TaskValidationError: メッセージデータが無効な場合
        """
        task_id = message.get("task_id")
        from_bee = message.get("from_bee")
        content = message.get("content", "")

        if not from_bee:
            raise TaskValidationError("Progress report missing from_bee")

        try:
            if task_id:
                # タスクの進捗を記録
                self.log_activity(
                    task_id, "progress_report", f"Progress report from {from_bee}: {content}"
                )

                # 必要に応じて次のアクションを決定
                task_details = self.get_task_details(task_id)
                if task_details and task_details.get("status") == "completed":
                    self._handle_task_completion(task_id, from_bee)

            # メッセージを処理済みにマーク
            if "message_id" in message:
                self.mark_message_processed(message["message_id"])

            self.logger.log_event(
                "progress_report_handled",
                f"Progress report processed from {from_bee}",
                "INFO",
                from_bee=from_bee,
                task_id=task_id,
            )

        except Exception as e:
            self.logger.log_event(
                "progress_report_error",
                f"Failed to handle progress report: {e}",
                "ERROR",
                from_bee=from_bee,
                task_id=task_id,
                error=str(e),
            )
            raise

    @error_handler
    def _handle_task_completion(self, task_id: str | int, completed_by: str) -> None:
        """タスク完了時の処理

        Args:
            task_id: 完了したタスクのID
            completed_by: タスクを完了したBee名

        Raises:
            TaskValidationError: タスクIDが無効な場合
            BeeNotFoundError: 完了者が無効な場合
        """
        if not isinstance(task_id, int | str) or (isinstance(task_id, int) and task_id <= 0):
            raise TaskValidationError(f"Invalid task_id: {task_id}")

        if not completed_by or completed_by not in self.available_bees:
            raise BeeNotFoundError(f"Invalid completed_by: {completed_by}")

        try:
            self.logger.log_event(
                "task_completion_processing",
                f"Task {task_id} completed by {completed_by}",
                "INFO",
                task_id=task_id,
                completed_by=completed_by,
            )

            # 子タスクがある場合、親タスクの状態をチェック
            parent_task = self._get_parent_task(task_id)
            if parent_task:
                if self._all_subtasks_completed(parent_task["task_id"]):
                    self.update_task_status(
                        parent_task["task_id"], "completed", "All subtasks completed"
                    )
                    self.logger.log_event(
                        "parent_task_completed",
                        f"Parent task {parent_task['task_id']} auto-completed",
                        "INFO",
                        parent_task_id=parent_task["task_id"],
                    )

            # 新しいタスクの自動割り当てを試みる
            try:
                assigned_count = self.auto_assign_tasks()
                if assigned_count > 0:
                    self.logger.log_event(
                        "post_completion_assignment",
                        f"Auto-assigned {assigned_count} new tasks",
                        "INFO",
                        assigned_count=assigned_count,
                    )
            except Exception as e:
                # 自動割り当ての失敗はタスク完了処理を阻害しない
                self.logger.log_event(
                    "post_completion_assignment_failed",
                    f"Auto-assignment failed: {e}",
                    "WARNING",
                    error=str(e),
                )

        except Exception as e:
            self.logger.log_event(
                "task_completion_error",
                f"Failed to handle task completion: {e}",
                "ERROR",
                task_id=task_id,
                completed_by=completed_by,
                error=str(e),
            )
            raise

    @error_handler
    def _get_parent_task(self, task_id: str | int) -> dict[str, Any] | None:
        """親タスクを取得

        Args:
            task_id: 子タスクのID

        Returns:
            親タスクの辞書、存在しない場合はNone

        Raises:
            TaskValidationError: タスクIDが無効な場合
            DatabaseConnectionError: データベースアクセスに失敗した場合
        """
        if not isinstance(task_id, int | str) or (isinstance(task_id, int) and task_id <= 0):
            raise TaskValidationError(f"Invalid task_id: {task_id}")

        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT p.* FROM tasks p
                    JOIN tasks c ON p.task_id = c.parent_task_id
                    WHERE c.task_id = ?
                """,
                    (task_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to get parent task for {task_id}: {e}") from e

    @error_handler
    def _all_subtasks_completed(self, parent_task_id: str | int) -> bool:
        """すべてのサブタスクが完了しているかチェック

        Args:
            parent_task_id: 親タスクのID

        Returns:
            すべてのサブタスクが完了している場合True

        Raises:
            TaskValidationError: 親タスクIDが無効な場合
            DatabaseConnectionError: データベースアクセスに失敗した場合
        """
        if not isinstance(parent_task_id, int | str) or (
            isinstance(parent_task_id, int) and parent_task_id <= 0
        ):
            raise TaskValidationError(f"Invalid parent_task_id: {parent_task_id}")

        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) as total,
                           COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
                    FROM tasks WHERE parent_task_id = ?
                """,
                    (parent_task_id,),
                )
                row = cursor.fetchone()

                if not row:
                    return False

                total = row["total"]
                completed = row["completed"]

                self.logger.log_event(
                    "subtask_completion_check",
                    f"Subtasks: {completed}/{total} completed",
                    "DEBUG",
                    parent_task_id=parent_task_id,
                    total=total,
                    completed=completed,
                )

                return total > 0 and total == completed

        except Exception as e:
            raise DatabaseConnectionError(
                f"Failed to check subtask completion for {parent_task_id}: {e}"
            ) from e

    @error_handler
    def _handle_resource_request(self, message: dict[str, Any]) -> None:
        """リソース要求の処理

        Args:
            message: リソース要求メッセージ

        Raises:
            TaskValidationError: メッセージデータが無効な場合
        """
        from_bee = message.get("from_bee")
        if not from_bee:
            raise TaskValidationError("Resource request missing from_bee")

        try:
            # 簡易実装：要求を承認し、必要に応じて他のBeeに協力を要請
            response = "Resource request acknowledged. Processing your request."
            self.send_message(
                from_bee, "response", f"Re: {message.get('subject', 'Resource Request')}", response
            )

            if "message_id" in message:
                self.mark_message_processed(message["message_id"])

            self.logger.log_event(
                "resource_request_handled",
                f"Resource request processed from {from_bee}",
                "INFO",
                from_bee=from_bee,
                request_type=message.get("subject"),
            )

        except Exception as e:
            self.logger.log_event(
                "resource_request_error",
                f"Failed to handle resource request: {e}",
                "ERROR",
                from_bee=from_bee,
                error=str(e),
            )
            raise

    @error_handler
    def _handle_consultation(self, message: dict[str, Any]) -> None:
        """相談の処理

        Args:
            message: 相談メッセージ

        Raises:
            TaskValidationError: メッセージデータが無効な場合
        """
        from_bee = message.get("from_bee")
        if not from_bee:
            raise TaskValidationError("Consultation missing from_bee")

        task_id = message.get("task_id")

        try:
            # 基本的な指導的回答
            response = f"Thank you for consulting me. Please proceed with your best judgment. I trust your expertise as {from_bee}."

            if task_id:
                task_details = self.get_task_details(task_id)
                if task_details:
                    response += f"\n\nFor task '{task_details.get('title', 'Unknown')}', focus on the core requirements and maintain quality."

            self.send_message(
                from_bee, "response", f"Re: {message.get('subject', 'Consultation')}", response
            )

            if "message_id" in message:
                self.mark_message_processed(message["message_id"])

            self.logger.log_event(
                "consultation_handled",
                f"Consultation processed from {from_bee}",
                "INFO",
                from_bee=from_bee,
                task_id=task_id,
            )

        except Exception as e:
            self.logger.log_event(
                "consultation_error",
                f"Failed to handle consultation: {e}",
                "ERROR",
                from_bee=from_bee,
                task_id=task_id,
                error=str(e),
            )
            raise
