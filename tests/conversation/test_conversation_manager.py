#!/usr/bin/env python3
"""
Comprehensive unit tests for ConversationManager
"""

import json
import pytest
import subprocess
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call

from bees.conversation_manager import ConversationManager
from bees.conversation_logger import ConversationLogger
from tests.utils.database_helpers import TestDatabaseHelper, test_db_helper, test_config, mock_logger
from tests.utils.mock_helpers import ConversationTestMocks


class TestConversationManagerInit:
    """Test ConversationManager initialization"""

    def test_init_with_config(self, test_config, mock_logger):
        """Test initialization with provided config"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            assert manager.config == test_config
            assert isinstance(manager.conversation_logger, ConversationLogger)
            assert manager._bee_communication_states == {}
            
            # Verify initialization log
            mock_logger.info.assert_called_with("ConversationManager initialized")

    def test_init_with_default_config(self, test_db_helper, mock_logger):
        """Test initialization with default config"""
        with patch('bees.conversation_manager.get_config') as mock_get_config:
            mock_get_config.return_value = test_db_helper.get_test_config()
            
            with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
                manager = ConversationManager()
                
                assert manager.config is not None
                mock_get_config.assert_called_once()


class TestConversationManagerBeekeeperInput:
    """Test beekeeper input interception"""

    def test_intercept_beekeeper_input_basic(self, test_config, mock_logger):
        """Test basic beekeeper input interception"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            # Mock the logger call to avoid database issues
            with patch.object(manager.conversation_logger, 'log_beekeeper_instruction', return_value=123):
                with patch.object(manager, '_send_via_sender_cli', return_value=True):
                    result = manager.intercept_beekeeper_input(
                        input_text="テスト指示: 実装してください",
                        target_bee="developer"
                    )
                    
                    assert result is True
                    mock_logger.info.assert_called()

    def test_classify_beekeeper_input_task_assignment(self, test_config):
        """Test beekeeper input classification - task assignment"""
        manager = ConversationManager(test_config)
        
        test_cases = [
            ("実装してください", "task_assignment"),
            ("開発を進めてください", "task_assignment"), 
            ("作成してください", "task_assignment"),
            ("implement new feature", "task_assignment"),
            ("develop the component", "task_assignment"),
            ("create a new module", "task_assignment"),
        ]
        
        for input_text, expected in test_cases:
            result = manager._classify_beekeeper_input(input_text)
            assert result == expected, f"Failed for input: {input_text}"

    def test_classify_beekeeper_input_bug_fix(self, test_config):
        """Test beekeeper input classification - bug fix"""
        manager = ConversationManager(test_config)
        
        test_cases = [
            ("修正してください", "bug_fix"),
            ("デバッグしてください", "bug_fix"),
            ("fix the bug", "bug_fix"),
            ("debug the issue", "bug_fix"),
            ("bugを直してください", "bug_fix"),
        ]
        
        for input_text, expected in test_cases:
            result = manager._classify_beekeeper_input(input_text)
            assert result == expected

    def test_classify_beekeeper_input_testing(self, test_config):
        """Test beekeeper input classification - testing"""
        manager = ConversationManager(test_config)
        
        test_cases = [
            ("テストしてください", "testing"),
            ("test the system", "testing"),
            ("qa検証をお願いします", "testing"),
            ("品質チェックしてください", "testing"),
        ]
        
        for input_text, expected in test_cases:
            result = manager._classify_beekeeper_input(input_text)
            assert result == expected

    def test_classify_beekeeper_input_status_inquiry(self, test_config):
        """Test beekeeper input classification - status inquiry"""
        manager = ConversationManager(test_config)
        
        test_cases = [
            ("進捗はどうですか？", "status_inquiry"),
            ("状況を教えてください", "status_inquiry"),
            ("check the status", "status_inquiry"),
            ("progress report please", "status_inquiry"),
        ]
        
        for input_text, expected in test_cases:
            result = manager._classify_beekeeper_input(input_text)
            assert result == expected

    def test_classify_beekeeper_input_control_command(self, test_config):
        """Test beekeeper input classification - control command"""
        manager = ConversationManager(test_config)
        
        test_cases = [
            ("停止してください", "control_command"),
            ("中止してください", "control_command"),
            ("stop the process", "control_command"),
            ("cancel the task", "control_command"),
        ]
        
        for input_text, expected in test_cases:
            result = manager._classify_beekeeper_input(input_text)
            assert result == expected

    def test_determine_priority_urgent(self, test_config):
        """Test priority determination - urgent"""
        manager = ConversationManager(test_config)
        
        test_cases = [
            ("緊急で実装してください", "urgent"),
            ("急いで修正してください", "urgent"),
            ("urgent fix needed", "urgent"),
            ("critical bug fix", "urgent"),
            ("immediately implement", "urgent"),
        ]
        
        for input_text, expected in test_cases:
            result = manager._determine_priority(input_text, "task_assignment")
            assert result == expected

    def test_determine_priority_high(self, test_config):
        """Test priority determination - high"""
        manager = ConversationManager(test_config)
        
        test_cases = [
            ("重要な実装です", "high"),
            ("高優先度でお願いします", "high"),
            ("high priority task", "high"),
            ("important feature", "high"),
        ]
        
        for input_text, expected in test_cases:
            result = manager._determine_priority(input_text, "task_assignment")
            assert result == expected

    def test_determine_priority_by_instruction_type(self, test_config):
        """Test priority determination by instruction type"""
        manager = ConversationManager(test_config)
        
        # Bug fix should be high priority
        result = manager._determine_priority("バグを修正してください", "bug_fix")
        assert result == "high"
        
        # Control command should be high priority
        result = manager._determine_priority("停止してください", "control_command")
        assert result == "high"
        
        # Task assignment should be normal priority by default
        result = manager._determine_priority("実装してください", "task_assignment")
        assert result == "normal"

    def test_intercept_single_target(self, test_config, mock_logger):
        """Test interception with single target bee"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            with patch.object(manager.conversation_logger, 'log_beekeeper_instruction', return_value=456):
                with patch.object(manager, '_send_via_sender_cli', return_value=True) as mock_send:
                    result = manager.intercept_beekeeper_input(
                        input_text="テスト指示",
                        target_bee="developer"
                    )
                    
                    assert result is True
                    mock_send.assert_called_once_with(
                        from_bee="beekeeper",
                        to_bee="developer",
                        message_type="instruction",
                        content="テスト指示",
                        subject="Beekeeper Instruction"
                    )

    def test_intercept_all_targets(self, test_config, mock_logger):
        """Test interception with all targets"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            with patch.object(manager.conversation_logger, 'log_beekeeper_instruction', return_value=789):
                with patch.object(manager, '_send_via_sender_cli', return_value=True) as mock_send:
                    result = manager.intercept_beekeeper_input(
                        input_text="全員への指示",
                        target_bee="all"
                    )
                    
                    assert result is True
                    # Should call _send_via_sender_cli for each bee
                    expected_calls = [
                        call(from_bee="beekeeper", to_bee="queen", message_type="instruction", 
                             content="全員への指示", subject="Beekeeper Instruction"),
                        call(from_bee="beekeeper", to_bee="developer", message_type="instruction",
                             content="全員への指示", subject="Beekeeper Instruction"),
                        call(from_bee="beekeeper", to_bee="qa", message_type="instruction",
                             content="全員への指示", subject="Beekeeper Instruction"),
                        call(from_bee="beekeeper", to_bee="analyst", message_type="instruction",
                             content="全員への指示", subject="Beekeeper Instruction")
                    ]
                    mock_send.assert_has_calls(expected_calls, any_order=True)

    def test_intercept_error_handling(self, test_config, mock_logger):
        """Test error handling in input interception"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            # Mock error in logging
            with patch.object(manager.conversation_logger, 'log_beekeeper_instruction', 
                            side_effect=Exception("Logging error")):
                result = manager.intercept_beekeeper_input(
                    input_text="テスト指示",
                    target_bee="developer"
                )
                
                assert result is False
                mock_logger.error.assert_called_once()


class TestConversationManagerSenderCLI:
    """Test sender CLI functionality"""

    def test_send_via_sender_cli_success(self, test_config):
        """Test successful sender CLI message sending"""
        manager = ConversationManager(test_config)
        
        with ConversationTestMocks() as mocks:
            mocks.setup_successful_cli_send()
            
            with patch.object(manager, 'log_bee_message', return_value=123):
                result = manager._send_via_sender_cli(
                    from_bee="beekeeper",
                    to_bee="developer",
                    message_type="instruction",
                    content="テストメッセージ",
                    subject="テスト件名"
                )
                
                assert result is True

    def test_send_via_sender_cli_unknown_bee(self, test_config, mock_logger):
        """Test sender CLI with unknown target bee"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            result = manager._send_via_sender_cli(
                from_bee="beekeeper",
                to_bee="unknown_bee",
                message_type="instruction",
                content="テストメッセージ",
                subject="テスト件名"
            )
            
            assert result is False
            mock_logger.warning.assert_called_with("Unknown target bee: unknown_bee")

    def test_send_via_sender_cli_command_failure(self, test_config, mock_logger):
        """Test sender CLI command failure"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            with ConversationTestMocks() as mocks:
                mocks.setup_failed_cli_send()
                
                result = manager._send_via_sender_cli(
                    from_bee="beekeeper",
                    to_bee="developer",
                    message_type="instruction",
                    content="テストメッセージ",
                    subject="テスト件名"
                )
                
                assert result is False
                mock_logger.error.assert_called()

    def test_send_via_sender_cli_timeout(self, test_config, mock_logger):
        """Test sender CLI timeout"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("cmd", 30)):
                result = manager._send_via_sender_cli(
                    from_bee="beekeeper",
                    to_bee="developer",
                    message_type="instruction",
                    content="テストメッセージ",
                    subject="テスト件名"
                )
                
                assert result is False
                mock_logger.error.assert_called_with("Sender CLI command timed out")

    def test_send_via_sender_cli_message_structure(self, test_config):
        """Test sender CLI message structure"""
        manager = ConversationManager(test_config)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            with patch.object(manager, 'log_bee_message', return_value=123):
                manager._send_via_sender_cli(
                    from_bee="beekeeper",
                    to_bee="developer",
                    message_type="instruction",
                    content="テストメッセージ\n複数行\nテスト",
                    subject="テスト件名",
                    task_id="test-task-123"
                )
                
                # Verify command structure
                mock_run.assert_called_once()
                call_args = mock_run.call_args[1]
                cmd = mock_run.call_args[0][0]
                
                # Check command components
                assert "python" in cmd
                assert "-m" in cmd
                assert "bees.cli" in cmd
                assert "send" in cmd
                assert "test_beehive" in cmd  # session name
                assert "1" in cmd  # pane id for developer
                
                # Check message content structure
                message_content = next(arg for arg in cmd if "MESSAGE FROM BEEKEEPER" in arg)
                assert "## 📨 MESSAGE FROM BEEKEEPER" in message_content
                assert "**Type:** instruction" in message_content
                assert "**Subject:** テスト件名" in message_content
                assert "**Task ID:** test-task-123" in message_content
                assert "テストメッセージ" in message_content
                assert "複数行" in message_content


