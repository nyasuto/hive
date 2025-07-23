#!/usr/bin/env python3
"""
Performance tests for conversation system components
"""

import json
import pytest
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from bees.conversation_logger import ConversationLogger
from bees.conversation_manager import ConversationManager
from bees.conversation_daemon import ConversationDaemon
from tests.utils.database_helpers import TestDatabaseHelper, test_db_helper, test_config
from tests.utils.mock_helpers import ConversationTestMocks


class TestConversationLoggerPerformance:
    """Performance tests for ConversationLogger"""

    def test_single_message_logging_performance(self, test_config):
        """Test single message logging performance"""
        logger = ConversationLogger(test_config)
        
        # Warm up
        logger.log_bee_conversation(
            from_bee="warmup",
            to_bee="target",
            content="Warmup message",
            sender_cli_used=True
        )
        
        # Performance test
        start_time = time.time()
        
        message_id = logger.log_bee_conversation(
            from_bee="performance_bee",
            to_bee="target",
            content="Performance test message",
            sender_cli_used=True,
            task_id="perf-task-1"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert message_id > 0
        assert duration < 0.1, f"Single message logging too slow: {duration}s"

    def test_bulk_message_logging_performance(self, test_config):
        """Test bulk message logging performance"""
        logger = ConversationLogger(test_config)
        
        message_count = 1000
        start_time = time.time()
        
        message_ids = []
        for i in range(message_count):
            message_id = logger.log_bee_conversation(
                from_bee=f"bee_{i % 10}",
                to_bee=f"target_{i % 5}",
                content=f"Bulk message {i}",
                sender_cli_used=True,
                task_id=f"task-{i % 20}"
            )
            message_ids.append(message_id)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert len(message_ids) == message_count
        assert duration < 5.0, f"Bulk logging too slow: {duration}s"
        
        # Throughput should be reasonable
        throughput = message_count / duration
        assert throughput > 200, f"Throughput too low: {throughput} msg/s"

    def test_concurrent_logging_performance(self, test_config):
        """Test concurrent message logging performance"""
        logger = ConversationLogger(test_config)
        
        def worker_task(worker_id: int, message_count: int):
            start_time = time.time()
            message_ids = []
            
            for i in range(message_count):
                message_id = logger.log_bee_conversation(
                    from_bee=f"worker_{worker_id}",
                    to_bee=f"target_{i % 3}",
                    content=f"Concurrent message {i} from worker {worker_id}",
                    sender_cli_used=True
                )
                message_ids.append(message_id)
            
            end_time = time.time()
            return {
                'worker_id': worker_id,
                'duration': end_time - start_time,
                'message_count': len(message_ids),
                'message_ids': message_ids
            }
        
        # Run concurrent workers
        num_workers = 10
        messages_per_worker = 100
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker_task, worker_id, messages_per_worker)
                for worker_id in range(num_workers)
            ]
            
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Verify results
        total_messages = sum(result['message_count'] for result in results)
        assert total_messages == num_workers * messages_per_worker
        
        # Performance assertions
        assert total_duration < 10.0, f"Concurrent logging too slow: {total_duration}s"
        
        # Check individual worker performance
        max_worker_duration = max(result['duration'] for result in results)
        assert max_worker_duration < 8.0, f"Slowest worker too slow: {max_worker_duration}s"
        
        # Verify database integrity
        with logger._get_db_connection() as conn:
            db_count = conn.execute("SELECT COUNT(*) FROM bee_messages").fetchone()[0]
            assert db_count == total_messages

    def test_stats_query_performance(self, test_config, test_db_helper):
        """Test conversation statistics query performance"""
        # Setup large dataset
        messages = []
        for i in range(10000):
            messages.append({
                "from_bee": f"bee_{i % 20}",
                "to_bee": f"target_{i % 10}",
                "content": f"Stats test message {i}",
                "sender_cli_used": i % 3 != 0,  # ~67% CLI usage
                "conversation_id": f"conv-{i % 500}",
                "task_id": f"task-{i % 100}" if i % 5 == 0 else None
            })
        
        test_data = {"messages": messages}
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        
        # Warm up query
        logger.get_conversation_stats()
        
        # Performance test
        start_time = time.time()
        stats = logger.get_conversation_stats()
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verify correctness
        assert stats["total_messages"] == 10000
        assert abs(stats["sender_cli_usage_rate"] - 66.67) < 1.0
        
        # Performance assertion
        assert duration < 0.5, f"Stats query too slow: {duration}s"

    def test_history_query_performance(self, test_config, test_db_helper):
        """Test conversation history query performance"""
        # Setup large dataset with specific conversation
        target_conv_id = "performance-test-conv"
        messages = []
        
        # Add messages for target conversation
        for i in range(1000):
            messages.append({
                "from_bee": f"bee_{i % 5}",
                "to_bee": f"target_{i % 3}",
                "content": f"Target conversation message {i}",
                "conversation_id": target_conv_id,
                "sender_cli_used": True
            })
        
        # Add noise messages
        for i in range(5000):
            messages.append({
                "from_bee": f"noise_bee_{i % 10}",
                "to_bee": f"noise_target_{i % 5}",
                "content": f"Noise message {i}",
                "conversation_id": f"noise-conv-{i % 100}",
                "sender_cli_used": True
            })
        
        test_data = {"messages": messages}
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        
        # Performance test - filtered query
        start_time = time.time()
        history = logger.get_conversation_history(
            conversation_id=target_conv_id,
            limit=500
        )
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verify correctness
        assert len(history) == 500  # Limited by limit parameter
        for msg in history:
            assert msg["conversation_id"] == target_conv_id
        
        # Performance assertion
        assert duration < 0.2, f"History query too slow: {duration}s"

    def test_violation_detection_performance(self, test_config, test_db_helper):
        """Test CLI violation detection performance"""
        # Setup dataset with mix of violations and compliance
        messages = []
        for i in range(5000):
            messages.append({
                "from_bee": f"bee_{i % 15}",
                "to_bee": f"target_{i % 8}",
                "content": f"Message {i}",
                "sender_cli_used": i % 10 != 0,  # 10% violations
                "message_type": "conversation"
            })
        
        test_data = {"messages": messages}
        test_db_helper.insert_test_data(test_data)
        
        logger = ConversationLogger(test_config)
        
        # Performance test
        start_time = time.time()
        violations = logger.enforce_sender_cli_usage()
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verify correctness
        expected_violations = 5000 * 0.1  # 10% violation rate
        assert abs(len(violations) - expected_violations) < 50  # Allow some variance
        
        for violation in violations:
            assert violation["sender_cli_used"] == 0  # False
        
        # Performance assertion
        assert duration < 0.3, f"Violation detection too slow: {duration}s"


