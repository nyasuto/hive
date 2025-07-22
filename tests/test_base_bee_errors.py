#!/usr/bin/env python3
"""
Test module for BaseBee error handling
Testing database errors, validation errors, and tmux communication errors
"""

import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from bees.base_bee import BaseBee
from bees.config import BeehiveConfig
from bees.exceptions import (
    BeeValidationError,
    DatabaseConnectionError,
    DatabaseOperationError,
    TaskExecutionError,
    TmuxCommandError,
)


class TestBaseBeeInitialization:
    """Test BaseBee initialization error handling"""

    def test_invalid_bee_name_empty(self):
        """Test initialization with empty bee name"""
        config = BeehiveConfig()

        with pytest.raises(BeeValidationError) as exc_info:
            BaseBee("", config)

        assert "bee_name" in str(exc_info.value)
        assert "non-empty string" in str(exc_info.value)

    def test_invalid_bee_name_none(self):
        """Test initialization with None bee name"""
        config = BeehiveConfig()

        with pytest.raises(BeeValidationError) as exc_info:
            BaseBee(None, config)

        assert "bee_name" in str(exc_info.value)

    def test_invalid_bee_name_too_long(self):
        """Test initialization with bee name too long"""
        config = BeehiveConfig()
        long_name = "a" * 51  # 51 characters, limit is 50

        with pytest.raises(BeeValidationError) as exc_info:
            BaseBee(long_name, config)

        assert "50 characters or less" in str(exc_info.value)

    def test_invalid_bee_name_not_in_pane_mapping(self):
        """Test initialization with bee name not in pane mapping"""
        config = BeehiveConfig(
            pane_mapping={"queen": "queen_pane", "developer": "dev_pane", "qa": "qa_pane"},
            pane_id_mapping={"queen": "beehive:0", "developer": "beehive:1", "qa": "beehive:2"},
        )

        with pytest.raises(BeeValidationError) as exc_info:
            BaseBee("unknown_bee", config)

        assert "unknown_bee" in str(exc_info.value)
        assert "must be one of" in str(exc_info.value)

    @patch("bees.base_bee.Path.exists")
    def test_database_not_found(self, mock_exists):
        """Test initialization when database file doesn't exist"""
        mock_exists.return_value = False

        config = BeehiveConfig(hive_db_path="nonexistent.db")

        with pytest.raises(DatabaseConnectionError) as exc_info:
            BaseBee("queen", config)

        assert "nonexistent.db" in str(exc_info.value)

    @patch("bees.base_bee.sqlite3.connect")
    @patch("bees.base_bee.Path.exists")
    def test_database_connection_error(self, mock_exists, mock_connect):
        """Test initialization when database connection fails"""
        mock_exists.return_value = True
        mock_connect.side_effect = sqlite3.OperationalError("database is locked")

        config = BeehiveConfig()

        with pytest.raises(DatabaseConnectionError) as exc_info:
            BaseBee("queen", config)

        assert "database is locked" in str(exc_info.value.original_error.args[0])


class TestBaseBeeStateManagement:
    """Test BaseBee state management error handling"""

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def setup_mock_bee(self, mock_connect, mock_exists):
        """Helper to set up a mocked BaseBee instance"""
        mock_exists.return_value = True
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()
        bee = BaseBee("queen", config)
        return bee, mock_conn

    def test_update_bee_state_invalid_status(self):
        """Test _update_bee_state with invalid status"""
        bee, _ = self.setup_mock_bee()

        with pytest.raises(BeeValidationError) as exc_info:
            bee._update_bee_state("invalid_status")

        assert "status" in str(exc_info.value)
        assert "invalid_status" in str(exc_info.value)

    def test_update_bee_state_invalid_workload(self):
        """Test _update_bee_state with invalid workload"""
        bee, _ = self.setup_mock_bee()

        with pytest.raises(BeeValidationError) as exc_info:
            bee._update_bee_state("idle", workload=150)  # Over 100

        assert "workload" in str(exc_info.value)
        assert "between 0 and 100" in str(exc_info.value)

    def test_update_bee_state_negative_workload(self):
        """Test _update_bee_state with negative workload"""
        bee, _ = self.setup_mock_bee()

        with pytest.raises(BeeValidationError) as exc_info:
            bee._update_bee_state("idle", workload=-10)

        assert "workload" in str(exc_info.value)
        assert "between 0 and 100" in str(exc_info.value)

    @patch("bees.base_bee.sqlite3.connect")
    @patch("bees.base_bee.Path.exists")
    def test_update_bee_state_database_error(self, mock_exists, mock_connect):
        """Test _update_bee_state with database error"""
        mock_exists.return_value = True

        # Mock connection that works for initialization but fails for update
        mock_conn = MagicMock()
        # First call (initialization) succeeds
        mock_conn.execute.side_effect = [
            MagicMock(),  # SELECT 1 for init_database
            sqlite3.OperationalError("disk I/O error"),  # UPDATE for _update_bee_state
        ]
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()
        bee = BaseBee("queen", config)

        with pytest.raises(DatabaseOperationError) as exc_info:
            bee._update_bee_state("idle")

        assert exc_info.value.operation == "update_bee_state"
        assert isinstance(exc_info.value.original_error, sqlite3.OperationalError)