class TestConversationManagerViolationHandling:
    """Test sender CLI violation handling"""

    def test_handle_sender_cli_violations_basic(self, test_config, mock_logger):
        """Test basic violation handling"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            violations = [
                {
                    "message_id": 123,
                    "from_bee": "developer",
                    "to_bee": "qa",
                    "content": "直接メッセージ"
                }
            ]
            
            with patch.object(manager, '_send_via_sender_cli', return_value=True):
                manager._handle_sender_cli_violations(violations)
                
                # Verify warning was logged
                mock_logger.warning.assert_called_once()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert "Sender CLI violation detected" in warning_msg
                assert "developer → qa" in warning_msg

    def test_handle_multiple_violations(self, test_config, mock_logger):
        """Test handling multiple violations"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            violations = [
                {"message_id": 123, "from_bee": "developer", "to_bee": "qa", "content": "msg1"},
                {"message_id": 124, "from_bee": "qa", "to_bee": "developer", "content": "msg2"},
            ]
            
            with patch.object(manager, '_send_via_sender_cli', return_value=True) as mock_send:
                manager._handle_sender_cli_violations(violations)
                
                # Should send warning to each violating bee
                assert mock_send.call_count == 2
                
                # Check warning messages were sent to violating bees
                calls = mock_send.call_args_list
                sent_to_bees = {call[1]['to_bee'] for call in calls}
                assert sent_to_bees == {"developer", "qa"}

    def test_violation_warning_message_content(self, test_config):
        """Test violation warning message content"""
        manager = ConversationManager(test_config)
        
        violations = [
            {
                "message_id": 123,
                "from_bee": "developer", 
                "to_bee": "qa",
                "content": "直接メッセージ"
            }
        ]
        
        with patch.object(manager, '_send_via_sender_cli') as mock_send:
            manager._handle_sender_cli_violations(violations)
            
            # Verify warning message content
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            
            assert call_kwargs['from_bee'] == "system"
            assert call_kwargs['to_bee'] == "developer"
            assert call_kwargs['message_type'] == "alert"
            assert call_kwargs['subject'] == "Communication Protocol Violation"
            
            content = call_kwargs['content']
            assert "COMMUNICATION PROTOCOL VIOLATION" in content
            assert "message (ID: 123)" in content
            assert "sender CLI system" in content


