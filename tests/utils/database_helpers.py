#!/usr/bin/env python3
"""
Database test helpers for conversation system testing
"""

import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import Mock

import pytest

from bees.config import BeehiveConfig


class TestDatabaseHelper:
    """Helper class for database testing operations"""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            # Create temporary database
            self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            self.db_path = self.temp_db.name
            self.temp_db.close()
        else:
            self.db_path = db_path
            self.temp_db = None

    def create_test_schema(self) -> None:
        """Create test database schema"""
        schema_sql = """
        -- Test schema for conversation system
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),
            priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
            assigned_to TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            estimated_hours REAL,
            actual_hours REAL,
            created_by TEXT DEFAULT 'human',
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS bee_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_bee TEXT NOT NULL,
            to_bee TEXT NOT NULL,
            message_type TEXT NOT NULL DEFAULT 'info' CHECK (message_type IN ('info', 'question', 'request', 'response', 'alert', 'task_update', 'instruction', 'conversation')),
            subject TEXT,
            content TEXT NOT NULL,
            task_id TEXT REFERENCES tasks(task_id),
            priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
            processed BOOLEAN NOT NULL DEFAULT FALSE,
            processed_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME,
            reply_to INTEGER REFERENCES bee_messages(message_id),
            sender_cli_used BOOLEAN NOT NULL DEFAULT TRUE,
            conversation_id TEXT,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS bee_states (
            state_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bee_name TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'busy', 'waiting', 'offline', 'error')),
            current_task_id TEXT REFERENCES tasks(task_id),
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
            capabilities TEXT,
            workload_score REAL DEFAULT 0,
            performance_score REAL DEFAULT 100,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Initialize bee states
        INSERT OR IGNORE INTO bee_states (bee_name, status, capabilities) VALUES
        ('queen', 'idle', '["task_management", "coordination", "planning", "delegation"]'),
        ('developer', 'idle', '["coding", "implementation", "debugging", "refactoring"]'),
        ('qa', 'idle', '["testing", "quality_assurance", "bug_reporting", "validation"]'),
        ('analyst', 'idle', '["performance_analysis", "code_metrics", "quality_assessment", "report_generation"]');
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(schema_sql)
            conn.commit()

    def insert_test_data(self, data: Dict[str, Any]) -> None:
        """Insert test data into database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Insert tasks if provided
            if 'tasks' in data:
                for task in data['tasks']:
                    conn.execute(
                        """
                        INSERT INTO tasks (task_id, title, description, status, priority, assigned_to, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            task.get('task_id'),
                            task.get('title'),
                            task.get('description'),
                            task.get('status', 'pending'),
                            task.get('priority', 'medium'),
                            task.get('assigned_to'),
                            task.get('created_by', 'test')
                        )
                    )

            # Insert messages if provided
            if 'messages' in data:
                for message in data['messages']:
                    conn.execute(
                        """
                        INSERT INTO bee_messages 
                        (from_bee, to_bee, message_type, subject, content, task_id, priority, sender_cli_used, conversation_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            message.get('from_bee'),
                            message.get('to_bee'),
                            message.get('message_type', 'info'),
                            message.get('subject'),
                            message.get('content'),
                            message.get('task_id'),
                            message.get('priority', 'medium'),
                            message.get('sender_cli_used', True),
                            message.get('conversation_id')
                        )
                    )

            conn.commit()

    def get_test_config(self) -> BeehiveConfig:
        """Get test configuration with test database"""
        config = BeehiveConfig()
        config.hive_db_path = self.db_path
        config.db_timeout = 5.0
        config.session_name = "test_beehive"
        config.pane_mapping = {
            "queen": "0",
            "developer": "1", 
            "qa": "2",
            "analyst": "3"
        }
        config.pane_id_mapping = {
            "queen": "0",
            "developer": "1",
            "qa": "2", 
            "analyst": "3"
        }
        return config

    def cleanup(self) -> None:
        """Clean up test database"""
        if self.temp_db is not None:
            Path(self.db_path).unlink(missing_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection for direct testing"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def count_records(self, table: str) -> int:
        """Count records in table"""
        with self.get_connection() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def get_latest_message(self) -> Dict[str, Any] | None:
        """Get the most recent message"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM bee_messages ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def get_latest_task(self) -> Dict[str, Any] | None:
        """Get the most recent task"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None


@pytest.fixture
def test_db_helper() -> Generator[TestDatabaseHelper, None, None]:
    """Pytest fixture for test database helper"""
    helper = TestDatabaseHelper()
    helper.create_test_schema()
    yield helper
    helper.cleanup()


@pytest.fixture
def test_config(test_db_helper: TestDatabaseHelper) -> BeehiveConfig:
    """Pytest fixture for test configuration"""
    return test_db_helper.get_test_config()


@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger