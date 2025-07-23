#!/usr/bin/env python3
"""
Pytest Configuration and Fixtures
Issue #23: テストスイート強化とコード品質向上

Beehiveプロジェクト用のpytestフィクスチャとテスト設定
"""

import os
import sqlite3
import tempfile
from unittest.mock import Mock, patch

import pytest

from .analyst_bee import AnalystBee
from .config import BeehiveConfig
from .queen_bee import QueenBee
from .worker_bee import WorkerBee


@pytest.fixture(scope="function")
def temp_db_path():
    """一時的なデータベースファイルパスを提供"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    yield db_path

    # クリーンアップ
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def temp_db_conn(temp_db_path):
    """一時的なデータベース接続とスキーマを提供"""
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row

    # テスト用スキーマを作成
    _create_test_schema(conn)

    yield conn

    conn.close()


@pytest.fixture(scope="function")
def base_config(temp_db_path):
    """基本的なBeehive設定を提供"""
    return BeehiveConfig(
        hive_db_path=temp_db_path,
        available_bees=["developer", "qa", "analyst"],
        task_assignment_strategy="balanced",
        max_tasks_per_bee=5,
    )


@pytest.fixture(scope="function")
def strict_config(temp_db_path):
    """厳格な制約を持つBeehive設定を提供"""
    return BeehiveConfig(
        hive_db_path=temp_db_path,
        available_bees=["developer", "qa", "analyst"],
        task_assignment_strategy="balanced",
        max_tasks_per_bee=3,
    )


@pytest.fixture(scope="function")
def queen_bee(base_config, temp_db_conn):
    """Queen Beeインスタンスを提供"""
    with patch.object(QueenBee, "_get_db_connection") as mock_db:
        mock_db.return_value.__enter__.return_value = temp_db_conn
        mock_db.return_value.__exit__.return_value = None

        queen = QueenBee(base_config)
        yield queen


@pytest.fixture(scope="function")
def queen_bee_strict(strict_config, temp_db_conn):
    """厳格設定のQueen Beeインスタンスを提供"""
    with patch.object(QueenBee, "_get_db_connection") as mock_db:
        mock_db.return_value.__enter__.return_value = temp_db_conn
        mock_db.return_value.__exit__.return_value = None

        queen = QueenBee(strict_config)
        yield queen


@pytest.fixture(scope="function")
def queen_bee_specialized(base_config, temp_db_conn):
    """特化戦略のQueen Beeインスタンスを提供"""
    config = base_config
    config.task_assignment_strategy = "specialized"

    with patch.object(QueenBee, "_get_db_connection") as mock_db:
        mock_db.return_value.__enter__.return_value = temp_db_conn
        mock_db.return_value.__exit__.return_value = None

        queen = QueenBee(config)
        yield queen


@pytest.fixture(scope="function")
def queen_bee_priority(base_config, temp_db_conn):
    """優先度戦略のQueen Beeインスタンスを提供"""
    config = base_config
    config.task_assignment_strategy = "priority"

    with patch.object(QueenBee, "_get_db_connection") as mock_db:
        mock_db.return_value.__enter__.return_value = temp_db_conn
        mock_db.return_value.__exit__.return_value = None

        queen = QueenBee(config)
        yield queen


@pytest.fixture(scope="function")
def worker_bee(base_config, temp_db_conn):
    """Developer Worker Beeインスタンスを提供"""
    with patch.object(WorkerBee, "_get_db_connection") as mock_db:
        mock_db.return_value.__enter__.return_value = temp_db_conn
        mock_db.return_value.__exit__.return_value = None

        worker = WorkerBee("developer", "development", base_config)
        yield worker


@pytest.fixture(scope="function")
def qa_bee(base_config, temp_db_conn):
    """QA Worker Beeインスタンスを提供"""
    with patch.object(WorkerBee, "_get_db_connection") as mock_db:
        mock_db.return_value.__enter__.return_value = temp_db_conn
        mock_db.return_value.__exit__.return_value = None

        qa = WorkerBee("qa", "quality_assurance", base_config)
        yield qa


@pytest.fixture(scope="function")
def analyst_bee(base_config, temp_db_conn):
    """Analyst Beeインスタンスを提供"""
    with patch.object(AnalystBee, "_get_db_connection") as mock_db:
        mock_db.return_value.__enter__.return_value = temp_db_conn
        mock_db.return_value.__exit__.return_value = None

        analyst = AnalystBee(base_config)
        yield analyst


@pytest.fixture(scope="function")
def integration_environment(base_config, temp_db_conn):
    """統合テスト用の完全環境を提供"""
    with patch("bees.base_bee.BaseBee._get_db_connection") as mock_db:
        mock_db.return_value.__enter__.return_value = temp_db_conn
        mock_db.return_value.__exit__.return_value = None

        # 全Beeインスタンスを作成
        queen = QueenBee(base_config)
        developer = WorkerBee("developer", "development", base_config)
        qa = WorkerBee("qa", "quality_assurance", base_config)
        analyst = AnalystBee(base_config)

        # Bee状態をデータベースに初期化
        _initialize_bee_states(temp_db_conn)

        yield queen, developer, qa, analyst, temp_db_conn


@pytest.fixture(scope="function")
def mock_logger():
    """モックロガーを提供"""
    logger = Mock()
    logger.log_event = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture(scope="function")
def sample_task_data():
    """サンプルタスクデータを提供"""
    return {
        "title": "Sample Task",
        "description": "This is a sample task for testing purposes",
        "priority": "medium",
        "estimated_hours": 3.5,
    }


@pytest.fixture(scope="function")
def sample_subtasks_data():
    """サンプルサブタスクデータを提供"""
    return [
        {
            "title": "Subtask 1: Analysis",
            "description": "Analyze requirements and create design",
            "priority": "high",
            "estimated_hours": 2.0,
        },
        {
            "title": "Subtask 2: Implementation",
            "description": "Implement the core functionality",
            "priority": "high",
            "estimated_hours": 4.0,
        },
        {
            "title": "Subtask 3: Testing",
            "description": "Create and run comprehensive tests",
            "priority": "medium",
            "estimated_hours": 2.5,
        },
    ]


@pytest.fixture(scope="function")
def sample_work_steps():
    """サンプル作業ステップデータを提供"""
    return [
        {"name": "Setup Environment", "duration": 0.1, "progress": 20},
        {"name": "Code Implementation", "duration": 0.1, "progress": 60},
        {"name": "Unit Testing", "duration": 0.1, "progress": 80},
        {"name": "Integration Testing", "duration": 0.1, "progress": 100},
    ]


def _create_test_schema(conn):
    """テスト用データベーススキーマを作成"""
    schema_sql = """
    -- Tasks table
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        priority TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'pending',
        assigned_to TEXT,
        created_by TEXT,
        parent_task_id INTEGER,
        estimated_hours REAL,
        actual_hours REAL,
        due_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id)
    );

    -- Task assignments table
    CREATE TABLE IF NOT EXISTS task_assignments (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        assigned_to TEXT NOT NULL,
        assigned_by TEXT NOT NULL,
        assignment_type TEXT DEFAULT 'primary',
        notes TEXT,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    );

    -- Task activity log
    CREATE TABLE IF NOT EXISTS task_activity (
        activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        bee_name TEXT NOT NULL,
        activity_type TEXT NOT NULL,
        description TEXT,
        metadata TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    );

    -- Bee states table
    CREATE TABLE IF NOT EXISTS bee_states (
        bee_name TEXT PRIMARY KEY,
        status TEXT DEFAULT 'idle',
        current_task_id INTEGER,
        workload_score REAL DEFAULT 0.0,
        performance_score REAL DEFAULT 100.0,
        capabilities TEXT,
        last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (current_task_id) REFERENCES tasks(task_id)
    );

    -- Bee messages table
    CREATE TABLE IF NOT EXISTS bee_messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_bee TEXT NOT NULL,
        to_bee TEXT NOT NULL,
        message_type TEXT NOT NULL,
        subject TEXT,
        content TEXT,
        priority TEXT DEFAULT 'normal',
        task_id INTEGER,
        processed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    );

    -- Context snapshots table
    CREATE TABLE IF NOT EXISTS context_snapshots (
        snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        bee_name TEXT NOT NULL,
        snapshot_type TEXT NOT NULL,
        context_data TEXT NOT NULL,
        task_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    );

    -- Decision log table
    CREATE TABLE IF NOT EXISTS decision_log (
        decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
        bee_name TEXT NOT NULL,
        decision_type TEXT NOT NULL,
        description TEXT NOT NULL,
        rationale TEXT,
        task_id INTEGER,
        metadata TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    );

    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);
    CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
    CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
    CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);
    CREATE INDEX IF NOT EXISTS idx_task_activity_task_id ON task_activity(task_id);
    CREATE INDEX IF NOT EXISTS idx_task_activity_bee ON task_activity(bee_name);
    CREATE INDEX IF NOT EXISTS idx_bee_messages_to_bee ON bee_messages(to_bee);
    CREATE INDEX IF NOT EXISTS idx_bee_messages_processed ON bee_messages(processed);
    """

    conn.executescript(schema_sql)
    conn.commit()


def _initialize_bee_states(conn):
    """Bee状態テーブルを初期化"""
    bees_data = [
        ("queen", "active", None, 0.0, 100.0, '["coordination", "task_management"]'),
        ("developer", "idle", None, 0.0, 95.0, '["development", "coding", "implementation"]'),
        ("qa", "idle", None, 0.0, 98.0, '["testing", "quality_assurance", "validation"]'),
        ("analyst", "idle", None, 0.0, 92.0, '["analysis", "metrics", "performance", "reporting"]'),
    ]

    conn.executemany(
        """
        INSERT OR REPLACE INTO bee_states
        (bee_name, status, current_task_id, workload_score, performance_score, capabilities)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        bees_data,
    )
    conn.commit()


