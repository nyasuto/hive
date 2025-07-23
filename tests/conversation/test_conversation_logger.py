#!/usr/bin/env python3
"""
Comprehensive unit tests for ConversationLogger
"""

import json
import pytest
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from bees.conversation_logger import ConversationLogger
from bees.exceptions import DatabaseConnectionError, DatabaseOperationError
from tests.utils.database_helpers import TestDatabaseHelper, test_db_helper, test_config, mock_logger
from tests.utils.mock_helpers import ConversationTestMocks


class TestConversationLoggerInit:
    """Test ConversationLogger initialization"""

    def test_init_with_valid_config(self, test_config):
        """Test initialization with valid configuration"""
        logger = ConversationLogger(test_config)
        assert logger.config == test_config
        assert logger.hive_db_path == Path(test_config.hive_db_path)

    def test_init_with_default_config(self, test_db_helper):
        """Test initialization with default configuration"""
        with patch('bees.conversation_logger.get_config') as mock_get_config:
            mock_get_config.return_value = test_db_helper.get_test_config()
            logger = ConversationLogger()
            assert logger.config is not None
            mock_get_config.assert_called_once()

    def test_init_database_not_found(self, test_config):
        """Test initialization fails when database doesn't exist"""
        test_config.hive_db_path = "/nonexistent/path/db.sqlite"
        
        with pytest.raises(DatabaseConnectionError):
            ConversationLogger(test_config)

    def test_init_invalid_database(self, tmp_path, test_config):
        """Test initialization fails with corrupted database"""
        # Create invalid database file
        invalid_db = tmp_path / "invalid.db"
        invalid_db.write_text("invalid database content")
        test_config.hive_db_path = str(invalid_db)

        with pytest.raises(DatabaseConnectionError):
            ConversationLogger(test_config)


class TestConversationLoggerBeekeeperInstructions:
    """Test beekeeper instruction logging"""

    def test_log_beekeeper_instruction_basic(self, test_config):
        """Test basic beekeeper instruction logging"""
        logger = ConversationLogger(test_config)
        
        instruction = "テスト指示: issue 47を実装してください"
        message_id = logger.log_beekeeper_instruction(
            instruction=instruction,
            target_bee="developer",
            priority="high"
        )
        
        assert isinstance(message_id, int)
        assert message_id > 0
        
        # Verify in database
        with logger._get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM bee_messages WHERE message_id = ?", 
                (message_id,)
            ).fetchone()
            
            assert row is not None
            assert row["from_bee"] == "beekeeper"
            assert row["to_bee"] == "developer"
            assert row["message_type"] == "instruction"
            assert row["content"] == instruction
            assert row["priority"] == "high"
            assert row["sender_cli_used"] == 1  # True
            assert row["conversation_id"] is not None

    def test_log_beekeeper_instruction_with_metadata(self, test_config):
        """Test beekeeper instruction logging with metadata"""
        logger = ConversationLogger(test_config)
        
        metadata = {
            "instruction_type": "task_assignment",
            "source": "console",
            "timestamp": "2025-01-01T12:00:00"
        }
        
        message_id = logger.log_beekeeper_instruction(
            instruction="メタデータ付きテスト",
            target_bee="all",
            priority="normal",
            metadata=metadata
        )
        
        # Verify metadata storage
        with logger._get_db_connection() as conn:
            row = conn.execute(
                "SELECT metadata FROM bee_messages WHERE message_id = ?",
                (message_id,)
            ).fetchone()
            
            stored_metadata = json.loads(row["metadata"])
            assert stored_metadata == metadata

    def test_log_beekeeper_instruction_auto_task_creation(self, test_config):
        """Test automatic task creation from beekeeper instruction"""
        logger = ConversationLogger(test_config)
        
        # Instruction with task keywords
        instruction = "新機能を実装してください"
        message_id = logger.log_beekeeper_instruction(
            instruction=instruction,
            target_bee="developer",
            priority="high"
        )
        
        # Verify task was created
        with logger._get_db_connection() as conn:
            task_row = conn.execute(
                "SELECT * FROM tasks WHERE created_by = 'beekeeper' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            
            assert task_row is not None
            assert task_row["title"] == instruction
            assert task_row["description"] == instruction
            assert task_row["assigned_to"] == "developer"
            assert task_row["created_by"] == "beekeeper"
            
            # Check metadata
            metadata = json.loads(task_row["metadata"])
            assert metadata["auto_generated"] is True
            assert "conversation_id" in metadata

    def test_log_beekeeper_instruction_no_task_creation(self, test_config):
        """Test no task creation for non-task instructions"""
        logger = ConversationLogger(test_config)
        
        # Instruction without task keywords
        instruction = "進捗はどうですか？"
        logger.log_beekeeper_instruction(
            instruction=instruction,
            target_bee="all",
            priority="normal"
        )
        
        # Verify no task was created
        with logger._get_db_connection() as conn:
            task_count = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE created_by = 'beekeeper'"
            ).fetchone()[0]
            
            assert task_count == 0

    def test_log_beekeeper_instruction_database_error(self, test_config):
        """Test database error handling"""
        logger = ConversationLogger(test_config)
        
        # Mock database error
        with patch.object(logger, '_get_db_connection') as mock_conn:
            mock_conn.side_effect = sqlite3.Error("Database error")
            
            with pytest.raises(DatabaseOperationError):
                logger.log_beekeeper_instruction(
                    instruction="テスト",
                    target_bee="developer"
                )