class TestConversationManagerCommunicationHealth:
    """Test communication health monitoring"""

    def test_check_bee_communication_health_normal(self, test_config, mock_logger):
        """Test communication health check - normal scenario"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            # Mock good CLI usage rate
            with patch.object(manager.conversation_logger, 'get_conversation_stats') as mock_stats:
                mock_stats.return_value = {"sender_cli_usage_rate": 98.5}
                
                manager._check_bee_communication_health()
                
                # Should not log any warnings
                mock_logger.warning.assert_not_called()

    def test_check_bee_communication_health_low_usage(self, test_config, mock_logger):
        """Test communication health check - low CLI usage"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            # Mock low CLI usage rate  
            with patch.object(manager.conversation_logger, 'get_conversation_stats') as mock_stats:
                mock_stats.return_value = {"sender_cli_usage_rate": 85.0}
                
                with patch.object(manager, '_send_via_sender_cli', return_value=True) as mock_send:
                    manager._check_bee_communication_health()
                    
                    # Should log warning
                    mock_logger.warning.assert_called_with("Low sender CLI usage rate: 85.0%")
                    
                    # Should send alert to queen
                    mock_send.assert_called_once()
                    call_kwargs = mock_send.call_args[1]
                    assert call_kwargs['from_bee'] == "system"
                    assert call_kwargs['to_bee'] == "queen"
                    assert call_kwargs['message_type'] == "alert"

    def test_communication_health_error_handling(self, test_config, mock_logger):
        """Test communication health check error handling"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            # Mock stats error
            with patch.object(manager.conversation_logger, 'get_conversation_stats', 
                            side_effect=Exception("Stats error")):
                manager._check_bee_communication_health()
                
                # Should log error
                mock_logger.error.assert_called_once()
                error_msg = mock_logger.error.call_args[0][0]
                assert "Failed to check communication health" in error_msg


class TestConversationManagerSummary:
    """Test conversation summary functionality"""

    def test_get_conversation_summary_basic(self, test_config):
        """Test basic conversation summary"""
        manager = ConversationManager(test_config)
        
        mock_stats = {
            "total_messages": 100,
            "beekeeper_instructions": 20,
            "bee_conversations": 80,
            "sender_cli_usage_rate": 95.0
        }
        
        mock_conversations = [
            {"from_bee": "queen", "to_bee": "developer"},
            {"from_bee": "developer", "to_bee": "qa"},
            {"from_bee": "qa", "to_bee": "queen"}
        ]
        
        with patch.object(manager.conversation_logger, 'get_conversation_stats', return_value=mock_stats):
            with patch.object(manager.conversation_logger, 'get_conversation_history', return_value=mock_conversations):
                summary = manager.get_conversation_summary()
                
                assert summary["stats"] == mock_stats
                assert summary["recent_conversations_count"] == 3
                assert "bee_message_counts" in summary
                assert "generated_at" in summary

    def test_get_conversation_summary_message_counts(self, test_config):
        """Test conversation summary message counts"""
        manager = ConversationManager(test_config)
        
        mock_conversations = [
            {"from_bee": "queen", "to_bee": "developer"},
            {"from_bee": "developer", "to_bee": "queen"},
            {"from_bee": "queen", "to_bee": "qa"},
        ]
        
        with patch.object(manager.conversation_logger, 'get_conversation_stats', return_value={}):
            with patch.object(manager.conversation_logger, 'get_conversation_history', return_value=mock_conversations):
                summary = manager.get_conversation_summary()
                
                counts = summary["bee_message_counts"]
                
                # Queen: sent 2, received 1
                assert counts["queen"]["sent"] == 2
                assert counts["queen"]["received"] == 1
                
                # Developer: sent 1, received 1
                assert counts["developer"]["sent"] == 1
                assert counts["developer"]["received"] == 1
                
                # QA: sent 0, received 1
                assert counts["qa"]["sent"] == 0
                assert counts["qa"]["received"] == 1

    def test_get_conversation_summary_error_handling(self, test_config, mock_logger):
        """Test conversation summary error handling"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            with patch.object(manager.conversation_logger, 'get_conversation_stats', 
                            side_effect=Exception("Stats error")):
                summary = manager.get_conversation_summary()
                
                assert summary == {}
                mock_logger.error.assert_called_once()


