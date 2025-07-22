#!/usr/bin/env python3
"""
Test module for logging system
Testing structured logging, BeehiveLogger, and log configuration
"""

import json
import logging
import pytest
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch, Mock

from bees.config import BeehiveConfig
from bees.logging_config import (
    BeehiveLogger,
    get_logger,
    setup_logging,
    StructuredFormatter,
)


class TestStructuredFormatter:
    """Test the StructuredFormatter class"""

    def test_structured_formatter_creation(self):
        """Test StructuredFormatter creation"""
        formatter = StructuredFormatter()
        assert formatter is not None

    def test_format_log_record(self):
        """Test formatting a log record"""
        formatter = StructuredFormatter()
        
        # Create a log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add some extra fields
        record.bee_name = "test_bee"
        record.task_id = 123
        
        formatted = formatter.format(record)
        
        # Should be valid JSON
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["logger_name"] == "test_logger"
        assert parsed["bee_name"] == "test_bee"
        assert parsed["task_id"] == 123
        assert "timestamp" in parsed

    def test_format_record_with_exception(self):
        """Test formatting a record with exception info"""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=(type(e), e, e.__traceback__)
            )
            
            formatted = formatter.format(record)
            parsed = json.loads(formatted)
            
            assert parsed["level"] == "ERROR"
            assert parsed["message"] == "Error occurred"
            assert "exception" in parsed
            assert "ValueError" in parsed["exception"]

    def test_format_record_with_extra_fields(self):
        """Test formatting record with various extra fields"""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=15,
            msg="Debug message",
            args=(),
            exc_info=None
        )
        
        # Add various extra fields
        record.event_type = "test_event"
        record.duration = 1.234
        record.success = True
        record.metadata = {"key": "value"}
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["event_type"] == "test_event"
        assert parsed["duration"] == 1.234
        assert parsed["success"] is True
        assert parsed["metadata"] == {"key": "value"}


class TestBeehiveLogger:
    """Test BeehiveLogger class"""

    def test_logger_creation(self):
        """Test BeehiveLogger creation"""
        config = BeehiveConfig()
        logger = BeehiveLogger("test_logger", config)
        
        assert logger.name == "test_logger"
        assert logger.config == config

    def test_logger_with_context(self):
        """Test logger with context information"""
        config = BeehiveConfig()
        context = {"bee_name": "test_bee", "session_id": "123"}
        logger = BeehiveLogger("test_logger", config, context)
        
        assert logger.context == context

    def test_log_event_method(self):
        """Test log_event method"""
        config = BeehiveConfig(structured_logging=True)
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = Mock()
            mock_get_logger.return_value = mock_logger_instance
            
            logger = BeehiveLogger("test_logger", config)
            
            logger.log_event("test_event", "Test message", task_id=123, success=True)
            
            # Verify the logger was called with proper arguments
            mock_logger_instance.info.assert_called_once()
            call_args = mock_logger_instance.info.call_args
            
            # Check that extra arguments were passed
            assert "extra" in call_args.kwargs
            extra = call_args.kwargs["extra"]
            assert extra["event_type"] == "test_event"
            assert extra["task_id"] == 123
            assert extra["success"] is True

    def test_log_event_with_different_levels(self):
        """Test log_event with different log levels"""
        config = BeehiveConfig()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = Mock()
            mock_get_logger.return_value = mock_logger_instance
            
            logger = BeehiveLogger("test_logger", config)
            
            # Test different log levels
            logger.log_event("error_event", "Error message", level="ERROR")
            logger.log_event("warning_event", "Warning message", level="WARNING")
            logger.log_event("debug_event", "Debug message", level="DEBUG")
            
            # Verify different methods were called
            mock_logger_instance.error.assert_called_once()
            mock_logger_instance.warning.assert_called_once()
            mock_logger_instance.debug.assert_called_once()

    def test_log_performance_method(self):
        """Test log_performance method"""
        config = BeehiveConfig()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = Mock()
            mock_get_logger.return_value = mock_logger_instance
            
            logger = BeehiveLogger("test_logger", config)
            
            logger.log_performance("database_query", 1.234, {"query_type": "SELECT"})
            
            mock_logger_instance.info.assert_called_once()
            call_args = mock_logger_instance.info.call_args
            extra = call_args.kwargs["extra"]
            
            assert extra["event_type"] == "performance"
            assert extra["operation"] == "database_query"
            assert extra["duration"] == 1.234
            assert extra["query_type"] == "SELECT"

    def test_log_error_method(self):
        """Test log_error method with exception"""
        config = BeehiveConfig()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = Mock()
            mock_get_logger.return_value = mock_logger_instance
            
            logger = BeehiveLogger("test_logger", config)
            
            test_error = ValueError("Test error")
            logger.log_error("Error occurred", error=test_error, task_id=123)
            
            mock_logger_instance.error.assert_called_once()
            call_args = mock_logger_instance.error.call_args
            extra = call_args.kwargs["extra"]
            
            assert extra["event_type"] == "error"
            assert extra["task_id"] == 123
            assert "error_type" in extra
            assert "error_message" in extra

    def test_context_logging(self):
        """Test that context is included in logs"""
        config = BeehiveConfig()
        context = {"bee_name": "test_bee", "session_id": "123"}
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = Mock()
            mock_get_logger.return_value = mock_logger_instance
            
            logger = BeehiveLogger("test_logger", config, context)
            logger.info("Test message")
            
            mock_logger_instance.info.assert_called_once()
            call_args = mock_logger_instance.info.call_args
            extra = call_args.kwargs["extra"]
            
            assert extra["bee_name"] == "test_bee"
            assert extra["session_id"] == "123"

    def test_standard_logging_methods(self):
        """Test standard logging methods (info, debug, warning, error, critical)"""
        config = BeehiveConfig()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = Mock()
            mock_get_logger.return_value = mock_logger_instance
            
            logger = BeehiveLogger("test_logger", config)
            
            logger.info("Info message")
            logger.debug("Debug message") 
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            mock_logger_instance.info.assert_called()
            mock_logger_instance.debug.assert_called()
            mock_logger_instance.warning.assert_called()
            mock_logger_instance.error.assert_called()
            mock_logger_instance.critical.assert_called()


