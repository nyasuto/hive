#!/usr/bin/env python3
"""
Comprehensive unit tests for ConversationDaemon
"""

import pytest
import subprocess
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from bees.conversation_daemon import ConversationDaemon
from bees.conversation_manager import ConversationManager
from tests.utils.database_helpers import TestDatabaseHelper, test_db_helper, test_config, mock_logger
from tests.utils.mock_helpers import ConversationTestMocks


class TestConversationDaemonInit:
    """Test ConversationDaemon initialization"""

    def test_init_with_config(self, test_config, mock_logger):
        """Test initialization with provided config"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            assert daemon.config == test_config
            assert isinstance(daemon.conversation_manager, ConversationManager)
            assert daemon.monitoring_interval == 5.0  # default
            assert daemon._shutdown_event is not None
            assert daemon._daemon_thread is None
            
            # Verify initialization log
            mock_logger.info.assert_called_with("ConversationDaemon initialized")

    def test_init_with_custom_interval(self, test_config, mock_logger):
        """Test initialization with custom monitoring interval"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(
                config=test_config,
                monitoring_interval=10.0
            )
            
            assert daemon.monitoring_interval == 10.0

    def test_init_with_default_config(self, test_db_helper, mock_logger):
        """Test initialization with default config"""
        with patch('bees.conversation_daemon.get_config') as mock_get_config:
            mock_get_config.return_value = test_db_helper.get_test_config()
            
            with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
                daemon = ConversationDaemon()
                
                assert daemon.config is not None
                mock_get_config.assert_called_once()


class TestConversationDaemonLifecycle:
    """Test daemon lifecycle management"""

    def test_start_daemon_basic(self, test_config, mock_logger):
        """Test basic daemon startup"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock the monitoring loop to prevent actual execution
            with patch.object(daemon, '_monitoring_loop') as mock_loop:
                daemon.start()
                
                assert daemon._daemon_thread is not None
                assert daemon._daemon_thread.is_alive()
                mock_logger.info.assert_any_call("ConversationDaemon started")
                
                # Cleanup
                daemon.stop()

    def test_start_daemon_already_running(self, test_config, mock_logger):
        """Test starting daemon when already running"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            with patch.object(daemon, '_monitoring_loop'):
                daemon.start()
                
                # Try to start again - should be no-op
                daemon.start()
                
                mock_logger.warning.assert_called_with("ConversationDaemon is already running")
                
                daemon.stop()

    def test_stop_daemon_basic(self, test_config, mock_logger):
        """Test basic daemon shutdown"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            with patch.object(daemon, '_monitoring_loop'):
                daemon.start()
                daemon.stop()
                
                assert daemon._shutdown_event.is_set()
                mock_logger.info.assert_any_call("ConversationDaemon stopped")

    def test_stop_daemon_not_running(self, test_config, mock_logger):
        """Test stopping daemon when not running"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            daemon.stop()
            
            mock_logger.warning.assert_called_with("ConversationDaemon is not running")

    def test_daemon_thread_cleanup(self, test_config, mock_logger):
        """Test proper thread cleanup on shutdown"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock short monitoring loop
            def short_loop():
                time.sleep(0.1)
                
            with patch.object(daemon, '_monitoring_loop', side_effect=short_loop):
                daemon.start()
                thread = daemon._daemon_thread
                
                daemon.stop()
                
                # Thread should finish and cleanup
                if thread:
                    thread.join(timeout=1.0)
                    assert not thread.is_alive()

    def test_context_manager(self, test_config, mock_logger):
        """Test daemon as context manager"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            with patch.object(ConversationDaemon, '_monitoring_loop'):
                with ConversationDaemon(config=test_config) as daemon:
                    assert daemon._daemon_thread is not None
                    assert daemon._daemon_thread.is_alive()
                
                # Should be stopped after context exit
                assert daemon._shutdown_event.is_set()


