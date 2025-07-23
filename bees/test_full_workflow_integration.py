#!/usr/bin/env python3
"""
Full Workflow Integration Tests
Issue #23: テストスイート強化とコード品質向上

タスク作成から完了までのE2Eテスト
Queen Bee、Worker Bee、Analyst Beeの連携テスト
"""

import json
import time
from unittest.mock import patch

import pytest

from .exceptions import TaskValidationError


class TestFullWorkflowIntegration:
    """完全ワークフロー統合テスト"""

    def test_complete_task_lifecycle(self, integration_environment):
        """タスクの完全ライフサイクルテスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # Step 1: Queen がタスクを作成
        task_id = queen.create_task(
            title="Integration Test Task",
            description="Implement feature with tests and analysis",
            priority="high",
            estimated_hours=4.0,
        )

        assert task_id > 0

        # Step 2: Queen がタスクを分解
        subtasks = [
            {
                "title": "Feature Implementation",
                "description": "Implement core functionality",
                "priority": "high",
            },
            {
                "title": "Test Suite Creation",
                "description": "Create comprehensive tests",
                "priority": "medium",
            },
            {
                "title": "Performance Analysis",
                "description": "Analyze performance metrics",
                "priority": "medium",
            },
        ]

        subtask_ids = queen.decompose_task(task_id, subtasks)
        assert len(subtask_ids) == 3

        # Step 3: Queen が自動割り当て実行
        with patch.object(queen, "send_message"):
            assigned_count = queen.auto_assign_tasks()

        assert assigned_count >= 3

        # Step 4: Worker Beeたちがタスクを受け入れ・実行
        # Developer がImplementationタスクを処理
        dev_task_id = self._find_task_by_title(db_conn, "Feature Implementation")
        if dev_task_id:
            with patch.object(developer, "send_message"):
                success = developer.accept_task(dev_task_id)
                assert success

                # 進捗報告
                developer.report_progress(dev_task_id, 50, "Half way through implementation")

                # タスク完了
                developer.complete_task(
                    dev_task_id,
                    "Feature implemented successfully",
                    ["feature.py", "interface.py"],
                    "Implemented according to specifications",
                    "Code reviewed and optimized",
                )

        # QA がTestタスクを処理
        qa_task_id = self._find_task_by_title(db_conn, "Test Suite Creation")
        if qa_task_id:
            with patch.object(qa, "send_message"):
                success = qa.accept_task(qa_task_id)
                assert success

                qa.complete_task(
                    qa_task_id,
                    "Test suite created and all tests pass",
                    ["test_feature.py", "test_integration.py"],
                    "Comprehensive test coverage achieved",
                    "All edge cases covered",
                )

        # Analyst がAnalysisタスクを処理
        analyst_task_id = self._find_task_by_title(db_conn, "Performance Analysis")
        if analyst_task_id:
            with patch.object(analyst, "send_message"):
                success = analyst.accept_task(analyst_task_id)
                assert success

                analyst.complete_task(
                    analyst_task_id,
                    "Performance analysis completed",
                    ["performance_report.md", "metrics.json"],
                    "System performance is within acceptable limits",
                    "No bottlenecks identified",
                )

        # Step 5: Queen が進捗をレビュー
        progress_report = queen.review_task_progress()

        assert "status_statistics" in progress_report
        assert "bee_statistics" in progress_report

        # 完了したタスクがカウントされることを確認
        completed_tasks = [
            stat for stat in progress_report["status_statistics"] if stat["status"] == "completed"
        ]
        assert len(completed_tasks) > 0

    def test_task_assignment_strategies(self, integration_environment):
        """タスク割り当て戦略テスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 異なる種類のタスクを作成
        tasks = [
            {
                "title": "Code Implementation Task",
                "description": "Implement new code functionality",
                "keywords": ["implement", "code", "develop"],
            },
            {
                "title": "Quality Assurance Task",
                "description": "Test and verify system quality",
                "keywords": ["test", "qa", "verify"],
            },
            {
                "title": "Performance Analysis Task",
                "description": "Analyze system performance metrics",
                "keywords": ["analyze", "performance", "metrics"],
            },
        ]

        task_ids = []
        for task in tasks:
            task_id = queen.create_task(
                title=task["title"], description=task["description"], priority="medium"
            )
            task_ids.append(task_id)

        # 自動割り当て実行
        with patch.object(queen, "send_message"):
            assigned_count = queen.auto_assign_tasks()

        assert assigned_count == len(tasks)

        # 割り当て結果を確認
        assignments = {}
        for task_id in task_ids:
            cursor = db_conn.execute(
                "SELECT title, assigned_to FROM tasks WHERE task_id = ?", (task_id,)
            )
            row = cursor.fetchone()
            assignments[row["title"]] = row["assigned_to"]

        # 特化割り当てが正しく行われることを期待
        assert assignments["Code Implementation Task"] in ["developer"]
        assert assignments["Quality Assurance Task"] in ["qa"]
        assert assignments["Performance Analysis Task"] in ["analyst"]

    def test_workload_balancing(self, integration_environment):
        """ワークロード分散テスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 複数のタスクを作成
        task_ids = []
        for i in range(6):
            task_id = queen.create_task(
                title=f"Generic Task {i + 1}",
                description=f"Generic work task {i + 1}",
                priority="medium",
            )
            task_ids.append(task_id)

        # バランス戦略でQueen設定
        queen.task_assignment_strategy = "balanced"

        # 自動割り当て実行
        with patch.object(queen, "send_message"):
            assigned_count = queen.auto_assign_tasks()

        assert assigned_count == 6

        # 各Beeの割り当て数を確認
        bee_counts = {}
        for bee in ["developer", "qa", "analyst"]:
            cursor = db_conn.execute(
                "SELECT COUNT(*) as count FROM tasks WHERE assigned_to = ?", (bee,)
            )
            row = cursor.fetchone()
            bee_counts[bee] = row["count"]

        # 負荷が比較的均等に分散されることを確認
        counts = list(bee_counts.values())
        assert max(counts) - min(counts) <= 2  # 最大2タスクの差まで許容

    def test_error_handling_workflow(self, integration_environment):
        """エラーハンドリングワークフローテスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 無効なタスクでのエラーハンドリング
        with pytest.raises(TaskValidationError):
            queen.create_task("", "Invalid empty title task")

        # 存在しないBeeへの割り当て
        task_id = queen.create_task("Test Task", "Test Description")

        with pytest.raises(ValueError):  # BeeNotFoundError
            queen.assign_task_to_bee(task_id, "nonexistent_bee")

        # Worker Beeの無効なタスク受け入れ
        invalid_result = developer.accept_task(999999)
        assert invalid_result is False

        # 存在しないタスクの完了試行
        completion_result = developer.complete_task(999999, "Cannot complete")
        assert completion_result is False

    def test_concurrent_task_processing(self, integration_environment):
        """並行タスク処理テスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 複数のタスクを同時に処理するシナリオ
        task_ids = []
        for i in range(3):
            task_id = queen.create_task(
                title=f"Concurrent Task {i + 1}",
                description=f"Task to be processed concurrently {i + 1}",
                priority="high",
            )
            task_ids.append(task_id)

        # 各Beeに手動で割り当て
        with patch.object(queen, "send_message"):
            queen.assign_task_to_bee(task_ids[0], "developer")
            queen.assign_task_to_bee(task_ids[1], "qa")
            queen.assign_task_to_bee(task_ids[2], "analyst")

        # 並行してタスクを受け入れ
        with (
            patch.object(developer, "send_message"),
            patch.object(qa, "send_message"),
            patch.object(analyst, "send_message"),
        ):
            dev_result = developer.accept_task(task_ids[0])
            qa_result = qa.accept_task(task_ids[1])
            analyst_result = analyst.accept_task(task_ids[2])

        assert dev_result is True
        assert qa_result is True
        assert analyst_result is True

        # 各Beeが独立して作業中であることを確認
        assert developer.current_task_id == task_ids[0]
        assert qa.current_task_id == task_ids[1]
        assert analyst.current_task_id == task_ids[2]

    def test_parent_task_completion_workflow(self, integration_environment):
        """親タスク完了ワークフローテスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 親タスクとサブタスクの作成
        parent_id = queen.create_task(
            title="Parent Task", description="Main task with subtasks", priority="high"
        )

        subtasks = [
            {"title": "Subtask 1", "description": "First subtask"},
            {"title": "Subtask 2", "description": "Second subtask"},
        ]

        subtask_ids = queen.decompose_task(parent_id, subtasks)

        # サブタスクを割り当て・完了
        with patch.object(queen, "send_message"):
            queen.assign_task_to_bee(subtask_ids[0], "developer")
            queen.assign_task_to_bee(subtask_ids[1], "qa")

        # 最初のサブタスクを完了
        with patch.object(developer, "send_message"):
            developer.accept_task(subtask_ids[0])
            developer.complete_task(subtask_ids[0], "Subtask 1 completed")

        # まだ親タスクは未完了
        cursor = db_conn.execute("SELECT status FROM tasks WHERE task_id = ?", (parent_id,))
        row = cursor.fetchone()
        assert row["status"] != "completed"

        # 2番目のサブタスクも完了
        with patch.object(qa, "send_message"):
            qa.accept_task(subtask_ids[1])
            qa.complete_task(subtask_ids[1], "Subtask 2 completed")

            # 完了処理中に親タスクの状態もチェック
            queen._handle_task_completion(subtask_ids[1], "qa")

        # 全サブタスク完了後、親タスクも自動完了
        cursor = db_conn.execute("SELECT status FROM tasks WHERE task_id = ?", (parent_id,))
        row = cursor.fetchone()
        assert row["status"] == "completed"

    def test_message_communication_flow(self, integration_environment):
        """メッセージ通信フローテスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # タスク作成と割り当て
        task_id = queen.create_task(
            title="Communication Test Task", description="Test inter-bee communication"
        )

        with patch.object(queen, "send_message") as queen_send:
            queen.assign_task_to_bee(task_id, "developer")

            # Queen がDeveloperにメッセージを送信したことを確認
            queen_send.assert_called_once()
            call_args = queen_send.call_args[0]
            assert call_args[0] == "developer"  # to_bee
            assert call_args[1] == "task_update"  # message_type

        # Developerがタスクを受け入れ、Queen に報告
        with patch.object(developer, "send_message") as dev_send:
            developer.accept_task(task_id)

            # Developer がQueenに受け入れ報告
            dev_send.assert_called_once()
            call_args = dev_send.call_args[0]
            assert call_args[0] == "queen"
            assert call_args[1] == "task_update"

        # 進捗報告の通信
        with patch.object(developer, "send_message") as dev_send:
            developer.report_progress(task_id, 75, "Nearly complete")

            dev_send.assert_called_once()
            call_args = dev_send.call_args[0]
            assert "Progress 75%" in call_args[2]

        # 支援要請の通信
        with patch.object(developer, "send_message") as dev_send:
            developer.request_assistance(task_id, "Technical help", "Need guidance on architecture")

            dev_send.assert_called_once()
            call_args = dev_send.call_args[0]
            assert call_args[1] == "request"

    def test_performance_monitoring_integration(self, integration_environment):
        """パフォーマンス監視統合テスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # タスクを作成してAnalystに分析させる
        task_id = queen.create_task(
            title="System Performance Analysis",
            description="Comprehensive performance analysis and optimization recommendations",
        )

        with patch.object(queen, "send_message"):
            queen.assign_task_to_bee(task_id, "analyst")

        # Analystがパフォーマンス分析を実行
        with patch.object(analyst, "send_message"):
            analyst.accept_task(task_id)

            # 分析結果をシミュレート
            analysis_result = {
                "cpu_usage": "65%",
                "memory_usage": "78%",
                "response_time": "245ms",
                "bottlenecks": ["database queries", "image processing"],
            }

            analyst.complete_task(
                task_id,
                f"Performance analysis completed: {json.dumps(analysis_result)}",
                ["performance_report.json", "optimization_plan.md"],
                "Identified key performance bottlenecks and optimization opportunities",
                "Recommendations prioritized by impact",
            )

        # タスクの完了とアクティビティログを確認
        cursor = db_conn.execute(
            "SELECT status, actual_hours FROM tasks WHERE task_id = ?", (task_id,)
        )
        row = cursor.fetchone()
        assert row["status"] == "completed"
        assert row["actual_hours"] is not None

    def test_stress_testing_workflow(self, integration_environment):
        """ストレステストワークフロー"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 大量のタスクを作成
        task_ids = []
        for i in range(20):
            task_id = queen.create_task(
                title=f"Stress Test Task {i + 1}",
                description=f"Load testing task {i + 1}",
                priority="medium" if i % 2 == 0 else "low",
            )
            task_ids.append(task_id)

        # 自動割り当てでシステム負荷をテスト
        with patch.object(queen, "send_message"):
            assigned_count = queen.auto_assign_tasks()

        assert assigned_count == 20

        # 全タスクが適切に割り当てられていることを確認
        cursor = db_conn.execute(
            "SELECT COUNT(*) as count FROM tasks WHERE assigned_to IS NOT NULL"
        )
        row = cursor.fetchone()
        assert row["count"] >= 20

        # 進捗レビューでシステム状態を確認
        progress_report = queen.review_task_progress()
        assert "bee_statistics" in progress_report
        assert len(progress_report["bee_statistics"]) > 0

    def _find_task_by_title(self, db_conn, title):
        """タイトルでタスクIDを検索"""
        cursor = db_conn.execute("SELECT task_id FROM tasks WHERE title = ?", (title,))
        row = cursor.fetchone()
        return row["task_id"] if row else None


class TestWorkflowEdgeCases:
    """ワークフローエッジケーステスト"""

    def test_rapid_task_creation_and_assignment(self, integration_environment):
        """高速タスク作成・割り当てテスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 短時間で大量のタスクを作成
        start_time = time.time()
        task_ids = []

        for i in range(10):
            task_id = queen.create_task(
                title=f"Rapid Task {i + 1}", description=f"Rapidly created task {i + 1}"
            )
            task_ids.append(task_id)

        creation_time = time.time() - start_time
        assert creation_time < 5.0  # 5秒以内で完了

        # 一括自動割り当て
        with patch.object(queen, "send_message"):
            assigned_count = queen.auto_assign_tasks()

        assert assigned_count == len(task_ids)

    def test_task_dependency_cycles(self, integration_environment):
        """タスク依存関係サイクルテスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 親子関係のタスクを作成
        parent_id = queen.create_task("Parent Task", "Main task")

        subtasks = [
            {"title": "Child Task 1", "description": "First child"},
            {"title": "Child Task 2", "description": "Second child"},
        ]

        child_ids = queen.decompose_task(parent_id, subtasks)

        # 循環依存を作成しようとする（これは防止されるべき）
        # 実装では親タスクIDは子タスクに設定できないようになっている
        with pytest.raises(ValueError):
            # 子タスクを親の親にしようとする無効な操作
            queen.decompose_task(child_ids[0], [{"title": "Invalid", "description": "Invalid"}])

    def test_simultaneous_bee_operations(self, integration_environment):
        """同時Bee操作テスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 複数のBeeが同時にタスクを処理
        task_id1 = queen.create_task("Concurrent Task 1", "Description 1")
        task_id2 = queen.create_task("Concurrent Task 2", "Description 2")
        task_id3 = queen.create_task("Concurrent Task 3", "Description 3")

        with patch.object(queen, "send_message"):
            queen.assign_task_to_bee(task_id1, "developer")
            queen.assign_task_to_bee(task_id2, "qa")
            queen.assign_task_to_bee(task_id3, "analyst")

        # 全Beeが同時にタスクを受け入れ
        with (
            patch.object(developer, "send_message"),
            patch.object(qa, "send_message"),
            patch.object(analyst, "send_message"),
        ):
            results = [
                developer.accept_task(task_id1),
                qa.accept_task(task_id2),
                analyst.accept_task(task_id3),
            ]

        assert all(results)  # すべて成功

        # 各Beeが独立して動作していることを確認
        assert developer.current_task_id == task_id1
        assert qa.current_task_id == task_id2
        assert analyst.current_task_id == task_id3

    def test_database_consistency_under_load(self, integration_environment):
        """負荷下でのデータベース整合性テスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 複数の操作を並行実行
        operations_completed = 0

        # タスク作成
        task_ids = []
        for i in range(5):
            task_id = queen.create_task(f"Load Test {i + 1}", f"Description {i + 1}")
            task_ids.append(task_id)
            operations_completed += 1

        # 割り当て
        with patch.object(queen, "send_message"):
            for i, task_id in enumerate(task_ids):
                bee_name = ["developer", "qa", "analyst"][i % 3]
                queen.assign_task_to_bee(task_id, bee_name)
                operations_completed += 1

        # データベースの整合性を確認
        cursor = db_conn.execute("SELECT COUNT(*) as count FROM tasks")
        task_count = cursor.fetchone()["count"]

        cursor = db_conn.execute("SELECT COUNT(*) as count FROM task_activity")
        activity_count = cursor.fetchone()["count"]

        assert task_count >= len(task_ids)
        assert activity_count >= operations_completed  # 各操作でアクティビティログが作成される

    def test_memory_usage_optimization(self, integration_environment):
        """メモリ使用量最適化テスト"""
        queen, developer, qa, analyst, db_conn = integration_environment

        # 大量のタスクデータでメモリ効率をテスト
        large_description = "x" * 1000  # 1KB の説明文

        task_ids = []
        for i in range(50):
            task_id = queen.create_task(
                f"Memory Test Task {i + 1}", large_description, estimated_hours=float(i % 10 + 1)
            )
            task_ids.append(task_id)

        # 進捗レビューで大量データを処理
        progress_report = queen.review_task_progress()

        # レポートが正常に生成されることを確認
        assert "status_statistics" in progress_report
        assert "bee_statistics" in progress_report
        assert isinstance(progress_report["status_statistics"], list)

        # データベースサイズが合理的であることを確認
        cursor = db_conn.execute("SELECT COUNT(*) as count FROM tasks")
        task_count = cursor.fetchone()["count"]
        assert task_count >= 50