class TestLoggerConfiguration:
    """Test logger configuration functions"""

    def test_configure_logging_structured(self):
        """Test setup_logging with structured logging enabled"""
        config = BeehiveConfig(
            structured_logging=True,
            log_level="DEBUG",
            log_file_path="test.log"
        )
        
        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(config)
            
            # Verify basicConfig was called
            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args.kwargs
            
            assert call_kwargs["level"] == logging.DEBUG
            assert call_kwargs["format"] is not None

    def test_configure_logging_plain(self):
        """Test setup_logging with plain text logging"""
        config = BeehiveConfig(
            structured_logging=False,
            log_level="INFO"
        )
        
        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(config)
            
            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args.kwargs
            
            assert call_kwargs["level"] == logging.INFO

    def test_get_logger_function(self):
        """Test get_logger function"""
        config = BeehiveConfig()
        
        logger = get_logger("test_logger", config)
        
        assert isinstance(logger, BeehiveLogger)
        assert logger.name == "test_logger"

    def test_get_logger_with_context(self):
        """Test get_logger with context"""
        config = BeehiveConfig()
        context = {"bee_name": "test_bee"}
        
        logger = get_logger("test_logger", config, context)
        
        assert isinstance(logger, BeehiveLogger)
        assert logger.context == context

    @pytest.mark.mock_required
    def test_file_logging_configuration(self):
        """Test configuration for file logging"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            config = BeehiveConfig(
                log_file_path=str(log_file),
                structured_logging=True
            )
            
            with patch('logging.basicConfig') as mock_basic_config, \
                 patch('logging.FileHandler') as mock_file_handler:
                
                setup_logging(config)
                
                # Should configure file handler
                mock_basic_config.assert_called_once()


class TestLoggingIntegration:
    """Integration tests for logging system"""

    def test_end_to_end_structured_logging(self):
        """Test end-to-end structured logging"""
        # Create a string stream to capture log output
        log_stream = StringIO()
        
        config = BeehiveConfig(structured_logging=True, log_level="DEBUG")
        
        # Configure logging to use our stream
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(StructuredFormatter())
        
        logger = get_logger("integration_test", config)
        
        # Get the underlying logger and add our handler
        underlying_logger = logging.getLogger(f"beehive.integration_test")
        underlying_logger.handlers.clear()  # Remove default handlers
        underlying_logger.addHandler(handler)
        underlying_logger.setLevel(logging.DEBUG)
        
        # Log some events
        logger.log_event("test_event", "Test message", task_id=123)
        logger.log_performance("test_operation", 0.5, {"success": True})
        
        # Get logged output
        log_output = log_stream.getvalue()
        
        # Should have two log lines
        lines = [line for line in log_output.strip().split('\n') if line]
        assert len(lines) >= 1
        
        # Parse first log line
        first_log = json.loads(lines[0])
        assert first_log["event_type"] == "test_event"
        assert first_log["message"] == "Test message"
        assert first_log["task_id"] == 123

    def test_error_logging_with_exception_info(self):
        """Test error logging with actual exception"""
        log_stream = StringIO()
        config = BeehiveConfig(structured_logging=True)
        
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(StructuredFormatter())
        
        logger = get_logger("error_test", config)
        
        underlying_logger = logging.getLogger(f"beehive.error_test")
        underlying_logger.handlers.clear()
        underlying_logger.addHandler(handler)
        underlying_logger.setLevel(logging.ERROR)
        
        # Create and log an actual exception
        try:
            raise ValueError("Test exception for logging")
        except ValueError as e:
            logger.log_error("Exception occurred", error=e, task_id=456)
        
        log_output = log_stream.getvalue()
        log_data = json.loads(log_output.strip())
        
        assert log_data["event_type"] == "error"
        assert log_data["task_id"] == 456
        assert "error_type" in log_data
        assert "error_message" in log_data

    def test_logging_performance_under_load(self):
        """Test logging performance with many messages"""
        config = BeehiveConfig(structured_logging=True)
        logger = get_logger("performance_test", config)
        
        # This shouldn't raise any exceptions
        for i in range(100):
            logger.log_event(f"event_{i}", f"Message {i}", counter=i)

    def test_logging_with_different_configurations(self):
        """Test logging behavior with different configurations"""
        # Test with structured logging disabled
        config_plain = BeehiveConfig(structured_logging=False)
        logger_plain = get_logger("plain_test", config_plain)
        
        # Should not raise exception
        logger_plain.info("Plain text log message")
        
        # Test with structured logging enabled
        config_structured = BeehiveConfig(structured_logging=True)
        logger_structured = get_logger("structured_test", config_structured)
        
        # Should not raise exception
        logger_structured.log_event("structured_event", "Structured log message")