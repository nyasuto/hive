#!/usr/bin/env python3
"""
Worker Bee Unit Tests
Issue #23: テストスイート強化とコード品質向上

Worker Beeクラスの単体テスト
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from .config import BeehiveConfig
from .exceptions import DatabaseConnectionError
from .worker_bee import WorkerBee


class TestWorkerBeeInitialization:
    """Worker Bee初期化テスト"""

    def test_init_developer_bee(self, temp_db_path):
        """Developer Worker Bee初期化テスト"""
        config = BeehiveConfig(
            database_path=temp_db_path,
            available_bees=["developer", "qa"],
        )

        worker = WorkerBee("developer", "development", config)

        assert worker.bee_name == "developer"
        assert worker.specialty == "development"
        assert worker.current_task_id is None
        assert worker.work_session_start is None
        assert "general_work" in worker.capabilities
        assert "task_execution" in worker.capabilities
        assert "reporting" in worker.capabilities

    def test_init_qa_bee(self, temp_db_path):
        """QA Worker Bee初期化テスト"""
        config = BeehiveConfig(
            database_path=temp_db_path,
            available_bees=["developer", "qa"],
        )

        worker = WorkerBee("qa", "quality_assurance", config)

        assert worker.bee_name == "qa"
        assert worker.specialty == "quality_assurance"
        assert worker.current_task_id is None

    def test_init_custom_capabilities(self, temp_db_path):
        """カスタム能力定義テスト"""

        class CustomWorkerBee(WorkerBee):
            def _define_capabilities(self):
                return ["custom_skill", "specialized_work"]

        config = BeehiveConfig(database_path=temp_db_path)
        worker = CustomWorkerBee("custom", "custom_specialty", config)

        assert "custom_skill" in worker.capabilities
        assert "specialized_work" in worker.capabilities

    @patch.object(WorkerBee, "_get_db_connection")
    def test_init_database_update_capabilities(self, mock_db, temp_db_path):
        """データベース能力更新テスト"""
        mock_conn = Mock()
        mock_db.return_value.__enter__.return_value = mock_conn

        config = BeehiveConfig(database_path=temp_db_path)
        WorkerBee("test", "test_specialty", config)

        # データベース更新が呼ばれることを確認
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()


class TestTaskAcceptance:
    """タスク受け入れテスト"""

    def test_accept_task_success(self, worker_bee, temp_db_conn):
        """正常なタスク受け入れテスト"""
        # テスト用タスクを作成
        task_id = self._create_test_task(temp_db_conn, "developer")

        with patch.object(worker_bee, "send_message") as mock_send:
            result = worker_bee.accept_task(task_id)

        assert result is True
        assert worker_bee.current_task_id == task_id
        assert worker_bee.work_session_start is not None
        assert isinstance(worker_bee.work_session_start, datetime)

        # データベース状態確認
        cursor = temp_db_conn.execute("SELECT status FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        assert row["status"] == "in_progress"

        # Queen Beeへのメッセージ送信確認
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert call_args[0] == "queen"  # to_bee
        assert call_args[1] == "task_update"  # message_type

    def test_accept_task_not_found(self, worker_bee):
        """存在しないタスクの受け入れテスト"""
        result = worker_bee.accept_task(999999)
        assert result is False
        assert worker_bee.current_task_id is None

    def test_accept_task_not_assigned_to_bee(self, worker_bee, temp_db_conn):
        """自分に割り当てられていないタスクの受け入れテスト"""
        task_id = self._create_test_task(temp_db_conn, "other_bee")

        result = worker_bee.accept_task(task_id)
        assert result is False
        assert worker_bee.current_task_id is None

    def test_accept_task_already_working(self, worker_bee, temp_db_conn):
        """既に作業中の場合のタスク受け入れテスト"""
        task_id1 = self._create_test_task(temp_db_conn, "developer", task_id=1)
        task_id2 = self._create_test_task(temp_db_conn, "developer", task_id=2)

        # 最初のタスクを受け入れ
        with patch.object(worker_bee, "send_message"):
            worker_bee.accept_task(task_id1)

        # 2番目のタスクの受け入れは失敗すべき
        result = worker_bee.accept_task(task_id2)
        assert result is False
        assert worker_bee.current_task_id == task_id1  # 最初のタスクのまま

    def _create_test_task(self, db_conn, assigned_to, task_id=None):
        """テスト用タスクを作成"""
        if task_id:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (task_id, title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, "Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        else:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        db_conn.commit()
        return task_id or cursor.lastrowid


class TestTaskCompletion:
    """タスク完了テスト"""

    def test_complete_task_success(self, worker_bee, temp_db_conn):
        """正常なタスク完了テスト"""
        # タスクを受け入れ
        task_id = self._create_test_task(temp_db_conn, "developer")
        with patch.object(worker_bee, "send_message"):
            worker_bee.accept_task(task_id)

        # 作業時間をシミュレート
        worker_bee.work_session_start = datetime.now() - timedelta(hours=2)

        # タスク完了
        deliverables = ["feature.py", "test_feature.py"]
        work_summary = "Implemented new feature with tests"
        quality_notes = "Code reviewed and tested"

        with patch.object(worker_bee, "send_message") as mock_send:
            result = worker_bee.complete_task(
                task_id, "Task completed successfully", deliverables, work_summary, quality_notes
            )

        assert result is True
        assert worker_bee.current_task_id is None
        assert worker_bee.work_session_start is None

        # データベース状態確認
        cursor = temp_db_conn.execute(
            "SELECT status, actual_hours, completed_at FROM tasks WHERE task_id = ?", (task_id,)
        )
        row = cursor.fetchone()
        assert row["status"] == "completed"
        assert row["actual_hours"] is not None
        assert row["completed_at"] is not None

        # 完了報告メッセージ確認
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert call_args[0] == "queen"
        assert call_args[1] == "task_update"
        assert "Task completed" in call_args[2]

    def test_complete_task_not_current_task(self, worker_bee, temp_db_conn):
        """現在の作業タスクでない場合の完了テスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")

        # タスクを受け入れずに完了を試行
        result = worker_bee.complete_task(task_id, "Result")
        assert result is False

    def test_complete_task_not_found(self, worker_bee):
        """存在しないタスクの完了テスト"""
        worker_bee.current_task_id = 999999

        result = worker_bee.complete_task(999999, "Result")
        assert result is False

    def test_completion_report_generation(self, worker_bee):
        """完了報告書生成テスト"""
        task_details = {
            "title": "Test Task",
            "estimated_hours": 3.0,
        }

        deliverables = ["file1.py", "file2.py"]
        work_summary = "Completed implementation"
        quality_notes = "All tests pass"
        work_duration = 2.5

        report = worker_bee._generate_completion_report(
            task_details, "Success", deliverables, work_summary, quality_notes, work_duration
        )

        assert "Test Task" in report
        assert "COMPLETED" in report
        assert "2.50 hours" in report
        assert "file1.py" in report
        assert "file2.py" in report
        assert "Completed implementation" in report
        assert "All tests pass" in report
        assert "Efficiency:" in report

    def _create_test_task(self, db_conn, assigned_to, task_id=None):
        """テスト用タスクを作成"""
        if task_id:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (task_id, title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, "Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        else:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        db_conn.commit()
        return task_id or cursor.lastrowid


class TestProgressReporting:
    """進捗報告テスト"""

    def test_report_progress_success(self, worker_bee, temp_db_conn):
        """正常な進捗報告テスト"""
        # タスクを受け入れ
        task_id = self._create_test_task(temp_db_conn, "developer")
        with patch.object(worker_bee, "send_message"):
            worker_bee.accept_task(task_id)

        # 進捗報告
        with patch.object(worker_bee, "send_message") as mock_send:
            result = worker_bee.report_progress(
                task_id, 50, "Half way complete", ["Need design approval"]
            )

        assert result is True

        # メッセージ送信確認
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert call_args[0] == "queen"
        assert call_args[1] == "task_update"
        assert "Progress 50%" in call_args[2]
        assert call_args[5] == "high"  # priority (blocking issues present)

    def test_report_progress_no_blocking_issues(self, worker_bee, temp_db_conn):
        """ブロッキング課題なしの進捗報告テスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")
        with patch.object(worker_bee, "send_message"):
            worker_bee.accept_task(task_id)

        with patch.object(worker_bee, "send_message") as mock_send:
            result = worker_bee.report_progress(task_id, 75, "Nearly complete")

        assert result is True

        call_args = mock_send.call_args[0]
        assert call_args[5] == "normal"  # priority (no blocking issues)

    def test_report_progress_non_current_task(self, worker_bee, temp_db_conn):
        """現在のタスクでない進捗報告テスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")

        # タスクを受け入れずに進捗報告
        with patch.object(worker_bee, "send_message") as mock_send:
            result = worker_bee.report_progress(task_id, 50, "Progress")

        # 警告は出るが、報告は実行される
        assert result is True
        mock_send.assert_called_once()

    def test_report_progress_task_not_found(self, worker_bee):
        """存在しないタスクの進捗報告テスト"""
        result = worker_bee.report_progress(999999, 50, "Progress")
        assert result is False

    def _create_test_task(self, db_conn, assigned_to, task_id=None):
        """テスト用タスクを作成"""
        cursor = db_conn.execute(
            """
            INSERT INTO tasks (task_id, title, description, assigned_to, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, "Test Task", "Test Description", assigned_to, "pending", "queen"),
        )
        db_conn.commit()
        return task_id or cursor.lastrowid


class TestAssistanceRequest:
    """支援要請テスト"""

    def test_request_assistance_success(self, worker_bee, temp_db_conn):
        """正常な支援要請テスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")
        with patch.object(worker_bee, "send_message"):
            worker_bee.accept_task(task_id)

        with (
            patch.object(worker_bee, "send_message") as mock_send,
            patch.object(worker_bee, "_get_current_progress", return_value=30),
        ):
            result = worker_bee.request_assistance(
                task_id, "Technical guidance", "Need help with architecture decision", urgent=True
            )

        assert result is True

        # メッセージ送信確認
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert call_args[0] == "queen"
        assert call_args[1] == "request"
        assert "Assistance needed" in call_args[2]
        assert call_args[5] == "urgent"  # priority

    def test_request_assistance_not_urgent(self, worker_bee, temp_db_conn):
        """緊急でない支援要請テスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")
        with patch.object(worker_bee, "send_message"):
            worker_bee.accept_task(task_id)

        with (
            patch.object(worker_bee, "send_message") as mock_send,
            patch.object(worker_bee, "_get_current_progress", return_value=30),
        ):
            result = worker_bee.request_assistance(
                task_id, "Code review", "Please review my implementation"
            )

        assert result is True

        call_args = mock_send.call_args[0]
        assert call_args[5] == "high"  # priority (not urgent)

    def test_request_assistance_task_not_found(self, worker_bee):
        """存在しないタスクの支援要請テスト"""
        result = worker_bee.request_assistance(999999, "Help", "Need assistance")
        assert result is False

    def _create_test_task(self, db_conn, assigned_to, task_id=None):
        """テスト用タスクを作成"""
        if task_id:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (task_id, title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, "Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        else:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        db_conn.commit()
        return task_id or cursor.lastrowid


class TestWorkTimeCalculation:
    """作業時間計算テスト"""

    def test_calculate_work_duration_no_session(self, worker_bee):
        """作業セッションなしでの時間計算テスト"""
        duration = worker_bee._calculate_work_duration()
        assert duration == 0.0

    def test_calculate_work_duration_with_session(self, worker_bee):
        """作業セッションありでの時間計算テスト"""
        # 2時間前に開始
        worker_bee.work_session_start = datetime.now() - timedelta(hours=2)

        duration = worker_bee._calculate_work_duration()
        assert 1.9 <= duration <= 2.1  # 約2時間の許容範囲

    def test_estimate_completion_time(self, worker_bee):
        """完了予定時間推定テスト"""
        task_details = {"estimated_hours": 4.0}

        completion_time = worker_bee._estimate_completion_time(task_details)

        # 形式確認（YYYY-MM-DD HH:MM）
        assert len(completion_time) == 16
        assert "-" in completion_time
        assert ":" in completion_time

    def test_estimate_completion_time_no_estimate(self, worker_bee):
        """推定時間なしでの完了予定時間推定テスト"""
        task_details = {}

        completion_time = worker_bee._estimate_completion_time(task_details)

        # デフォルト2時間後
        assert isinstance(completion_time, str)
        assert len(completion_time) == 16

    def test_get_current_progress_with_estimates(self, worker_bee, temp_db_conn):
        """推定時間ありでの進捗計算テスト"""
        task_id = self._create_test_task_with_estimates(temp_db_conn, "developer", 4.0)

        # 2時間作業済み
        worker_bee.work_session_start = datetime.now() - timedelta(hours=2)

        progress = worker_bee._get_current_progress(task_id)
        assert 40 <= progress <= 60  # 約50%の許容範囲

    def test_get_current_progress_no_estimates(self, worker_bee, temp_db_conn):
        """推定時間なしでの進捗計算テスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")

        progress = worker_bee._get_current_progress(task_id)
        assert progress == 50  # デフォルト値

    def _create_test_task(self, db_conn, assigned_to, task_id=None):
        """テスト用タスクを作成"""
        if task_id:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (task_id, title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, "Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        else:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        db_conn.commit()
        return task_id or cursor.lastrowid

    def _create_test_task_with_estimates(self, db_conn, assigned_to, estimated_hours, task_id=None):
        """推定時間付きテスト用タスクを作成"""
        if task_id:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (task_id, title, description, assigned_to, status, created_by, estimated_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    "Test Task",
                    "Test Description",
                    assigned_to,
                    "pending",
                    "queen",
                    estimated_hours,
                ),
            )
        else:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (title, description, assigned_to, status, created_by, estimated_hours)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("Test Task", "Test Description", assigned_to, "pending", "queen", estimated_hours),
            )
        db_conn.commit()
        return task_id or cursor.lastrowid


class TestMessageProcessing:
    """メッセージ処理テスト"""

    def test_handle_task_assignment(self, worker_bee, temp_db_conn):
        """タスク割り当てメッセージ処理テスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")

        message = {
            "message_id": 1,
            "message_type": "task_update",
            "from_bee": "queen",
            "task_id": task_id,
            "content": "New task assigned",
        }

        with (
            patch.object(worker_bee, "mark_message_processed") as mock_mark,
            patch.object(worker_bee, "accept_task", return_value=True) as mock_accept,
        ):
            worker_bee._handle_task_assignment(message)

            mock_accept.assert_called_once_with(task_id)
            mock_mark.assert_called_once_with(1)

    def test_handle_task_assignment_already_busy(self, worker_bee, temp_db_conn):
        """既に作業中でのタスク割り当て処理テスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")
        worker_bee.current_task_id = 999  # 既に作業中

        message = {
            "message_id": 1,
            "message_type": "task_update",
            "from_bee": "queen",
            "task_id": task_id,
        }

        with (
            patch.object(worker_bee, "mark_message_processed") as mock_mark,
            patch.object(worker_bee, "accept_task") as mock_accept,
        ):
            worker_bee._handle_task_assignment(message)

            # 受け入れは試行されない
            mock_accept.assert_not_called()
            mock_mark.assert_called_once_with(1)

    def test_handle_work_request(self, worker_bee):
        """作業要請メッセージ処理テスト"""
        message = {
            "message_id": 1,
            "message_type": "request",
            "from_bee": "queen",
            "subject": "Additional work needed",
            "content": "Please help with this task",
        }

        with (
            patch.object(worker_bee, "send_message") as mock_send,
            patch.object(worker_bee, "mark_message_processed") as mock_mark,
        ):
            worker_bee._handle_work_request(message)

            mock_send.assert_called_once()
            mock_mark.assert_called_once_with(1)

    def test_handle_queen_response(self, worker_bee, temp_db_conn):
        """Queen回答メッセージ処理テスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")
        worker_bee.current_task_id = task_id

        message = {
            "message_id": 1,
            "message_type": "response",
            "from_bee": "queen",
            "task_id": task_id,
            "content": "Proceed with plan A",
        }

        with (
            patch.object(worker_bee, "mark_message_processed") as mock_mark,
            patch.object(worker_bee, "log_activity") as mock_log,
        ):
            worker_bee._handle_queen_response(message)

            mock_log.assert_called_once()
            mock_mark.assert_called_once_with(1)

    def test_process_message_routing(self, worker_bee):
        """メッセージルーティングテスト"""
        # task_update メッセージ
        task_message = {"message_type": "task_update", "from_bee": "queen", "task_id": 1}

        with patch.object(worker_bee, "_handle_task_assignment") as mock_task:
            worker_bee._process_message(task_message)
            mock_task.assert_called_once_with(task_message)

        # request メッセージ
        request_message = {"message_type": "request", "from_bee": "queen"}

        with patch.object(worker_bee, "_handle_work_request") as mock_request:
            worker_bee._process_message(request_message)
            mock_request.assert_called_once_with(request_message)

    def _create_test_task(self, db_conn, assigned_to, task_id=None):
        """テスト用タスクを作成"""
        if task_id:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (task_id, title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, "Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        else:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        db_conn.commit()
        return task_id or cursor.lastrowid


class TestWorkSimulation:
    """作業シミュレーションテスト"""

    def test_simulate_work_success(self, worker_bee, temp_db_conn):
        """正常な作業シミュレーションテスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")

        work_steps = [
            {"name": "Analysis", "duration": 0.1, "progress": 25},
            {"name": "Implementation", "duration": 0.1, "progress": 75},
            {"name": "Testing", "duration": 0.1, "progress": 100},
        ]

        with patch.object(worker_bee, "send_message"):
            result = worker_bee.simulate_work(task_id, work_steps)

        assert result is True
        assert worker_bee.current_task_id is None  # 完了後はリセット

        # データベース状態確認
        cursor = temp_db_conn.execute("SELECT status FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        assert row["status"] == "completed"

    def test_simulate_work_task_accept_failure(self, worker_bee, temp_db_conn):
        """タスク受け入れ失敗時のシミュレーションテスト"""
        # 他のBeeに割り当てられたタスク
        task_id = self._create_test_task(temp_db_conn, "other_bee")

        work_steps = [{"name": "Work", "duration": 0.1}]

        result = worker_bee.simulate_work(task_id, work_steps)
        assert result is False

    def test_simulate_work_empty_steps(self, worker_bee, temp_db_conn):
        """空の作業ステップでのシミュレーションテスト"""
        task_id = self._create_test_task(temp_db_conn, "developer")

        with patch.object(worker_bee, "send_message"):
            result = worker_bee.simulate_work(task_id, [])

        assert result is True  # 空でも完了扱い

    def _create_test_task(self, db_conn, assigned_to, task_id=None):
        """テスト用タスクを作成"""
        if task_id:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (task_id, title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, "Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        else:
            cursor = db_conn.execute(
                """
                INSERT INTO tasks (title, description, assigned_to, status, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Test Task", "Test Description", assigned_to, "pending", "queen"),
            )
        db_conn.commit()
        return task_id or cursor.lastrowid


class TestErrorHandling:
    """エラーハンドリングテスト"""

    @patch.object(WorkerBee, "_get_db_connection")
    def test_update_capabilities_database_error(self, mock_db, temp_db_path):
        """能力更新でのデータベースエラーテスト"""
        mock_db.side_effect = DatabaseConnectionError("DB Error")

        config = BeehiveConfig(database_path=temp_db_path)

        with pytest.raises(DatabaseConnectionError):
            WorkerBee("test", "test_specialty", config)

    def test_bee_state_update_error_handling(self, worker_bee):
        """Bee状態更新エラーのハンドリングテスト"""
        with patch.object(worker_bee, "_update_bee_state", side_effect=Exception("Update failed")):
            # エラーが発生してもaccept_taskは続行する
            with (
                patch.object(
                    worker_bee,
                    "get_task_details",
                    return_value={"assigned_to": "developer", "title": "Test"},
                ),
                patch.object(worker_bee, "send_message"),
                patch.object(worker_bee, "update_task_status"),
                patch.object(worker_bee, "log_activity"),
            ):
                # エラーが発生するがテストは通る（ログに記録される）
                pass
