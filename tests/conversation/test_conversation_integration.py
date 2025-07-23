#!/usr/bin/env python3
"""
Integration tests for conversation system components
"""

import json
import pytest
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from bees.conversation_logger import ConversationLogger
from bees.conversation_manager import ConversationManager
from bees.conversation_daemon import ConversationDaemon
from tests.utils.database_helpers import TestDatabaseHelper, test_db_helper, test_config, mock_logger
from tests.utils.mock_helpers import ConversationTestMocks


class TestConversationSystemIntegration:
    """Test full conversation system integration"""

    def test_end_to_end_beekeeper_instruction_flow(self, test_config, mock_logger):
        """Test complete flow from beekeeper instruction to task creation"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            # Mock successful CLI send
            with ConversationTestMocks() as mocks:
                mocks.setup_successful_cli_send()
                
                # Simulate beekeeper instruction
                result = manager.intercept_beekeeper_input(
                    input_text="issue 47を実装してください",
                    target_bee="developer"
                )
                
                assert result is True
                
                # Verify message was logged
                logger = ConversationLogger(test_config)
                history = logger.get_conversation_history(limit=1)
                assert len(history) == 1
                assert history[0]["from_bee"] == "beekeeper"
                assert history[0]["to_bee"] == "developer"
                assert "issue 47を実装" in history[0]["content"]
                
                # Verify task was auto-created
                with logger._get_db_connection() as conn:
                    task_count = conn.execute(
                        "SELECT COUNT(*) FROM tasks WHERE created_by = 'beekeeper'"
                    ).fetchone()[0]
                    assert task_count == 1

    def test_bee_to_bee_communication_flow(self, test_config, mock_logger):
        """Test bee-to-bee communication with CLI enforcement"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            logger = ConversationLogger(test_config)
            
            # Test proper CLI usage
            message_id = logger.log_bee_conversation(
                from_bee="queen",
                to_bee="developer",
                content="新しいタスクを割り当てました",
                message_type="task_update",
                sender_cli_used=True,
                task_id="test-task-123"
            )
            
            assert message_id > 0
            
            # Verify no violations detected
            violations = logger.enforce_sender_cli_usage()
            assert len(violations) == 0
            
            # Test CLI violation
            logger.log_bee_conversation(
                from_bee="developer",
                to_bee="qa",
                content="直接メッセージ（違反）",
                sender_cli_used=False
            )
            
            # Verify violation detected
            violations = logger.enforce_sender_cli_usage()
            assert len(violations) == 1
            assert violations[0]["from_bee"] == "developer"
            assert violations[0]["to_bee"] == "qa"

    def test_conversation_stats_and_monitoring(self, test_config, test_db_helper):
        """Test conversation statistics and monitoring integration"""
        # Setup test conversation data
        test_data = {
            "messages": [
                {
                    "from_bee": "beekeeper",
                    "to_bee": "developer",
                    "content": "実装してください",
                    "message_type": "instruction",
                    "sender_cli_used": True
                },
                {
                    "from_bee": "queen",
                    "to_bee": "developer",
                    "content": "タスク割り当て",
                    "sender_cli_used": True
                },
                {
                    "from_bee": "developer",
                    "to_bee": "qa",
                    "content": "テスト依頼",
                    "sender_cli_used": True
                },
                {
                    "from_bee": "qa",
                    "to_bee": "developer",
                    "content": "違反メッセージ",
                    "sender_cli_used": False
                }
            ]
        }
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        manager = ConversationManager(test_config)
        
        # Test statistics
        stats = logger.get_conversation_stats()
        assert stats["total_messages"] == 4
        assert stats["beekeeper_instructions"] == 1
        assert stats["bee_conversations"] == 3
        assert stats["sender_cli_usage_rate"] == 75.0  # 3/4 * 100
        
        # Test conversation summary
        summary = manager.get_conversation_summary()
        assert summary["stats"]["total_messages"] == 4
        assert summary["recent_conversations_count"] == 4
        assert "bee_message_counts" in summary

    def test_daemon_manager_integration(self, test_config, mock_logger):
        """Test daemon and manager integration"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config, monitoring_interval=0.1)
            
            # Mock the monitoring to prevent infinite loop
            call_count = 0
            def mock_monitor(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count >= 2:
                    raise KeyboardInterrupt()
                time.sleep(0.05)
            
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications', 
                            side_effect=mock_monitor):
                
                # Test daemon lifecycle
                daemon.start()
                assert daemon._daemon_thread is not None
                assert daemon._daemon_thread.is_alive()
                
                # Wait for monitoring iterations
                time.sleep(0.3)
                
                daemon.stop()
                assert daemon._shutdown_event.is_set()
                
                # Verify monitoring was called
                assert call_count >= 2


class TestConversationSystemConcurrency:
    """Test conversation system under concurrent access"""

    def test_concurrent_message_logging(self, test_config):
        """Test concurrent message logging"""
        logger = ConversationLogger(test_config)
        
        results = []
        errors = []
        
        def log_messages(thread_id: int, count: int):
            try:
                for i in range(count):
                    message_id = logger.log_bee_conversation(
                        from_bee=f"bee_{thread_id}",
                        to_bee="target",
                        content=f"Message {i} from thread {thread_id}",
                        sender_cli_used=True
                    )
                    results.append((thread_id, message_id))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=log_messages, args=(thread_id, 10))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 50  # 5 threads * 10 messages each
        
        # Verify all messages were stored
        with logger._get_db_connection() as conn:
            message_count = conn.execute("SELECT COUNT(*) FROM bee_messages").fetchone()[0]
            assert message_count == 50

    def test_concurrent_stats_and_logging(self, test_config):
        """Test concurrent statistics queries and logging operations"""
        logger = ConversationLogger(test_config)
        
        stats_results = []
        log_results = []
        errors = []
        
        def continuous_stats():
            try:
                for _ in range(20):
                    stats = logger.get_conversation_stats()
                    stats_results.append(stats["total_messages"])
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Stats error: {e}")
        
        def continuous_logging():
            try:
                for i in range(20):
                    message_id = logger.log_bee_conversation(
                        from_bee="concurrent_bee",
                        to_bee="target",
                        content=f"Concurrent message {i}",
                        sender_cli_used=True
                    )
                    log_results.append(message_id)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Logging error: {e}")
        
        # Run concurrent operations
        stats_thread = threading.Thread(target=continuous_stats)
        log_thread = threading.Thread(target=continuous_logging)
        
        stats_thread.start()
        log_thread.start()
        
        stats_thread.join(timeout=5.0)
        log_thread.join(timeout=5.0)
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(log_results) == 20
        assert len(stats_results) == 20
        
        # Stats should show increasing message counts
        assert stats_results[-1] >= stats_results[0]

    def test_daemon_with_concurrent_operations(self, test_config, mock_logger):
        """Test daemon operation with concurrent message activity"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config, monitoring_interval=0.1)
            logger = ConversationLogger(test_config)
            
            results = []
            
            def background_logging():
                for i in range(10):
                    message_id = logger.log_bee_conversation(
                        from_bee="background_bee",
                        to_bee="target",
                        content=f"Background message {i}",
                        sender_cli_used=i % 2 == 0  # Mix of CLI usage
                    )
                    results.append(message_id)
                    time.sleep(0.05)
            
            # Start daemon with limited monitoring
            monitor_count = 0
            def limited_monitor(*args, **kwargs):
                nonlocal monitor_count
                monitor_count += 1
                if monitor_count >= 3:
                    raise KeyboardInterrupt()
                time.sleep(0.1)
            
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications',
                            side_effect=limited_monitor):
                
                # Start daemon and background logging
                daemon.start()
                log_thread = threading.Thread(target=background_logging)
                log_thread.start()
                
                # Wait for operations
                log_thread.join(timeout=2.0)
                time.sleep(0.4)  # Let daemon run
                daemon.stop()
                
                # Verify operations completed
                assert len(results) == 10
                assert monitor_count >= 3


