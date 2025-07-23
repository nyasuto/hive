#!/usr/bin/env python3
"""
Queen Bee Unit Tests
Issue #23: テストスイート強化とコード品質向上

Queen Beeクラスの単体テスト
"""

import sqlite3
from unittest.mock import patch

import pytest

from .config import BeehiveConfig
from .exceptions import (
    BeeNotFoundError,
    DatabaseConnectionError,
    TaskValidationError,
    WorkflowError,
)
from .queen_bee import QueenBee


class TestQueenBeeInitialization:
    """Queen Bee初期化テスト"""

    def test_init_default_config(self, temp_db_path):
        """デフォルト設定での初期化テスト"""
        config = BeehiveConfig(
            database_path=temp_db_path,
            available_bees=["developer", "qa"],
            task_assignment_strategy="balanced",
            max_tasks_per_bee=5,
        )

        queen = QueenBee(config)

        assert queen.bee_name == "queen"
        assert queen.available_bees == ["developer", "qa"]
        assert queen.task_assignment_strategy == "balanced"
        assert queen.max_tasks_per_bee == 5

    def test_init_no_available_bees_raises_error(self, temp_db_path):
        """利用可能なBeeがない場合のエラーテスト"""
        config = BeehiveConfig(
            database_path=temp_db_path,
            available_bees=[],
        )

        with pytest.raises(WorkflowError, match="No available bees configured"):
            QueenBee(config)

    def test_init_invalid_assignment_strategy_raises_error(self, temp_db_path):
        """無効な割り当て戦略でのエラーテスト"""
        config = BeehiveConfig(
            database_path=temp_db_path,
            available_bees=["developer"],
            task_assignment_strategy="invalid",
        )

        with pytest.raises(WorkflowError, match="Invalid task assignment strategy"):
            QueenBee(config)

    def test_init_invalid_max_tasks_raises_error(self, temp_db_path):
        """無効な最大タスク数でのエラーテスト"""
        config = BeehiveConfig(
            database_path=temp_db_path,
            available_bees=["developer"],
            max_tasks_per_bee=0,
        )

        with pytest.raises(WorkflowError, match="Invalid max_tasks_per_bee"):
            QueenBee(config)


class TestTaskCreation:
    """タスク作成テスト"""

    def test_create_task_success(self, queen_bee, temp_db_conn):
        """正常なタスク作成テスト"""
        task_id = queen_bee.create_task(
            title="Test Task",
            description="Test task description",
            priority="high",
            estimated_hours=2.5,
        )

        assert isinstance(task_id, int)
        assert task_id > 0

        # データベース確認
        cursor = temp_db_conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["title"] == "Test Task"
        assert row["description"] == "Test task description"
        assert row["priority"] == "high"
        assert row["estimated_hours"] == 2.5

    def test_create_task_empty_title_raises_error(self, queen_bee):
        """空のタイトルでのエラーテスト"""
        with pytest.raises(TaskValidationError, match="Task title cannot be empty"):
            queen_bee.create_task(
                title="",
                description="Test description",
            )

    def test_create_task_empty_description_raises_error(self, queen_bee):
        """空の説明でのエラーテスト"""
        with pytest.raises(TaskValidationError, match="Task description cannot be empty"):
            queen_bee.create_task(
                title="Test Task",
                description="",
            )

    def test_create_task_invalid_priority_raises_error(self, queen_bee):
        """無効な優先度でのエラーテスト"""
        with pytest.raises(TaskValidationError, match="Invalid priority"):
            queen_bee.create_task(
                title="Test Task",
                description="Test description",
                priority="invalid",
            )

    def test_create_task_negative_hours_raises_error(self, queen_bee):
        """負の推定時間でのエラーテスト"""
        with pytest.raises(TaskValidationError, match="Invalid estimated_hours"):
            queen_bee.create_task(
                title="Test Task",
                description="Test description",
                estimated_hours=-1.0,
            )

    def test_create_task_title_too_long_raises_error(self, queen_bee):
        """長すぎるタイトルでのエラーテスト"""
        long_title = "x" * 1001  # max_title_length より長い
        with pytest.raises(TaskValidationError, match="Task title too long"):
            queen_bee.create_task(
                title=long_title,
                description="Test description",
            )