# Test utility functions
def create_test_task(
    conn,
    title="Test Task",
    description="Test Description",
    assigned_to=None,
    status="pending",
    priority="medium",
):
    """テスト用タスクを作成するヘルパー関数"""
    cursor = conn.execute(
        """
        INSERT INTO tasks (title, description, assigned_to, status, priority, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, description, assigned_to, status, priority, "test_system"),
    )
    conn.commit()
    return cursor.lastrowid


def create_test_message(
    conn,
    from_bee,
    to_bee,
    message_type="info",
    subject="Test Message",
    content="Test content",
    task_id=None,
):
    """テスト用メッセージを作成するヘルパー関数"""
    cursor = conn.execute(
        """
        INSERT INTO bee_messages (from_bee, to_bee, message_type, subject, content, task_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (from_bee, to_bee, message_type, subject, content, task_id),
    )
    conn.commit()
    return cursor.lastrowid


def update_bee_state(conn, bee_name, status="idle", workload_score=0.0, current_task_id=None):
    """Bee状態を更新するヘルパー関数"""
    conn.execute(
        """
        UPDATE bee_states
        SET status = ?, workload_score = ?, current_task_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE bee_name = ?
        """,
        (status, workload_score, current_task_id, bee_name),
    )
    conn.commit()


# Test markers configuration
# pytest_plugins = []  # Removed - should be in top-level conftest.py


# Custom pytest collection hooks
def pytest_collection_modifyitems(config, items):
    """テスト項目にマーカーを自動追加"""
    for item in items:
        # テストファイル名に基づいてマーカーを追加
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # クラス名に基づいてマーカーを追加
        if "Queen" in item.nodeid:
            item.add_marker(pytest.mark.queen_bee)
        elif "Worker" in item.nodeid:
            item.add_marker(pytest.mark.worker_bee)
        elif "Analyst" in item.nodeid:
            item.add_marker(pytest.mark.analyst_bee)

        # 特定のテスト名パターンに基づいてマーカーを追加
        if "slow" in item.name or "stress" in item.name:
            item.add_marker(pytest.mark.slow)
        if "database" in item.name or "db" in item.name:
            item.add_marker(pytest.mark.database)
        if "workflow" in item.name:
            item.add_marker(pytest.mark.workflow)
        if "error" in item.name or "exception" in item.name:
            item.add_marker(pytest.mark.error_handling)


def pytest_configure(config):
    """Pytest設定の追加構成"""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for component interaction")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")
    config.addinivalue_line("markers", "database: Tests that require database access")
    config.addinivalue_line("markers", "queen_bee: Tests specific to Queen Bee functionality")
    config.addinivalue_line("markers", "worker_bee: Tests specific to Worker Bee functionality")
    config.addinivalue_line("markers", "analyst_bee: Tests specific to Analyst Bee functionality")
    config.addinivalue_line("markers", "workflow: Full workflow tests")
    config.addinivalue_line("markers", "error_handling: Error handling and edge case tests")