class TestConversationManagerMonitoring:
    """Test monitoring functionality"""

    def test_log_bee_message_delegation(self, test_config):
        """Test bee message logging delegation"""
        manager = ConversationManager(test_config)
        
        with patch.object(manager.conversation_logger, 'log_bee_conversation', return_value=456) as mock_log:
            result = manager.log_bee_message(
                from_bee="queen",
                to_bee="developer",
                content="テストメッセージ",
                message_type="task_update",
                task_id="test-123",
                sender_cli_used=True
            )
            
            assert result == 456
            mock_log.assert_called_once_with(
                from_bee="queen",
                to_bee="developer",
                content="テストメッセージ",
                message_type="task_update",
                task_id="test-123",
                sender_cli_used=True
            )

    def test_monitor_bee_communications_basic(self, test_config, mock_logger):
        """Test basic communication monitoring"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            # Mock monitoring components
            with patch.object(manager.conversation_logger, 'enforce_sender_cli_usage', return_value=[]):
                with patch.object(manager, '_check_bee_communication_health'):
                    with patch('time.sleep', side_effect=KeyboardInterrupt):  # Exit after first iteration
                        manager.monitor_bee_communications(interval=0.1)
                        
                        # Should log monitoring start and stop
                        expected_calls = [
                            call("ConversationManager initialized"),
                            call("Starting bee communication monitoring (interval: 0.1s)"),
                            call("Communication monitoring stopped by user")
                        ]
                        mock_logger.info.assert_has_calls(expected_calls)

    def test_monitor_bee_communications_with_violations(self, test_config, mock_logger):
        """Test communication monitoring with violations"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            violations = [{"message_id": 123, "from_bee": "developer", "to_bee": "qa"}]
            
            with patch.object(manager.conversation_logger, 'enforce_sender_cli_usage', return_value=violations):
                with patch.object(manager, '_handle_sender_cli_violations') as mock_handle:
                    with patch.object(manager, '_check_bee_communication_health'):
                        with patch('time.sleep', side_effect=KeyboardInterrupt):
                            manager.monitor_bee_communications(interval=0.1)
                            
                            # Should handle violations
                            mock_handle.assert_called_once_with(violations)

    def test_shutdown_with_stats(self, test_config, mock_logger):
        """Test shutdown with final stats"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            final_stats = {"total_messages": 50, "sender_cli_usage_rate": 98.0}
            
            with patch.object(manager.conversation_logger, 'get_conversation_stats', return_value=final_stats):
                manager.shutdown()
                
                expected_calls = [
                    call("ConversationManager initialized"),
                    call("ConversationManager shutting down"),
                    call(f"Final conversation stats: {final_stats}")
                ]
                mock_logger.info.assert_has_calls(expected_calls)

    def test_shutdown_stats_error(self, test_config, mock_logger):
        """Test shutdown with stats error"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            with patch.object(manager.conversation_logger, 'get_conversation_stats', 
                            side_effect=Exception("Stats error")):
                manager.shutdown()
                
                mock_logger.warning.assert_called_with("Failed to get final stats: Stats error")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])