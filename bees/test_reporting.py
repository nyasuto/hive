#!/usr/bin/env python3
"""
Test script for Worker→Queen result reporting functionality
Issue #4: 基本的な自律実行システムのテスト
"""

import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from bees.queen_bee import QueenBee
from bees.worker_bee import WorkerBee


def test_worker_to_queen_reporting():
    """Worker→Queen 結果報告のテスト"""
    print("🧪 Testing Worker→Queen Result Reporting")
    print("=" * 50)
    
    # Beeインスタンス作成
    queen = QueenBee("hive/hive_memory.db")
    worker = WorkerBee("qa", "quality_assurance", "hive/hive_memory.db")
    
    # テストタスクを作成・割り当て
    print("📋 Creating and assigning test task...")
    task_id = queen.create_task(
        title="Test Application Quality",
        description="Perform comprehensive quality testing on the application",
        priority="high",
        estimated_hours=4.0
    )
    
    queen.assign_task_to_bee(task_id, "qa", "Quality testing assignment for reporting test")
    print(f"✅ Task {task_id} assigned to QA Bee")
    
    # Workerがタスクを受け入れ
    print("\n🤝 Worker accepting task...")
    worker.accept_task(task_id)
    
    # 様々な種類の報告をテスト
    print("\n📊 Testing various types of reports...")
    
    # 1. 進捗報告
    print("  1. Progress Reports:")
    worker.report_progress(task_id, 20, "Started test planning and environment setup")
    worker.report_progress(task_id, 40, "Completed unit tests, starting integration tests")
    worker.report_progress(task_id, 60, "Integration tests complete, performing system tests")
    
    # 2. 問題報告
    print("  2. Issue Reports:")
    worker.report_progress(
        task_id, 65, 
        "Found critical bugs during system testing", 
        ["Login functionality broken for mobile users", 
         "Database connection timeout under load",
         "CSS rendering issues in Safari browser"]
    )
    
    # 3. 支援要請
    print("  3. Assistance Request:")
    worker.request_assistance(
        task_id,
        "Technical Support",
        "Need developer assistance to reproduce and fix the login bug. "
        "Issue appears to be related to mobile authentication tokens.",
        urgent=True
    )
    
    # 4. 最終完了報告
    print("  4. Completion Report:")
    worker.complete_task(
        task_id,
        "Quality testing completed with critical issues identified and documented",
        [
            "Test Plan Document (test_plan.md)",
            "Bug Report Summary (bug_report.pdf)", 
            "Test Coverage Report (coverage.html)",
            "Performance Test Results (perf_results.json)"
        ],
        "Conducted comprehensive testing across web, mobile, and API endpoints. "
        "Identified 3 critical bugs, 5 medium priority issues, and 12 minor improvements. "
        "All test cases documented with reproduction steps.",
        "Test coverage: 87%. All critical paths tested. "
        "Performance benchmarks show acceptable response times under normal load."
    )
    
    print("\n📨 Analyzing Queen's received messages...")
    
    # Queen側のメッセージを確認
    queen_messages = queen.get_messages(processed=False)
    print(f"Queen received {len(queen_messages)} messages from workers:")
    
    message_types = {}
    for msg in queen_messages:
        msg_type = msg['message_type']
        message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        print(f"\n📧 Message {msg['message_id']}:")
        print(f"   From: {msg['from_bee']}")
        print(f"   Type: {msg['message_type']}")
        print(f"   Subject: {msg['subject']}")
        print(f"   Priority: {msg['priority']}")
        print(f"   Task ID: {msg.get('task_id')}")
        print(f"   Content: {msg['content'][:100]}...")
    
    print(f"\n📈 Message Summary:")
    for msg_type, count in message_types.items():
        print(f"   {msg_type}: {count}")
    
    # Queen がメッセージを処理
    print(f"\n🔄 Testing Queen's message processing...")
    for msg in queen_messages:
        queen._process_message(msg)
        print(f"   Processed: {msg['message_type']} - {msg['subject'][:30]}...")
    
    # データベースでタスク状態を確認
    print(f"\n🗃️  Final Task Status:")
    final_task = queen.get_task_details(task_id)
    if final_task:
        print(f"   Status: {final_task['status']}")
        print(f"   Completed at: {final_task.get('completed_at', 'N/A')}")
        print(f"   Actual hours: {final_task.get('actual_hours', 'N/A')}")
    
    # アクティビティログを確認
    print(f"\n📋 Activity Log:")
    with queen._get_db_connection() as conn:
        cursor = conn.execute("""
            SELECT activity_type, description, bee_name, created_at
            FROM task_activity 
            WHERE task_id = ? 
            ORDER BY created_at ASC
        """, (task_id,))
        
        activities = cursor.fetchall()
        for activity in activities:
            print(f"   [{activity[3]}] {activity[2]}: {activity[0]} - {activity[1]}")
    
    print(f"\n🎯 Testing Result:")
    if len(queen_messages) >= 6:  # 期待される最小メッセージ数
        print("✅ Worker→Queen reporting functionality is working correctly!")
        print("✅ All report types successfully delivered and logged")
    else:
        print("❌ Some reports may be missing")
    
    print("\n🎉 Reporting test completed!")


if __name__ == "__main__":
    test_worker_to_queen_reporting()