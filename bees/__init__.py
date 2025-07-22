"""
Beehive Multi-Agent System
Issue #22: コード品質・エラーハンドリング強化

Claude Multi-Agent Development System (Beehive) パッケージ
"""

from .base_bee import BaseBee
from .config import BeehiveConfig, get_config, set_config
from .exceptions import (
    BeehiveError,
    BeeValidationError,
    CommunicationError,
    ConfigurationError,
    ConfigurationLoadError,
    ConfigurationValidationError,
    DatabaseConnectionError,
    DatabaseError,
    DatabaseOperationError,
    MessageSendError,
    TaskExecutionError,
    TaskValidationError,
    TmuxSessionError,
    ValidationError,
    WorkflowError,
    WorkflowStateError,
)
from .logging_config import BeehiveLogger, get_logger, setup_logging

__version__ = "0.1.0"
__author__ = "Beehive Team"

__all__ = [
    # Main classes
    "BaseBee",
    "BeehiveConfig",
    "BeehiveLogger",
    # Configuration management
    "get_config",
    "set_config",
    "get_logger",
    "setup_logging",
    # Exceptions
    "BeehiveError",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseOperationError",
    "CommunicationError",
    "TmuxSessionError",
    "MessageSendError",
    "ValidationError",
    "TaskValidationError",
    "BeeValidationError",
    "ConfigurationError",
    "ConfigurationLoadError",
    "ConfigurationValidationError",
    "WorkflowError",
    "TaskExecutionError",
    "WorkflowStateError",
]