class TestConversationLoggerBeeConversations:
    """Test bee conversation logging"""

    def test_log_bee_conversation_basic(self, test_config):
        """Test basic bee conversation logging"""
        logger = ConversationLogger(test_config)
        
        message_id = logger.log_bee_conversation(
            from_bee="queen",
            to_bee="developer",
            content="タスクを割り当てました",
            message_type="task_update",
            sender_cli_used=True
        )
        
        assert isinstance(message_id, int)
        
        # Verify in database
        with logger._get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM bee_messages WHERE message_id = ?",
                (message_id,)
            ).fetchone()
            
            assert row["from_bee"] == "queen"
            assert row["to_bee"] == "developer"
            assert row["message_type"] == "task_update"
            assert row["content"] == "タスクを割り当てました"
            assert row["sender_cli_used"] == 1
            assert row["conversation_id"] is not None

    def test_log_bee_conversation_with_task_id(self, test_config):
        """Test bee conversation logging with task ID"""
        logger = ConversationLogger(test_config)
        
        task_id = str(uuid.uuid4())
        conversation_id = str(uuid.uuid4())
        
        message_id = logger.log_bee_conversation(
            from_bee="developer",
            to_bee="qa", 
            content="作業完了しました",
            task_id=task_id,
            conversation_id=conversation_id,
            sender_cli_used=True
        )
        
        # Verify task_id and conversation_id
        with logger._get_db_connection() as conn:
            row = conn.execute(
                "SELECT task_id, conversation_id FROM bee_messages WHERE message_id = ?",
                (message_id,)
            ).fetchone()
            
            assert row["task_id"] == task_id
            assert row["conversation_id"] == conversation_id

    def test_log_bee_conversation_cli_violation_warning(self, test_config, mock_logger):
        """Test CLI violation warning"""
        with patch('bees.conversation_logger.get_logger', return_value=mock_logger):
            logger = ConversationLogger(test_config)
            
            logger.log_bee_conversation(
                from_bee="developer",
                to_bee="qa",
                content="直接メッセージ",
                sender_cli_used=False
            )
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Non-CLI communication detected" in warning_call

    def test_log_bee_conversation_auto_conversation_id(self, test_config):
        """Test automatic conversation ID generation"""
        logger = ConversationLogger(test_config)
        
        message_id = logger.log_bee_conversation(
            from_bee="queen",
            to_bee="developer",
            content="テストメッセージ"
        )
        
        # Verify conversation_id was generated
        with logger._get_db_connection() as conn:
            row = conn.execute(
                "SELECT conversation_id FROM bee_messages WHERE message_id = ?",
                (message_id,)
            ).fetchone()
            
            assert row["conversation_id"] is not None
            # Should be valid UUID format
            uuid.UUID(row["conversation_id"])