class TestConversationManagerPerformance:
    """Performance tests for ConversationManager"""

    def test_beekeeper_input_processing_performance(self, test_config, mock_logger):
        """Test beekeeper input processing performance"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            with ConversationTestMocks() as mocks:
                mocks.setup_successful_cli_send()
                
                # Warm up
                manager.intercept_beekeeper_input(
                    input_text="ウォームアップ指示",
                    target_bee="developer"
                )
                
                # Performance test
                start_time = time.time()
                
                result = manager.intercept_beekeeper_input(
                    input_text="パフォーマンステスト: issue 123を実装してください",
                    target_bee="developer"
                )
                
                end_time = time.time()
                duration = end_time - start_time
                
                assert result is True
                assert duration < 0.2, f"Input processing too slow: {duration}s"

    def test_bulk_input_processing_performance(self, test_config, mock_logger):
        """Test bulk beekeeper input processing"""
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
            
            with ConversationTestMocks() as mocks:
                mocks.setup_successful_cli_send()
                
                instructions = [
                    f"タスク{i}: feature_{i}を実装してください"
                    for i in range(100)
                ]
                
                start_time = time.time()
                
                results = []
                for instruction in instructions:
                    result = manager.intercept_beekeeper_input(
                        input_text=instruction,
                        target_bee="developer"
                    )
                    results.append(result)
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Verify all succeeded
                assert all(results)
                
                # Performance assertion
                assert duration < 5.0, f"Bulk processing too slow: {duration}s"
                
                # Throughput check
                throughput = len(instructions) / duration
                assert throughput > 20, f"Throughput too low: {throughput} instructions/s"

    def test_conversation_summary_performance(self, test_config, test_db_helper):
        """Test conversation summary generation performance"""
        # Setup large conversation dataset
        messages = []
        for i in range(5000):
            messages.append({
                "from_bee": f"bee_{i % 12}",
                "to_bee": f"target_{i % 8}",
                "content": f"Summary test message {i}",
                "sender_cli_used": True,
                "conversation_id": f"conv-{i % 200}"
            })
        
        test_data = {"messages": messages}
        test_db_helper.insert_test_data(test_data)
        
        manager = ConversationManager(test_config)
        
        # Performance test
        start_time = time.time()
        summary = manager.get_conversation_summary()
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verify summary content
        assert summary["stats"]["total_messages"] == 5000
        assert "bee_message_counts" in summary
        assert "generated_at" in summary
        
        # Performance assertion
        assert duration < 1.0, f"Summary generation too slow: {duration}s"


class TestConversationDaemonPerformance:
    """Performance tests for ConversationDaemon"""

    def test_daemon_startup_performance(self, test_config, mock_logger):
        """Test daemon startup performance"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Mock monitoring to prevent actual execution
            with patch.object(daemon, '_monitoring_loop'):
                start_time = time.time()
                daemon.start()
                end_time = time.time()
                
                startup_duration = end_time - start_time
                
                assert daemon._daemon_thread is not None
                assert daemon._daemon_thread.is_alive()
                assert startup_duration < 0.5, f"Daemon startup too slow: {startup_duration}s"
                
                daemon.stop()

    def test_daemon_shutdown_performance(self, test_config, mock_logger):
        """Test daemon shutdown performance"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config)
            
            # Start daemon with quick monitoring loop
            def quick_loop():
                while not daemon._shutdown_event.is_set():
                    time.sleep(0.01)
            
            with patch.object(daemon, '_monitoring_loop', side_effect=quick_loop):
                daemon.start()
                time.sleep(0.1)  # Let it run briefly
                
                start_time = time.time()
                daemon.stop()
                end_time = time.time()
                
                shutdown_duration = end_time - start_time
                
                assert daemon._shutdown_event.is_set()
                assert shutdown_duration < 1.0, f"Daemon shutdown too slow: {shutdown_duration}s"

    def test_daemon_monitoring_overhead(self, test_config, mock_logger):
        """Test daemon monitoring overhead"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config, monitoring_interval=0.1)
            
            monitor_call_times = []
            
            def timed_monitor(*args, **kwargs):
                start = time.time()
                time.sleep(0.05)  # Simulate monitoring work
                end = time.time()
                monitor_call_times.append(end - start)
                
                if len(monitor_call_times) >= 10:
                    raise KeyboardInterrupt()
            
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications',
                            side_effect=timed_monitor):
                
                daemon.start()
                time.sleep(2.0)  # Let it run for measurements
                daemon.stop()
                
                # Verify monitoring was called
                assert len(monitor_call_times) >= 5
                
                # Check overhead is reasonable
                avg_monitor_time = sum(monitor_call_times) / len(monitor_call_times)
                assert avg_monitor_time < 0.1, f"Monitor overhead too high: {avg_monitor_time}s"

    def test_daemon_memory_usage_stability(self, test_config, mock_logger):
        """Test daemon memory usage stability over time"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config, monitoring_interval=0.05)
            
            import psutil
            process = psutil.Process()
            
            initial_memory = process.memory_info().rss
            memory_samples = []
            
            def monitoring_with_memory_tracking(*args, **kwargs):
                current_memory = process.memory_info().rss
                memory_samples.append(current_memory)
                
                time.sleep(0.02)
                
                if len(memory_samples) >= 50:
                    raise KeyboardInterrupt()
            
            with patch.object(daemon.conversation_manager, 'monitor_bee_communications',
                            side_effect=monitoring_with_memory_tracking):
                
                daemon.start()
                time.sleep(3.0)
                daemon.stop()
                
                # Analyze memory usage
                if memory_samples:
                    final_memory = memory_samples[-1]
                    memory_growth = final_memory - initial_memory
                    
                    # Memory growth should be minimal (less than 10MB)
                    assert memory_growth < 10 * 1024 * 1024, f"Memory leak detected: {memory_growth} bytes"


class TestConversationSystemScalability:
    """Scalability tests for the entire conversation system"""

    def test_system_scalability_with_load(self, test_config, mock_logger):
        """Test system behavior under high load"""
        logger = ConversationLogger(test_config)
        
        with patch('bees.conversation_manager.get_logger', return_value=mock_logger):
            manager = ConversationManager(test_config)
        
        # Simulate high load scenario
        def high_load_worker(worker_id: int):
            results = []
            
            # Each worker simulates mixed workload
            for i in range(50):
                # Log messages
                message_id = logger.log_bee_conversation(
                    from_bee=f"load_bee_{worker_id}",
                    to_bee=f"target_{i % 3}",
                    content=f"Load test message {i}",
                    sender_cli_used=True
                )
                results.append(('log', message_id))
                
                # Query stats occasionally
                if i % 10 == 0:
                    stats = logger.get_conversation_stats()
                    results.append(('stats', stats['total_messages']))
                
                # Brief pause to simulate realistic timing
                time.sleep(0.001)
            
            return results
        
        # Run high load test
        num_workers = 20
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(high_load_worker, worker_id)
                for worker_id in range(num_workers)
            ]
            
            all_results = []
            for future in as_completed(futures):
                worker_results = future.result()
                all_results.extend(worker_results)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Verify system handled the load
        log_results = [r for r in all_results if r[0] == 'log']
        stats_results = [r for r in all_results if r[0] == 'stats']
        
        expected_logs = num_workers * 50
        assert len(log_results) == expected_logs
        assert len(stats_results) == num_workers * 5  # Every 10th operation
        
        # Performance assertion
        assert total_duration < 30.0, f"High load test too slow: {total_duration}s"
        
        # Verify database consistency
        with logger._get_db_connection() as conn:
            final_count = conn.execute("SELECT COUNT(*) FROM bee_messages").fetchone()[0]
            assert final_count == expected_logs

    def test_long_running_system_stability(self, test_config, mock_logger):
        """Test system stability over extended operation"""
        with patch('bees.conversation_daemon.get_logger', return_value=mock_logger):
            daemon = ConversationDaemon(config=test_config, monitoring_interval=0.1)
        
        logger = ConversationLogger(test_config)
        
        # Track system metrics over time
        metrics = {
            'messages_logged': 0,
            'stats_queries': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        def background_activity():
            """Simulate ongoing system activity"""
            while metrics['start_time'] + 5.0 > time.time():  # Run for 5 seconds
                try:
                    # Log a message
                    logger.log_bee_conversation(
                        from_bee="stability_bee",
                        to_bee="target",
                        content=f"Stability test message {metrics['messages_logged']}",
                        sender_cli_used=True
                    )
                    metrics['messages_logged'] += 1
                    
                    # Query stats occasionally
                    if metrics['messages_logged'] % 10 == 0:
                        logger.get_conversation_stats()
                        metrics['stats_queries'] += 1
                    
                    time.sleep(0.05)
                    
                except Exception:
                    metrics['errors'] += 1
        
        # Mock daemon monitoring
        def stability_monitor(*args, **kwargs):
            time.sleep(0.08)
            if time.time() - metrics['start_time'] >= 5.0:
                raise KeyboardInterrupt()
        
        with patch.object(daemon.conversation_manager, 'monitor_bee_communications',
                          side_effect=stability_monitor):
            
            # Start daemon and background activity
            daemon.start()
            activity_thread = threading.Thread(target=background_activity)
            activity_thread.start()
            
            # Let system run
            time.sleep(6.0)
            
            # Stop gracefully
            activity_thread.join(timeout=1.0)
            daemon.stop()
        
        # Verify stability
        assert metrics['errors'] == 0, f"System errors detected: {metrics['errors']}"
        assert metrics['messages_logged'] > 50, "Insufficient activity for stability test"
        assert metrics['stats_queries'] > 5, "Insufficient stats queries for stability test"


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Comprehensive performance benchmarks"""

    def test_message_logging_benchmark(self, test_config):
        """Benchmark message logging performance"""
        logger = ConversationLogger(test_config)
        
        test_sizes = [100, 500, 1000, 2000]
        results = {}
        
        for size in test_sizes:
            start_time = time.time()
            
            for i in range(size):
                logger.log_bee_conversation(
                    from_bee=f"bench_bee_{i % 10}",
                    to_bee=f"target_{i % 5}",
                    content=f"Benchmark message {i}",
                    sender_cli_used=True
                )
            
            end_time = time.time()
            duration = end_time - start_time
            throughput = size / duration
            
            results[size] = {
                'duration': duration,
                'throughput': throughput
            }
            
            # Clear for next test
            with logger._get_db_connection() as conn:
                conn.execute("DELETE FROM bee_messages")
                conn.commit()
        
        # Verify performance scales reasonably
        for size, result in results.items():
            min_throughput = 100  # messages per second
            assert result['throughput'] > min_throughput, \
                f"Size {size}: throughput {result['throughput']:.1f} < {min_throughput}"
            
            print(f"Size {size}: {result['duration']:.3f}s, {result['throughput']:.1f} msg/s")

    def test_concurrent_access_benchmark(self, test_config):
        """Benchmark concurrent access performance"""
        logger = ConversationLogger(test_config)
        
        thread_counts = [1, 2, 5, 10]
        messages_per_thread = 200
        results = {}
        
        for num_threads in thread_counts:
            def worker():
                for i in range(messages_per_thread):
                    logger.log_bee_conversation(
                        from_bee=f"thread_bee",
                        to_bee="target",
                        content=f"Concurrent message {i}",
                        sender_cli_used=True
                    )
            
            start_time = time.time()
            
            threads = []
            for _ in range(num_threads):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            end_time = time.time()
            duration = end_time - start_time
            total_messages = num_threads * messages_per_thread
            throughput = total_messages / duration
            
            results[num_threads] = {
                'duration': duration,
                'throughput': throughput,
                'total_messages': total_messages
            }
            
            # Clear for next test
            with logger._get_db_connection() as conn:
                conn.execute("DELETE FROM bee_messages")
                conn.commit()
        
        # Print benchmark results
        for threads, result in results.items():
            print(f"Threads {threads}: {result['duration']:.3f}s, "
                  f"{result['throughput']:.1f} msg/s, "
                  f"{result['total_messages']} total")
        
        # Verify reasonable performance scaling
        single_thread_throughput = results[1]['throughput']
        multi_thread_throughput = results[max(thread_counts)]['throughput']
        
        # Multi-threading should provide some benefit
        scaling_factor = multi_thread_throughput / single_thread_throughput
        assert scaling_factor > 1.5, f"Poor scaling factor: {scaling_factor:.2f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])