class TestConversationDaemonMonitoring:
    """Test daemon monitoring functionality"""

    def test_monitoring_loop_basic(self, test_config, mock_logger):
        """Test basic monitoring loop"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config, monitoring_interval=0.1)
            
            # Mock the manager monitoring method
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications') as mock_monitor:
                mock_monitor.side_effect = KeyboardInterrupt  # Exit after first iteration
                
                daemon._monitoring_loop()
                
                mock_monitor.assert_called_once_with(interval=0.1)

    def test_monitoring_loop_exception_handling(self, test_config, mock_logger):
        """Test monitoring loop exception handling"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock monitoring to raise exception first, then KeyboardInterrupt
            side_effects = [Exception("Test error"), KeyboardInterrupt()]
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications', 
                            side_effect=side_effects) as mock_monitor:
                
                daemon._monitoring_loop()
                
                # Should handle exception and continue
                assert mock_monitor.call_count == 2
                mock_logger.error.assert_called_once()
                error_msg = mock_logger.error.call_args[0][0]
                assert "Error in monitoring loop" in error_msg

    def test_monitoring_loop_shutdown_signal(self, test_config, mock_logger):
        """Test monitoring loop responds to shutdown signal"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Set shutdown event before starting loop
            daemon._shutdown_event.set()
            
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications') as mock_monitor:
                daemon._monitoring_loop()
                
                # Should not call monitoring if shutdown is set
                mock_monitor.assert_not_called()

    def test_monitoring_restart_on_failure(self, test_config, mock_logger):
        """Test monitoring restart after failures"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            call_count = 0
            def mock_monitor(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception(f"Failure {call_count}")
                else:
                    raise KeyboardInterrupt()  # Exit after 3 attempts
            
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications', 
                            side_effect=mock_monitor):
                
                daemon._monitoring_loop()
                
                # Should have attempted 3 times
                assert call_count == 3
                assert mock_logger.error.call_count == 2  # Two failures logged

    def test_daemon_status_reporting(self, test_config, mock_logger):
        """Test daemon status reporting"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Test status when not running
            status = daemon.get_status()
            assert status["is_running"] is False
            assert status["uptime"] is None
            
            with patch.object(daemon, '_monitoring_loop'):
                daemon.start()
                
                # Test status when running
                status = daemon.get_status()
                assert status["is_running"] is True
                assert status["uptime"] is not None
                assert "start_time" in status
                
                daemon.stop()


class TestConversationDaemonIntegration:
    """Test daemon integration with conversation system"""

    def test_daemon_integration_with_manager(self, test_config, mock_logger):
        """Test daemon integration with conversation manager"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Verify manager is properly initialized
            assert daemon.conversation_manager is not None
            assert daemon.conversation_manager.config == test_config

    def test_daemon_health_check(self, test_config, mock_logger):
        """Test daemon health check functionality"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock successful health check
            with patch.object(daemon.conversation_manager, 'get_conversation_summary') as mock_summary:
                mock_summary.return_value = {
                    "stats": {"total_messages": 100},
                    "recent_conversations_count": 5
                }
                
                health = daemon.check_health()
                
                assert health["daemon_running"] is False  # Not started yet
                assert health["manager_responsive"] is True
                assert health["conversation_stats"] is not None

    def test_daemon_health_check_failure(self, test_config, mock_logger):
        """Test daemon health check with manager failure"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock manager failure
            with patch.object(daemon.conversation_manager, 'get_conversation_summary', 
                            side_effect=Exception("Manager error")):
                
                health = daemon.check_health()
                
                assert health["manager_responsive"] is False
                assert health["error"] is not None

    def test_daemon_graceful_shutdown_with_manager(self, test_config, mock_logger):
        """Test daemon graceful shutdown including manager"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            with patch.object(daemon, '_monitoring_loop'):
                daemon.start()
                
                # Mock manager shutdown
                with patch.object(daemon.conversation_manager, 'shutdown') as mock_shutdown:
                    daemon.stop()
                    
                    mock_shutdown.assert_called_once()


class TestConversationDaemonConfiguration:
    """Test daemon configuration handling"""

    def test_daemon_config_validation(self, test_config, mock_logger):
        """Test daemon configuration validation"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            # Test with valid config
            daemon = ConversationDaemon(config=test_config)
            assert daemon.config.hive_db_path is not None
            
            # Test with invalid monitoring interval
            with pytest.raises(ValueError):
                ConversationDaemon(config=test_config, monitoring_interval=0)
            
            with pytest.raises(ValueError):
                ConversationDaemon(config=test_config, monitoring_interval=-5)

    def test_daemon_config_defaults(self, test_config, mock_logger):
        """Test daemon configuration defaults"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            assert daemon.monitoring_interval == 5.0
            assert daemon.config.session_name == "test_beehive"

    def test_daemon_runtime_config_changes(self, test_config, mock_logger):
        """Test runtime configuration changes"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Test interval change
            daemon.set_monitoring_interval(10.0)
            assert daemon.monitoring_interval == 10.0
            
            # Test invalid interval change
            with pytest.raises(ValueError):
                daemon.set_monitoring_interval(-1.0)