class TestConversationLoggerHistoryAndStats:
    """Test conversation history and statistics"""

    def test_get_conversation_history_basic(self, test_config, test_db_helper):
        """Test basic conversation history retrieval"""
        # Setup test data
        test_data = {
            "messages": [
                {
                    "from_bee": "beekeeper",
                    "to_bee": "developer", 
                    "content": "指示1",
                    "message_type": "instruction",
                    "conversation_id": "conv-1"
                },
                {
                    "from_bee": "queen",
                    "to_bee": "developer",
                    "content": "メッセージ1", 
                    "message_type": "task_update",
                    "conversation_id": "conv-2"
                }
            ]
        }
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        history = logger.get_conversation_history(limit=10)
        
        assert len(history) == 2
        assert history[0]["content"] in ["指示1", "メッセージ1"]  # Order may vary

    def test_get_conversation_history_filtered(self, test_config, test_db_helper):
        """Test filtered conversation history"""
        # Setup test data with specific conversation ID
        conv_id = "test-conversation-1"
        test_data = {
            "messages": [
                {
                    "from_bee": "queen",
                    "to_bee": "developer",
                    "content": "関連メッセージ1",
                    "conversation_id": conv_id
                },
                {
                    "from_bee": "developer", 
                    "to_bee": "queen",
                    "content": "関連メッセージ2",
                    "conversation_id": conv_id
                },
                {
                    "from_bee": "qa",
                    "to_bee": "developer",
                    "content": "無関係メッセージ",
                    "conversation_id": "other-conv"
                }
            ]
        }
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        history = logger.get_conversation_history(conversation_id=conv_id)
        
        assert len(history) == 2
        for msg in history:
            assert msg["conversation_id"] == conv_id

    def test_get_conversation_history_exclude_beekeeper(self, test_config, test_db_helper):
        """Test conversation history excluding beekeeper"""
        test_data = {
            "messages": [
                {
                    "from_bee": "beekeeper",
                    "to_bee": "developer",
                    "content": "beekeeperメッセージ"
                },
                {
                    "from_bee": "queen",
                    "to_bee": "developer", 
                    "content": "bee間メッセージ"
                }
            ]
        }
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        history = logger.get_conversation_history(include_beekeeper=False)
        
        assert len(history) == 1
        assert history[0]["from_bee"] == "queen"

    def test_get_conversation_stats_basic(self, test_config, test_db_helper):
        """Test basic conversation statistics"""
        test_data = {
            "messages": [
                {
                    "from_bee": "beekeeper",
                    "to_bee": "developer",
                    "content": "指示1",
                    "sender_cli_used": True,
                    "conversation_id": "conv-1"
                },
                {
                    "from_bee": "queen",
                    "to_bee": "developer",
                    "content": "メッセージ1",
                    "sender_cli_used": True,
                    "conversation_id": "conv-2"
                },
                {
                    "from_bee": "developer",
                    "to_bee": "qa",
                    "content": "メッセージ2",
                    "sender_cli_used": False,
                    "conversation_id": "conv-3"
                }
            ]
        }
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        stats = logger.get_conversation_stats()
        
        assert stats["total_messages"] == 3
        assert stats["beekeeper_instructions"] == 1
        assert stats["bee_conversations"] == 2
        assert stats["sender_cli_usage_rate"] == round(2/3 * 100, 2)  # 66.67%
        assert stats["active_conversations"] == 3

    def test_get_conversation_stats_empty_database(self, test_config):
        """Test conversation statistics with empty database"""
        logger = ConversationLogger(test_config)
        stats = logger.get_conversation_stats()
        
        assert stats["total_messages"] == 0
        assert stats["beekeeper_instructions"] == 0
        assert stats["bee_conversations"] == 0
        assert stats["sender_cli_usage_rate"] == 0
        assert stats["active_conversations"] == 0


class TestConversationLoggerSenderCLIEnforcement:
    """Test sender CLI enforcement features"""

    def test_enforce_sender_cli_usage_violations(self, test_config, test_db_helper):
        """Test detection of sender CLI violations"""
        # Setup violations data
        test_data = {
            "messages": [
                {
                    "from_bee": "developer",
                    "to_bee": "qa",
                    "content": "違反メッセージ1",
                    "sender_cli_used": False
                },
                {
                    "from_bee": "qa",
                    "to_bee": "developer", 
                    "content": "違反メッセージ2",
                    "sender_cli_used": False
                },
                {
                    "from_bee": "queen",
                    "to_bee": "developer",
                    "content": "正常メッセージ",
                    "sender_cli_used": True
                },
                {
                    "from_bee": "beekeeper",  # Should be excluded
                    "to_bee": "developer",
                    "content": "beekeeperメッセージ",
                    "sender_cli_used": False
                }
            ]
        }
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        violations = logger.enforce_sender_cli_usage()
        
        # Should find 2 violations (excluding beekeeper)
        assert len(violations) == 2
        for violation in violations:
            assert violation["sender_cli_used"] == 0  # False
            assert violation["from_bee"] != "beekeeper"
            assert violation["to_bee"] != "beekeeper"

    def test_enforce_sender_cli_usage_no_violations(self, test_config, test_db_helper):
        """Test no violations scenario"""
        test_data = {
            "messages": [
                {
                    "from_bee": "queen",
                    "to_bee": "developer",
                    "content": "正常メッセージ1",
                    "sender_cli_used": True
                },
                {
                    "from_bee": "developer",
                    "to_bee": "qa",
                    "content": "正常メッセージ2", 
                    "sender_cli_used": True
                }
            ]
        }
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        violations = logger.enforce_sender_cli_usage()
        
        assert len(violations) == 0


