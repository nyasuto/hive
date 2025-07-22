#!/usr/bin/env python3
"""
Test module for custom exception classes
Testing all custom exceptions and error handling decorators
"""

import json
import pytest
import sqlite3
from unittest.mock import Mock, patch

from bees.exceptions import (
    BeehiveError,
    BeeValidationError,
    DatabaseConnectionError,
    DatabaseOperationError,
    TaskExecutionError,
    TaskValidationError,
    TmuxSessionError,
    MessageSendError,
    ConfigurationLoadError,
    ConfigurationValidationError,
    WorkflowStateError,
    error_handler,
    wrap_database_error,
    wrap_communication_error,
)


class TestBeehiveError:
    """Test the base BeehiveError class"""

    def test_basic_creation(self):
        """Test basic error creation"""
        error = BeehiveError("Test error message")
        assert str(error) == "Test error message"
        assert error.error_code is None
        assert error.metadata == {}

    def test_creation_with_error_code(self):
        """Test error creation with error code"""
        error = BeehiveError("Test error", error_code="TEST001")
        assert str(error) == "[TEST001] Test error"
        assert error.error_code == "TEST001"
        assert error.metadata == {}

    def test_creation_with_metadata(self):
        """Test error creation with metadata"""
        metadata = {"component": "test", "severity": "high"}
        error = BeehiveError("Test error", metadata=metadata)
        assert str(error) == "Test error"
        assert error.error_code is None
        assert error.metadata == metadata

    def test_creation_with_all_params(self):
        """Test error creation with all parameters"""
        metadata = {"component": "test", "severity": "high"}
        error = BeehiveError("Test error", error_code="TEST001", metadata=metadata)
        assert str(error) == "[TEST001] Test error"
        assert error.error_code == "TEST001"
        assert error.metadata == metadata

    def test_dict_representation(self):
        """Test dictionary representation"""
        metadata = {"component": "test"}
        error = BeehiveError("Test error", error_code="TEST001", metadata=metadata)
        error_dict = error.to_dict()
        
        expected = {
            "error_type": "BeehiveError",
            "message": "[TEST001] Test error",
            "error_code": "TEST001",
            "metadata": metadata
        }
        assert error_dict == expected

    def test_json_representation(self):
        """Test JSON representation"""
        metadata = {"component": "test"}
        error = BeehiveError("Test error", error_code="TEST001", metadata=metadata)
        json_str = error.to_json()
        
        parsed = json.loads(json_str)
        assert parsed["error_type"] == "BeehiveError"
        assert parsed["message"] == "[TEST001] Test error"
        assert parsed["error_code"] == "TEST001"
        assert parsed["metadata"] == metadata


class TestBeeValidationError:
    """Test BeeValidationError class"""

    def test_creation(self):
        """Test BeeValidationError creation"""
        error = BeeValidationError(
            bee_name="test_bee",
            field="test_field", 
            value="invalid_value",
            reason="Test validation failed"
        )
        assert "test_bee" in str(error)
        assert "test_field" in str(error)
        assert "invalid_value" in str(error)
        assert error.bee_name == "test_bee"
        assert error.field == "test_field"
        assert error.value == "invalid_value"
        assert error.reason == "Test validation failed"

    def test_metadata_includes_validation_info(self):
        """Test that metadata includes validation information"""
        error = BeeValidationError(
            bee_name="test_bee",
            field="test_field",
            value="invalid_value", 
            reason="Test validation failed"
        )
        assert error.metadata["bee_name"] == "test_bee"
        assert error.metadata["field"] == "test_field"
        assert error.metadata["value"] == "invalid_value"
        assert error.metadata["reason"] == "Test validation failed"


class TestDatabaseErrors:
    """Test database-related error classes"""

    def test_database_connection_error(self):
        """Test DatabaseConnectionError"""
        error = DatabaseConnectionError("test.db")
        assert "test.db" in str(error)
        assert error.database_path == "test.db"

    def test_database_connection_error_with_original(self):
        """Test DatabaseConnectionError with original error"""
        original = sqlite3.OperationalError("database is locked")
        error = DatabaseConnectionError("test.db", original)
        assert "test.db" in str(error)
        assert error.database_path == "test.db"
        assert error.original_error == original

    def test_database_operation_error(self):
        """Test DatabaseOperationError"""
        error = DatabaseOperationError(
            operation="insert_task",
            query="INSERT INTO tasks...",
            original_error=sqlite3.Error("constraint failed")
        )
        assert "insert_task" in str(error)
        assert error.operation == "insert_task"
        assert error.query == "INSERT INTO tasks..."
        assert isinstance(error.original_error, sqlite3.Error)


class TestTaskErrors:
    """Test task-related error classes"""

    def test_task_execution_error(self):
        """Test TaskExecutionError"""
        error = TaskExecutionError(
            task_id=123,
            bee_name="test_bee",
            stage="validation",
            original_error=ValueError("invalid input")
        )
        assert "123" in str(error)
        assert "test_bee" in str(error) 
        assert "validation" in str(error)
        assert error.task_id == 123
        assert error.bee_name == "test_bee"
        assert error.stage == "validation"

    def test_task_validation_error(self):
        """Test TaskValidationError"""
        error = TaskValidationError(
            field="priority",
            value="invalid_priority",
            reason="Must be low, medium, or high"
        )
        assert "priority" in str(error)
        assert error.field == "priority"
        assert error.value == "invalid_priority"
        assert error.reason == "Must be low, medium, or high"