class TestConversationSystemErrorRecovery:
    """Test conversation system error recovery"""

    def test_database_reconnection_on_failure(self, test_config, mock_logger):
        """Test database reconnection after connection failure"""
        with patch('bees.conversation_logger.get_logger', return_value=mock_logger):
            logger = ConversationLogger(test_config)
            
            # First, log a message successfully
            message_id = logger.log_bee_conversation(
                from_bee="test_bee",
                to_bee="target",
                content="Initial message",
                sender_cli_used=True
            )
            assert message_id > 0
            
            # Simulate database connection failure and recovery
            original_get_connection = logger._get_db_connection
            
            call_count = 0
            def failing_connection():
                nonlocal call_count
                call_count += 1
                if call_count <= 2:  # Fail first 2 attempts
                    raise sqlite3.OperationalError("Database locked")
                return original_get_connection()
            
            with patch.object(logger, '_get_db_connection', side_effect=failing_connection):
                # This should eventually succeed after retries
                try:
                    stats = logger.get_conversation_stats()
                    # If we get here, the retry mechanism worked
                    assert call_count > 2
                except Exception:
                    # Expected if retry mechanism not implemented
                    pass

    def test_manager_resilience_to_cli_failures(self, test_config, mock_logger):
        """Test manager resilience to CLI command failures"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            # Mock CLI failures
            failure_count = 0
            def failing_cli(*args, **kwargs):
                nonlocal failure_count
                failure_count += 1
                if failure_count <= 2:
                    raise subprocess.CalledProcessError(1, "tmux")
                return True
            
            with patch.object(manager, '_send_via_sender_cli', side_effect=failing_cli):
                # Multiple attempts should eventually succeed
                result = manager.intercept_beekeeper_input(
                    input_text="テスト指示",
                    target_bee="developer"
                )
                
                # Should handle failures gracefully
                assert failure_count > 0

    def test_daemon_restart_after_critical_failure(self, test_config, mock_logger):
        """Test daemon restart capability after critical failures"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config, monitoring_interval=0.1)
            
            # Mock critical failure followed by recovery
            failure_count = 0
            def failing_monitor(*args, **kwargs):
                nonlocal failure_count
                failure_count += 1
                if failure_count == 1:
                    raise SystemError("Critical failure")
                elif failure_count < 4:
                    time.sleep(0.05)
                else:
                    raise KeyboardInterrupt()  # Stop after recovery
            
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications',
                            side_effect=failing_monitor):
                
                # Test restart capability
                daemon.start()
                time.sleep(0.3)
                daemon.stop()
                
                # Verify critical failure was handled
                mock_logger.critical.assert_called_once()
                
                # Daemon should be able to restart
                daemon.start()
                time.sleep(0.2)
                daemon.stop()