class TestConversationLoggerTaskGeneration:
    """Test automatic task generation features"""

    @pytest.mark.parametrize("keyword,expected", [
        ("実装してください", True),
        ("開発を進めてください", True), 
        ("作成してください", True),
        ("修正してください", True),
        ("テストしてください", True),
        ("デバッグしてください", True),
        ("implement the feature", True),
        ("develop new functionality", True),
        ("create a new component", True),
        ("fix the bug", True),
        ("test the system", True),
        ("debug the issue", True),
        ("作って", True),
        ("直して", True),
        ("書いて", True),
        ("やって", True),
        ("進捗を確認してください", False),
        ("状況はどうですか", False),
        ("報告してください", False),
    ])
    def test_task_keyword_detection(self, test_config, keyword, expected):
        """Test task keyword detection"""
        logger = ConversationLogger(test_config)
        
        message_id = logger.log_beekeeper_instruction(
            instruction=keyword,
            target_bee="developer",
            priority="normal"
        )
        
        # Check if task was created
        with logger._get_db_connection() as conn:
            task_count = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE created_by = 'beekeeper'"
            ).fetchone()[0]
            
            if expected:
                assert task_count == 1
            else:
                assert task_count == 0

    def test_extract_task_title_truncation(self, test_config):
        """Test task title extraction and truncation"""
        logger = ConversationLogger(test_config)
        
        # Long instruction
        long_instruction = "これは非常に長い指示です。" * 10 + "実装してください"
        
        logger.log_beekeeper_instruction(
            instruction=long_instruction,
            target_bee="developer",
            priority="normal"
        )
        
        # Check title truncation
        with logger._get_db_connection() as conn:
            task_row = conn.execute(
                "SELECT title FROM tasks WHERE created_by = 'beekeeper'"
            ).fetchone()
            
            assert len(task_row["title"]) <= 50
            assert task_row["title"].endswith("...")

    def test_task_assignment_all_target(self, test_config):
        """Test task assignment when target is 'all'"""
        logger = ConversationLogger(test_config)
        
        logger.log_beekeeper_instruction(
            instruction="実装してください",
            target_bee="all",  # Should result in NULL assignment
            priority="normal"
        )
        
        # Check task assignment
        with logger._get_db_connection() as conn:
            task_row = conn.execute(
                "SELECT assigned_to FROM tasks WHERE created_by = 'beekeeper'"
            ).fetchone()
            
            assert task_row["assigned_to"] is None


class TestConversationLoggerErrorHandling:
    """Test error handling scenarios"""

    def test_database_connection_error_in_stats(self, test_config):
        """Test database error handling in stats"""
        logger = ConversationLogger(test_config)
        
        with patch.object(logger, '_get_db_connection') as mock_conn:
            mock_conn.side_effect = sqlite3.Error("Connection failed")
            
            stats = logger.get_conversation_stats()
            assert stats == {}

    def test_database_error_in_history(self, test_config):
        """Test database error handling in history"""
        logger = ConversationLogger(test_config)
        
        with patch.object(logger, '_get_db_connection') as mock_conn:
            mock_conn.side_effect = sqlite3.Error("Query failed")
            
            history = logger.get_conversation_history()
            assert history == []

    def test_task_creation_failure(self, test_config, mock_logger):
        """Test task creation failure handling"""
        with patch('bees.conversation_logger.get_logger', return_value=mock_logger):
            logger = ConversationLogger(test_config)
            
            # Mock task creation failure
            with patch.object(logger, '_get_db_connection') as mock_conn:
                mock_conn.return_value.__enter__.return_value.execute.side_effect = [
                    Mock(lastrowid=1),  # First call succeeds (message insert)
                    sqlite3.Error("Task insert failed")  # Second call fails (task insert)
                ]
                mock_conn.return_value.__enter__.return_value.commit.return_value = None
                
                # This should not raise an exception
                logger.log_beekeeper_instruction(
                    instruction="実装してください",
                    target_bee="developer"
                )
                
                # Should log warning about task creation failure
                mock_logger.warning.assert_called_once()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert "Failed to auto-generate task" in warning_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])