class TestBaseBeeMessageHandling:
    """Test BaseBee message handling error scenarios"""

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def setup_mock_bee(self, mock_connect, mock_exists):
        """Helper to set up a mocked BaseBee instance"""
        mock_exists.return_value = True
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()
        bee = BaseBee("queen", config)
        return bee, mock_conn

    @patch("bees.base_bee.subprocess.run")
    def test_send_tmux_message_unknown_target(self, mock_subprocess):
        """Test sending message to unknown target bee"""
        bee, _ = self.setup_mock_bee()

        # This should log a warning but not raise an exception
        bee._send_tmux_message("unknown_bee", "test", "subject", "content")

        # subprocess.run should not have been called
        mock_subprocess.assert_not_called()

    @patch("bees.base_bee.subprocess.run")
    def test_send_tmux_message_subprocess_error(self, mock_subprocess):
        """Test tmux message sending with subprocess error"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "tmux", stderr="session not found"
        )

        bee, _ = self.setup_mock_bee()

        # Should handle the error gracefully (log warning, not raise exception)
        bee._send_tmux_message("developer", "test", "subject", "content")

        # Verify subprocess was attempted
        mock_subprocess.assert_called()

    def test_parse_structured_message_invalid_format(self):
        """Test parsing malformed structured message"""
        bee, _ = self.setup_mock_bee()

        # Test with completely invalid message
        invalid_message = "This is not a structured message"

        # Should handle gracefully and return parsed data with None values
        result = bee._parse_structured_message(invalid_message)

        assert result["message_type"] is None
        assert result["subject"] is None
        assert result["from_bee"] is None

    def test_parse_structured_message_partial_data(self):
        """Test parsing structured message with missing fields"""
        bee, _ = self.setup_mock_bee()

        partial_message = """## 📨 MESSAGE FROM DEVELOPER
**Type:** task_update
**Subject:** Test Subject
**Content:**
This is the content"""

        result = bee._parse_structured_message(partial_message)

        assert result["from_bee"] == "DEVELOPER"
        assert result["message_type"] == "task_update"
        assert result["subject"] == "Test Subject"
        assert result["task_id"] is None  # Missing field
        assert "This is the content" in result["content"]


class TestBaseBeeTaskOperations:
    """Test BaseBee task operations error handling"""

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def setup_mock_bee(self, mock_connect, mock_exists):
        """Helper to set up a mocked BaseBee instance"""
        mock_exists.return_value = True
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()
        bee = BaseBee("queen", config)
        return bee, mock_conn

    def test_get_task_details_nonexistent_task(self):
        """Test getting details for nonexistent task"""
        bee, mock_conn = self.setup_mock_bee()

        # Mock cursor that returns None (no row found)
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor

        result = bee.get_task_details(999)
        assert result is None

    @patch("bees.base_bee.sqlite3.connect")
    @patch("bees.base_bee.Path.exists")
    def test_update_task_status_database_error(self, mock_exists, mock_connect):
        """Test update_task_status with database error"""
        mock_exists.return_value = True

        mock_conn = MagicMock()
        # First call (initialization) succeeds, second call (update) fails
        mock_conn.execute.side_effect = [
            MagicMock(),  # SELECT 1 for init_database
            sqlite3.IntegrityError("constraint failed"),  # UPDATE for update_task_status
        ]
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()
        bee = BaseBee("queen", config)

        # Should handle database error gracefully or re-raise appropriately
        with pytest.raises(sqlite3.IntegrityError):
            bee.update_task_status(123, "completed", "Task finished")

    def test_log_activity_with_invalid_metadata(self):
        """Test log_activity with metadata that can't be JSON serialized"""
        bee, mock_conn = self.setup_mock_bee()

        # Create metadata with non-serializable object
        class NonSerializable:
            pass

        invalid_metadata = {"object": NonSerializable()}

        # Should handle JSON serialization error gracefully
        with pytest.raises(TypeError):
            bee.log_activity(123, "test", "description", invalid_metadata)