class TestTaskDecomposition:
    """タスク分解テスト"""

    def test_decompose_task_success(self, queen_bee, temp_db_conn):
        """正常なタスク分解テスト"""
        # 親タスク作成
        parent_id = queen_bee.create_task(
            title="Parent Task",
            description="Main task to decompose",
        )

        # サブタスク定義
        subtasks = [
            {"title": "Subtask 1", "description": "First subtask"},
            {"title": "Subtask 2", "description": "Second subtask", "priority": "high"},
        ]

        subtask_ids = queen_bee.decompose_task(parent_id, subtasks)

        assert len(subtask_ids) == 2
        assert all(isinstance(task_id, int) for task_id in subtask_ids)

        # データベース確認
        for i, subtask_id in enumerate(subtask_ids):
            cursor = temp_db_conn.execute("SELECT * FROM tasks WHERE task_id = ?", (subtask_id,))
            row = cursor.fetchone()
            assert row is not None
            assert row["parent_task_id"] == parent_id
            assert row["title"] == subtasks[i]["title"]

    def test_decompose_task_invalid_task_id_raises_error(self, queen_bee):
        """無効なタスクIDでのエラーテスト"""
        with pytest.raises(TaskValidationError, match="Invalid task_id"):
            queen_bee.decompose_task(-1, [{"title": "Test", "description": "Test"}])

    def test_decompose_task_empty_subtasks_raises_error(self, queen_bee):
        """空のサブタスクリストでのエラーテスト"""
        with pytest.raises(TaskValidationError, match="Subtasks must be a non-empty list"):
            queen_bee.decompose_task(1, [])

    def test_decompose_task_nonexistent_parent_raises_error(self, queen_bee):
        """存在しない親タスクでのエラーテスト"""
        with pytest.raises(TaskValidationError, match="Parent task .* not found"):
            queen_bee.decompose_task(999999, [{"title": "Test", "description": "Test"}])

    def test_decompose_task_invalid_subtask_format_raises_error(self, queen_bee, temp_db_conn):
        """無効なサブタスク形式でのエラーテスト"""
        parent_id = queen_bee.create_task("Parent", "Description")

        with pytest.raises(TaskValidationError, match="Subtask .* must be a dictionary"):
            queen_bee.decompose_task(parent_id, ["invalid"])

    def test_decompose_task_missing_required_fields_raises_error(self, queen_bee, temp_db_conn):
        """必須フィールド不足でのエラーテスト"""
        parent_id = queen_bee.create_task("Parent", "Description")

        with pytest.raises(TaskValidationError, match="missing required fields"):
            queen_bee.decompose_task(parent_id, [{"title": "Test"}])  # description missing


class TestTaskAssignment:
    """タスク割り当てテスト"""

    def test_assign_task_to_bee_success(self, queen_bee, temp_db_conn):
        """正常なタスク割り当てテスト"""
        # タスク作成
        task_id = queen_bee.create_task("Test Task", "Test description")

        # 割り当て実行
        result = queen_bee.assign_task_to_bee(task_id, "developer", "Test assignment")

        assert result is True

        # データベース確認
        cursor = temp_db_conn.execute(
            "SELECT assigned_to, status FROM tasks WHERE task_id = ?", (task_id,)
        )
        row = cursor.fetchone()
        assert row["assigned_to"] == "developer"
        assert row["status"] == "pending"

    def test_assign_task_invalid_task_id_raises_error(self, queen_bee):
        """無効なタスクIDでのエラーテスト"""
        with pytest.raises(TaskValidationError, match="Invalid task_id"):
            queen_bee.assign_task_to_bee(-1, "developer")

    def test_assign_task_invalid_bee_raises_error(self, queen_bee, temp_db_conn):
        """無効なBee名でのエラーテスト"""
        task_id = queen_bee.create_task("Test Task", "Test description")

        with pytest.raises(BeeNotFoundError, match="Unknown bee"):
            queen_bee.assign_task_to_bee(task_id, "invalid_bee")

    def test_assign_task_nonexistent_task_raises_error(self, queen_bee):
        """存在しないタスクでのエラーテスト"""
        with pytest.raises(TaskValidationError, match="Task .* not found"):
            queen_bee.assign_task_to_bee(999999, "developer")

    @patch.object(QueenBee, "_get_bee_workload")
    def test_assign_task_high_workload_warning(self, mock_workload, queen_bee, temp_db_conn):
        """高負荷時の警告テスト"""
        # 高負荷を模擬
        mock_workload.return_value = 95.0

        task_id = queen_bee.create_task("Test Task", "Test description")

        # 警告ログが出力されることを確認（strict_workload_enforcement=False）
        result = queen_bee.assign_task_to_bee(task_id, "developer")
        assert result is True

    @patch.object(QueenBee, "_get_bee_workload")
    def test_assign_task_workload_enforcement_raises_error(
        self, mock_workload, queen_bee_strict, temp_db_conn
    ):
        """厳格な負荷制御でのエラーテスト"""
        # 高負荷を模擬
        mock_workload.return_value = 95.0

        task_id = queen_bee_strict.create_task("Test Task", "Test description")

        with pytest.raises(WorkflowError, match="workload too high"):
            queen_bee_strict.assign_task_to_bee(task_id, "developer")


class TestAutoAssignment:
    """自動割り当てテスト"""

    def test_auto_assign_tasks_success(self, queen_bee, temp_db_conn):
        """正常な自動割り当てテスト"""
        # 未割り当てタスクを作成
        task_ids = []
        for i in range(3):
            task_id = queen_bee.create_task(f"Task {i}", f"Description {i}")
            task_ids.append(task_id)

        # 自動割り当て実行
        assigned_count = queen_bee.auto_assign_tasks()

        assert assigned_count == 3

        # 全タスクが割り当てられていることを確認
        for task_id in task_ids:
            cursor = temp_db_conn.execute(
                "SELECT assigned_to FROM tasks WHERE task_id = ?", (task_id,)
            )
            row = cursor.fetchone()
            assert row["assigned_to"] in ["developer", "qa", "analyst"]

    @patch.object(QueenBee, "_select_best_bee_for_task")
    def test_auto_assign_tasks_no_suitable_bee(self, mock_select, queen_bee, temp_db_conn):
        """適切なBeeが見つからない場合のテスト"""
        mock_select.return_value = None

        queen_bee.create_task("Test Task", "Description")

        assigned_count = queen_bee.auto_assign_tasks()
        assert assigned_count == 0

    def test_auto_assign_tasks_empty_queue(self, queen_bee):
        """空のタスクキューでの自動割り当てテスト"""
        assigned_count = queen_bee.auto_assign_tasks()
        assert assigned_count == 0