class TestConversationDaemonErrorHandling:
    """Test daemon error handling scenarios"""

    def test_daemon_manager_initialization_failure(self, test_config, mock_logger):
        """Test daemon handling of manager initialization failure"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            with patch('bees.conversation_daemon.ConversationManager', 
                      side_effect=Exception("Manager init failed")):
                
                with pytest.raises(Exception):
                    ConversationDaemon(config=test_config)

    def test_daemon_thread_creation_failure(self, test_config, mock_logger):
        """Test daemon handling of thread creation failure"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            with patch('threading.Thread', side_effect=RuntimeError("Thread creation failed")):
                daemon.start()
                
                mock_logger.error.assert_called_once()
                error_msg = mock_logger.error.call_args[0][0]
                assert "Failed to start daemon thread" in error_msg

    def test_daemon_monitoring_critical_failure(self, test_config, mock_logger):
        """Test daemon handling of critical monitoring failures"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock critical failure that should stop daemon
            def critical_failure(*args, **kwargs):
                raise SystemError("Critical system failure")
            
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications', 
                            side_effect=critical_failure):
                
                daemon._monitoring_loop()
                
                mock_logger.critical.assert_called_once()
                critical_msg = mock_logger.critical.call_args[0][0]
                assert "Critical error in monitoring loop" in critical_msg

    def test_daemon_shutdown_timeout_handling(self, test_config, mock_logger):
        """Test daemon shutdown timeout handling"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock a thread that takes too long to stop
            def long_running_loop():
                time.sleep(10)  # Simulate long-running operation
            
            with patch.object(daemon, '_monitoring_loop', side_effect=long_running_loop):
                daemon.start()
                
                # Mock thread join with timeout
                with patch.object(daemon._daemon_thread, 'join') as mock_join:
                    mock_join.return_value = None  # Simulate timeout
                    
                    daemon.stop(timeout=0.1)
                    
                    mock_logger.warning.assert_called_once()
                    warning_msg = mock_logger.warning.call_args[0][0]
                    assert "Daemon thread did not stop gracefully" in warning_msg


class TestConversationDaemonMetrics:
    """Test daemon metrics and monitoring features"""

    def test_daemon_metrics_collection(self, test_config, mock_logger):
        """Test daemon metrics collection"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            with patch.object(daemon, '_monitoring_loop'):
                daemon.start()
                
                metrics = daemon.get_metrics()
                
                assert "uptime" in metrics
                assert "monitoring_interval" in metrics
                assert "thread_active" in metrics
                assert "restart_count" in metrics
                
                daemon.stop()

    def test_daemon_restart_counting(self, test_config, mock_logger):
        """Test daemon restart counting"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock multiple start/stop cycles
            with patch.object(daemon, '_monitoring_loop'):
                for i in range(3):
                    daemon.start()
                    daemon.stop()
                
                metrics = daemon.get_metrics()
                assert metrics["restart_count"] == 3

    def test_daemon_performance_tracking(self, test_config, mock_logger):
        """Test daemon performance tracking"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock performance data
            with patch.object(daemon.conversation_manager, 'get_conversation_summary') as mock_summary:
                mock_summary.return_value = {
                    "stats": {
                        "total_messages": 1000,
                        "sender_cli_usage_rate": 95.5
                    }
                }
                
                performance = daemon.get_performance_stats()
                
                assert "message_throughput" in performance
                assert "cli_compliance_rate" in performance
                assert performance["cli_compliance_rate"] == 95.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])