class TestBaseBeeContextManager:
    """Test BaseBee context manager error handling"""

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def test_context_manager_normal_exit(self, mock_connect, mock_exists):
        """Test context manager with normal exit"""
        mock_exists.return_value = True
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()

        with BaseBee("queen", config) as bee:
            assert bee is not None

        # Should have updated state to idle on normal exit
        assert mock_conn.execute.called

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def test_context_manager_exception_exit(self, mock_connect, mock_exists):
        """Test context manager with exception exit"""
        mock_exists.return_value = True
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()

        try:
            with BaseBee("queen", config) as bee:
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should have updated state to error on exception exit
        assert mock_conn.execute.called

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def test_context_manager_exit_database_error(self, mock_connect, mock_exists):
        """Test context manager when exit state update fails"""
        mock_exists.return_value = True
        mock_conn = MagicMock()

        # Make the initial connection work but final state update fail
        def side_effect(*args, **kwargs):
            if "UPDATE bee_states" in args[0]:
                raise sqlite3.OperationalError("database locked")
            return Mock()

        mock_conn.execute.side_effect = side_effect
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()

        # Should handle the error gracefully and not raise
        with BaseBee("queen", config) as bee:
            pass


class TestBaseBeeHealthMonitoring:
    """Test BaseBee health monitoring and error recovery"""

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def test_get_health_status(self, mock_connect, mock_exists):
        """Test get_health_status method"""
        mock_exists.return_value = True
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()
        bee = BaseBee("queen", config)

        health = bee.get_health_status()

        assert "bee_name" in health
        assert "database_healthy" in health
        assert "tmux_session_healthy" in health
        assert "config_loaded" in health
        assert "timestamp" in health

        assert health["bee_name"] == "queen"
        assert health["config_loaded"] is True

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def test_database_health_after_connection_error(self, mock_connect, mock_exists):
        """Test database health status after connection error"""
        mock_exists.return_value = True

        # First connection fails
        mock_connect.side_effect = [
            sqlite3.OperationalError("database locked"),
            MagicMock(),  # Second connection succeeds
        ]

        config = BeehiveConfig()

        with pytest.raises(DatabaseConnectionError):
            BaseBee("queen", config)


class TestBaseBeeStringRepresentation:
    """Test BaseBee string representation methods"""

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def test_str_representation(self, mock_connect, mock_exists):
        """Test __str__ method"""
        mock_exists.return_value = True
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()
        bee = BaseBee("queen", config)

        str_repr = str(bee)

        assert "BaseBee" in str_repr
        assert "queen" in str_repr
        assert "db_healthy" in str_repr
        assert "tmux_healthy" in str_repr

    @patch("bees.base_bee.Path.exists")
    @patch("bees.base_bee.sqlite3.connect")
    def test_repr_representation(self, mock_connect, mock_exists):
        """Test __repr__ method"""
        mock_exists.return_value = True
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_connect.return_value.__exit__.return_value = None

        config = BeehiveConfig()
        bee = BaseBee("queen", config)

        repr_str = repr(bee)

        assert "BaseBee" in repr_str
        assert "bee_name='queen'" in repr_str
        assert "hive_db_path" in repr_str
        assert "session_name" in repr_str