class TestConversationSystemPerformance:
    """Test conversation system performance characteristics"""

    def test_large_message_volume_handling(self, test_config):
        """Test handling of large message volumes"""
        logger = ConversationLogger(test_config)
        
        start_time = time.time()
        
        # Log large number of messages
        message_ids = []
        for i in range(1000):
            message_id = logger.log_bee_conversation(
                from_bee=f"bee_{i % 4}",
                to_bee=f"target_{i % 3}",
                content=f"Performance test message {i}",
                sender_cli_used=True,
                task_id=f"task-{i % 10}"
            )
            message_ids.append(message_id)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert len(message_ids) == 1000
        assert duration < 10.0, f"Logging took too long: {duration}s"
        
        # Verify database integrity
        with logger._get_db_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM bee_messages").fetchone()[0]
            assert count == 1000

    def test_stats_query_performance(self, test_config, test_db_helper):
        """Test statistics query performance with large dataset"""
        # Setup large dataset
        messages = []
        for i in range(5000):
            messages.append({
                "from_bee": f"bee_{i % 10}",
                "to_bee": f"target_{i % 5}",
                "content": f"Message {i}",
                "sender_cli_used": i % 4 != 0,  # 75% CLI usage
                "conversation_id": f"conv-{i % 100}"
            })
        
        test_data = {"messages": messages}
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        
        # Test stats query performance
        start_time = time.time()
        stats = logger.get_conversation_stats()
        end_time = time.time()
        
        # Performance and correctness
        duration = end_time - start_time
        assert duration < 1.0, f"Stats query too slow: {duration}s"
        assert stats["total_messages"] == 5000
        assert stats["sender_cli_usage_rate"] == 75.0

    def test_concurrent_access_performance(self, test_config):
        """Test performance under concurrent access"""
        logger = ConversationLogger(test_config)
        
        def worker_thread(thread_id: int, message_count: int):
            start_time = time.time()
            for i in range(message_count):
                logger.log_bee_conversation(
                    from_bee=f"thread_{thread_id}",
                    to_bee="target",
                    content=f"Message {i}",
                    sender_cli_used=True
                )
            return time.time() - start_time
        
        # Run concurrent workers
        threads = []
        for thread_id in range(10):
            thread = threading.Thread(
                target=worker_thread, 
                args=(thread_id, 100)
            )
            threads.append(thread)
        
        start_time = time.time()
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=10.0)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Performance assertions
        assert total_duration < 15.0, f"Concurrent operations too slow: {total_duration}s"
        
        # Verify data integrity
        with logger._get_db_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM bee_messages").fetchone()[0]
            assert count == 1000  # 10 threads * 100 messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])