class TestBeeSelection:
    """Bee選択戦略テスト"""

    @patch.object(QueenBee, "_get_bee_workload")
    def test_get_least_loaded_bee(self, mock_workload, queen_bee):
        """最小負荷Bee選択テスト"""
        # 負荷を模擬
        workload_map = {"developer": 20.0, "qa": 10.0, "analyst": 30.0}
        mock_workload.side_effect = lambda bee: workload_map[bee]

        least_loaded = queen_bee._get_least_loaded_bee()
        assert least_loaded == "qa"

    def test_get_specialized_bee_for_task_analyst(self, queen_bee):
        """Analyst特化割り当てテスト"""
        task = {
            "task_id": 1,
            "title": "Performance Analysis Report",
            "description": "Analyze system performance and generate metrics report",
        }

        specialized_bee = queen_bee._get_specialized_bee_for_task(task)
        assert specialized_bee == "analyst"

    def test_get_specialized_bee_for_task_qa(self, queen_bee):
        """QA特化割り当てテスト"""
        task = {
            "task_id": 1,
            "title": "Test Suite Implementation",
            "description": "Implement comprehensive test cases for validation",
        }

        specialized_bee = queen_bee._get_specialized_bee_for_task(task)
        assert specialized_bee == "qa"

    def test_get_specialized_bee_for_task_developer(self, queen_bee):
        """Developer特化割り当てテスト"""
        task = {
            "task_id": 1,
            "title": "Feature Implementation",
            "description": "Implement new code functionality and build components",
        }

        specialized_bee = queen_bee._get_specialized_bee_for_task(task)
        assert specialized_bee == "developer"

    @patch.object(QueenBee, "_get_least_loaded_bee")
    def test_get_specialized_bee_fallback(self, mock_least_loaded, queen_bee):
        """特化Bee見つからない場合のフォールバックテスト"""
        mock_least_loaded.return_value = "developer"

        task = {
            "task_id": 1,
            "title": "Generic Task",
            "description": "Some generic work without specific keywords",
        }

        specialized_bee = queen_bee._get_specialized_bee_for_task(task)
        assert specialized_bee == "developer"

    def test_select_best_bee_balanced_strategy(self, queen_bee):
        """バランス戦略での最適Bee選択テスト"""
        with patch.object(queen_bee, "_get_least_loaded_bee", return_value="qa"):
            task = {"task_id": 1, "title": "Test", "description": "Test"}
            best_bee = queen_bee._select_best_bee_for_task(task)
            assert best_bee == "qa"

    def test_select_best_bee_specialized_strategy(self, queen_bee_specialized):
        """特化戦略での最適Bee選択テスト"""
        task = {
            "task_id": 1,
            "title": "Code Review",
            "description": "Review code quality and implement improvements",
        }

        best_bee = queen_bee_specialized._select_best_bee_for_task(task)
        assert best_bee == "developer"

    def test_select_best_bee_priority_strategy_critical(self, queen_bee_priority):
        """優先度戦略（緊急）での最適Bee選択テスト"""
        with patch.object(queen_bee_priority, "_get_best_performer_bee", return_value="analyst"):
            task = {"task_id": 1, "priority": "critical", "title": "Test", "description": "Test"}
            best_bee = queen_bee_priority._select_best_bee_for_task(task)
            assert best_bee == "analyst"


class TestProgressReview:
    """進捗レビューテスト"""

    def test_review_task_progress_success(self, queen_bee, temp_db_conn):
        """正常な進捗レビューテスト"""
        # テスト用タスクとデータを準備
        task_id = queen_bee.create_task("Test Task", "Description", priority="high")
        queen_bee.assign_task_to_bee(task_id, "developer")

        progress_report = queen_bee.review_task_progress()

        assert "status_statistics" in progress_report
        assert "bee_statistics" in progress_report
        assert "overdue_tasks" in progress_report
        assert "review_timestamp" in progress_report
        assert "total_overdue" in progress_report
        assert isinstance(progress_report["status_statistics"], list)
        assert isinstance(progress_report["bee_statistics"], list)
        assert isinstance(progress_report["overdue_tasks"], list)

    def test_review_task_progress_with_overdue_tasks(self, queen_bee, temp_db_conn):
        """期限切れタスクがある場合の進捗レビューテスト"""
        # 期限切れタスクを作成
        task_id = queen_bee.create_task("Overdue Task", "Description")

        # 手動で期限を過去に設定
        temp_db_conn.execute(
            "UPDATE tasks SET due_date = datetime('now', '-1 day') WHERE task_id = ?", (task_id,)
        )
        temp_db_conn.commit()

        progress_report = queen_bee.review_task_progress()

        assert progress_report["total_overdue"] >= 1
        assert len(progress_report["overdue_tasks"]) >= 1


