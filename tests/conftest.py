#!/usr/bin/env python3
"""
pytest configuration and fixtures for Beehive tests
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bees.config import BeehiveConfig


@pytest.fixture
def temp_db():
    """Create a temporary database file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Create basic schema for testing
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bee_states (
            bee_name TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            current_task_id INTEGER,
            last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            workload_score INTEGER DEFAULT 0,
            capabilities TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            assigned_to TEXT,
            created_by TEXT,
            estimated_hours REAL,
            actual_hours REAL,
            parent_task_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bee_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_bee TEXT NOT NULL,
            to_bee TEXT NOT NULL,
            message_type TEXT NOT NULL,
            subject TEXT,
            content TEXT,
            task_id INTEGER,
            priority TEXT DEFAULT 'normal',
            processed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_activity (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            bee_name TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            description TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def test_config(temp_db):
    """Create a test configuration using temporary database"""
    return BeehiveConfig(
        hive_db_path=temp_db,
        session_name="test_session",
        log_level="DEBUG",
        structured_logging=True,
        pane_mapping={"queen": 1, "developer": 2, "qa": 3},
    )


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing"""
    logger = Mock()
    logger.info = Mock()
    logger.debug = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    logger.log_event = Mock()
    logger.log_performance = Mock()
    logger.log_error = Mock()
    return logger


@pytest.fixture
def mock_tmux_session():
    """Mock tmux session for testing tmux communication"""
    with patch("bees.base_bee.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        "task_id": 123,
        "title": "Test Task",
        "description": "This is a test task",
        "status": "pending",
        "priority": "medium",
        "assigned_to": "developer",
        "estimated_hours": 2.0,
    }


@pytest.fixture
def sample_bee_state():
    """Sample bee state data for testing"""
    return {
        "bee_name": "test_bee",
        "status": "idle",
        "current_task_id": None,
        "workload_score": 0,
        "capabilities": '["general_work", "task_execution"]',
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing"""
    return {
        "from_bee": "queen",
        "to_bee": "developer",
        "message_type": "task_assignment",
        "subject": "New Task Assignment",
        "content": "Please work on task #123",
        "task_id": 123,
        "priority": "normal",
    }


class DatabaseTestHelper:
    """Helper class for database testing operations"""

    @staticmethod
    def insert_test_task(db_path, task_data):
        """Insert test task into database"""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO tasks (title, description, status, priority, assigned_to, estimated_hours)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                task_data["title"],
                task_data["description"],
                task_data["status"],
                task_data["priority"],
                task_data["assigned_to"],
                task_data["estimated_hours"],
            ),
        )
        task_id = conn.lastrowid
        conn.commit()
        conn.close()
        return task_id

    @staticmethod
    def insert_test_bee_state(db_path, bee_data):
        """Insert test bee state into database"""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO bee_states
            (bee_name, status, current_task_id, workload_score, capabilities)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                bee_data["bee_name"],
                bee_data["status"],
                bee_data["current_task_id"],
                bee_data["workload_score"],
                bee_data["capabilities"],
            ),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_task_count(db_path):
        """Get total number of tasks in database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    @staticmethod
    def get_bee_state(db_path, bee_name):
        """Get bee state from database"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM bee_states WHERE bee_name = ?", (bee_name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


@pytest.fixture
def db_helper():
    """Database helper fixture"""
    return DatabaseTestHelper


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test"""
    import logging

    # Clear all handlers from root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Clear all handlers from beehive loggers
    beehive_logger = logging.getLogger("beehive")
    beehive_logger.handlers.clear()
    beehive_logger.propagate = True

    # Reset level
    root_logger.setLevel(logging.WARNING)

    yield

    # Cleanup after test
    root_logger.handlers.clear()
    beehive_logger.handlers.clear()


# Pytest markers for categorizing tests
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests that don't require external dependencies")
    config.addinivalue_line(
        "markers", "integration: Integration tests that require external dependencies"
    )
    config.addinivalue_line("markers", "mock_required: Tests that require extensive mocking")
    config.addinivalue_line("markers", "slow: Tests that may take longer to run")
    config.addinivalue_line("markers", "database: Tests that require database operations")
    config.addinivalue_line("markers", "tmux: Tests that require tmux functionality")