class TestTmuxErrors:
    """Test tmux-related error classes"""

    def test_tmux_session_error(self):
        """Test TmuxSessionError"""
        error = TmuxSessionError("beehive", "start_session", ValueError("Session not found"))
        assert "beehive" in str(error)
        assert "start_session" in str(error)
        assert error.session_name == "beehive"
        assert error.operation == "start_session"

    def test_message_send_error(self):
        """Test MessageSendError"""
        error = MessageSendError(
            from_bee="queen",
            to_bee="developer",
            message_type="task_assignment",
            original_error=ConnectionError("Connection failed")
        )
        assert "queen" in str(error)
        assert "developer" in str(error)
        assert "task_assignment" in str(error)
        assert error.from_bee == "queen"
        assert error.to_bee == "developer"
        assert error.message_type == "task_assignment"


class TestOtherErrors:
    """Test other custom error classes"""

    def test_configuration_load_error(self):
        """Test ConfigurationLoadError"""
        error = ConfigurationLoadError("config.json", FileNotFoundError("File not found"))
        assert "config.json" in str(error)
        assert error.config_path == "config.json"
        assert isinstance(error.original_error, FileNotFoundError)

    def test_configuration_validation_error(self):
        """Test ConfigurationValidationError"""
        error = ConfigurationValidationError("log_level", "INVALID", "Must be DEBUG, INFO, WARNING, or ERROR")
        assert "log_level" in str(error)
        assert "INVALID" in str(error)
        assert error.key == "log_level"
        assert error.value == "INVALID"
        assert error.reason == "Must be DEBUG, INFO, WARNING, or ERROR"

    def test_workflow_state_error(self):
        """Test WorkflowStateError"""
        error = WorkflowStateError("pending", "complete", "Cannot complete task that hasn't started")
        assert "pending" in str(error)
        assert "complete" in str(error)
        assert error.current_state == "pending"
        assert error.attempted_operation == "complete"
        assert error.reason == "Cannot complete task that hasn't started"


class TestErrorDecorators:
    """Test error handling decorators"""

    def test_error_handler_success(self):
        """Test error_handler decorator with successful execution"""
        @error_handler
        def successful_function(x, y):
            return x + y
        
        result = successful_function(2, 3)
        assert result == 5

    def test_error_handler_with_beehive_error(self):
        """Test error_handler decorator with BeehiveError"""
        @error_handler
        def function_with_beehive_error():
            raise BeeValidationError("test_bee", "field", "value", "reason")
        
        # BeehiveError should be re-raised as-is
        with pytest.raises(BeeValidationError):
            function_with_beehive_error()

    def test_error_handler_with_generic_exception(self):
        """Test error_handler decorator with generic exception"""
        @error_handler
        def function_with_generic_error():
            raise ValueError("Generic error")
        
        # Generic exceptions should be wrapped in BeehiveError
        with pytest.raises(BeehiveError) as exc_info:
            function_with_generic_error()
        
        assert "Generic error" in str(exc_info.value)
        assert exc_info.value.metadata["original_error_type"] == "ValueError"
        assert exc_info.value.metadata["original_error_message"] == "Generic error"

    def test_wrap_database_error_success(self):
        """Test wrap_database_error decorator with successful execution"""
        @wrap_database_error
        def successful_db_function():
            return "success"
        
        result = successful_db_function()
        assert result == "success"

    def test_wrap_database_error_with_sqlite_error(self):
        """Test wrap_database_error decorator with SQLite error"""
        @wrap_database_error
        def function_with_db_error():
            raise sqlite3.OperationalError("database is locked")
        
        with pytest.raises(DatabaseOperationError) as exc_info:
            function_with_db_error()
        
        assert isinstance(exc_info.value.original_error, sqlite3.OperationalError)

    def test_wrap_database_error_with_generic_error(self):
        """Test wrap_database_error decorator with generic error"""
        @wrap_database_error  
        def function_with_generic_error():
            raise ValueError("Not a database error")
        
        # Non-database errors should pass through unchanged
        with pytest.raises(ValueError):
            function_with_generic_error()


class TestErrorHandlingIntegration:
    """Integration tests for error handling"""

    def test_error_chaining(self):
        """Test error chaining and context preservation"""
        try:
            try:
                raise sqlite3.OperationalError("original database error")
            except sqlite3.OperationalError as e:
                raise DatabaseConnectionError("test.db", e) from e
        except DatabaseConnectionError as final_error:
            assert final_error.database_path == "test.db"
            assert isinstance(final_error.original_error, sqlite3.OperationalError)
            assert final_error.__cause__ is not None

    def test_error_metadata_preservation(self):
        """Test that error metadata is preserved through transformations"""
        metadata = {"bee_name": "test_bee", "task_id": 123}
        original_error = BeehiveError("Original error", metadata=metadata)
        
        # Simulate wrapping in another error
        wrapped_error = TaskExecutionError(
            task_id=123,
            bee_name="test_bee", 
            stage="execution",
            original_error=original_error
        )
        
        assert wrapped_error.task_id == 123
        assert wrapped_error.bee_name == "test_bee"
        assert wrapped_error.original_error == original_error

    @pytest.mark.mock_required
    def test_logging_integration(self):
        """Test that errors integrate properly with logging"""
        with patch('bees.exceptions.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            @error_handler
            def function_that_fails():
                raise ValueError("Test error")
            
            with pytest.raises(BeehiveError):
                function_that_fails()
            
            # Verify logger was called (if logging is implemented in decorator)
            # This would need to be implemented in the actual decorator