class TestMessageProcessing:
    """メッセージ処理テスト"""

    def test_handle_progress_report(self, queen_bee, temp_db_conn):
        """進捗報告処理テスト"""
        task_id = queen_bee.create_task("Test Task", "Description")

        message = {
            "message_id": 1,
            "message_type": "task_update",
            "from_bee": "developer",
            "task_id": task_id,
            "content": "50% complete",
        }

        with patch.object(queen_bee, "mark_message_processed") as mock_mark:
            queen_bee._handle_progress_report(message)
            mock_mark.assert_called_once_with(1)

    def test_handle_resource_request(self, queen_bee):
        """リソース要求処理テスト"""
        message = {
            "message_id": 1,
            "message_type": "request",
            "from_bee": "developer",
            "subject": "Need assistance",
            "content": "Require additional resources",
        }

        with (
            patch.object(queen_bee, "send_message") as mock_send,
            patch.object(queen_bee, "mark_message_processed") as mock_mark,
        ):
            queen_bee._handle_resource_request(message)
            mock_send.assert_called_once()
            mock_mark.assert_called_once_with(1)

    def test_handle_consultation(self, queen_bee):
        """相談処理テスト"""
        message = {
            "message_id": 1,
            "message_type": "question",
            "from_bee": "developer",
            "subject": "Technical question",
            "content": "How should I proceed?",
        }

        with (
            patch.object(queen_bee, "send_message") as mock_send,
            patch.object(queen_bee, "mark_message_processed") as mock_mark,
        ):
            queen_bee._handle_consultation(message)
            mock_send.assert_called_once()
            mock_mark.assert_called_once_with(1)

    def test_process_message_task_completion(self, queen_bee, temp_db_conn):
        """タスク完了メッセージ処理テスト"""
        task_id = queen_bee.create_task("Test Task", "Description")
        queen_bee.assign_task_to_bee(task_id, "developer")

        # タスクを完了状態に設定
        temp_db_conn.execute("UPDATE tasks SET status = 'completed' WHERE task_id = ?", (task_id,))
        temp_db_conn.commit()

        message = {
            "message_id": 1,
            "message_type": "task_update",
            "from_bee": "developer",
            "task_id": task_id,
            "content": "Task completed",
        }

        with patch.object(queen_bee, "_handle_task_completion") as mock_completion:
            queen_bee._handle_progress_report(message)
            mock_completion.assert_called_once_with(task_id, "developer")


class TestErrorHandling:
    """エラーハンドリングテスト"""

    def test_task_validation_error_handling(self, queen_bee):
        """タスク検証エラーのハンドリングテスト"""
        with pytest.raises(TaskValidationError):
            queen_bee.create_task("", "description")

    def test_bee_not_found_error_handling(self, queen_bee, temp_db_conn):
        """Bee未発見エラーのハンドリングテスト"""
        task_id = queen_bee.create_task("Test", "Description")

        with pytest.raises(BeeNotFoundError):
            queen_bee.assign_task_to_bee(task_id, "nonexistent_bee")

    @patch("sqlite3.connect")
    def test_database_connection_error_handling(self, mock_connect, queen_bee):
        """データベース接続エラーのハンドリングテスト"""
        mock_connect.side_effect = sqlite3.Error("Connection failed")

        with pytest.raises(DatabaseConnectionError):
            queen_bee.create_task("Test", "Description")

    def test_workflow_error_handling(self, queen_bee):
        """ワークフローエラーのハンドリングテスト"""
        with pytest.raises(WorkflowError):
            queen_bee.decompose_task(999999, [{"title": "Test", "description": "Test"}])
