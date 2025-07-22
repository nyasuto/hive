#!/usr/bin/env python3
"""
Test script for Queen→Worker task assignment functionality
Issue #4: 基本的な自律実行システムのテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from bees.queen_bee import QueenBee
from bees.worker_bee import WorkerBee


def test_queen_to_worker_assignment():
    """Queen→Worker タスク割り当てのテスト"""
    print("🧪 Testing Queen→Worker Task Assignment")
    print("=" * 50)

    # Beeインスタンス作成
    queen = QueenBee("hive/hive_memory.db")
    developer = WorkerBee("developer", "development", "hive/hive_memory.db")

    # テストタスクを作成
    print("📋 Creating test task...")
    task_id = queen.create_task(
        title="Create Hello World App",
        description="Implement a simple Hello World application with proper structure",
        priority="medium",
        estimated_hours=2.0,
    )
    print(f"✅ Task created with ID: {task_id}")

    # タスクをDeveloper Beeに割り当て
    print("\n🎯 Assigning task to Developer Bee...")
    success = queen.assign_task_to_bee(
        task_id, "developer", "Initial development task for testing autonomous execution system"
    )

    if success:
        print("✅ Task assigned successfully!")

        # メッセージが送信されたかチェック
        print("\n📨 Checking messages...")
        messages = developer.get_messages(processed=False)
        print(f"Developer has {len(messages)} unread messages")

        for msg in messages:
            print(f"  - From: {msg['from_bee']}")
            print(f"    Type: {msg['message_type']}")
            print(f"    Subject: {msg['subject']}")
            print(f"    Task ID: {msg.get('task_id')}")

        # Developer Beeがタスクを受け入れ
        print("\n🤝 Developer accepting task...")
        if developer.accept_task(task_id):
            print("✅ Task accepted!")

            # 進捗報告のテスト
            print("\n📊 Reporting progress...")
            developer.report_progress(task_id, 25, "Set up project structure")
            developer.report_progress(task_id, 50, "Implemented core functionality")
            developer.report_progress(task_id, 75, "Added documentation")

            # 作業完了のテスト
            print("\n🏁 Completing task...")
            developer.complete_task(
                task_id,
                "Hello World application successfully implemented",
                ["main.py", "README.md", "requirements.txt"],
                "Clean implementation with proper error handling",
                "All tests passed, code follows best practices",
            )
            print("✅ Task completed!")

            # Queenのメッセージをチェック
            print("\n📨 Checking Queen's messages...")
            queen_messages = queen.get_messages(processed=False)
            print(f"Queen has {len(queen_messages)} unread messages")

            for msg in queen_messages:
                print(f"  - From: {msg['from_bee']}")
                print(f"    Type: {msg['message_type']}")
                print(f"    Subject: {msg['subject'][:50]}...")

        else:
            print("❌ Failed to accept task")
    else:
        print("❌ Failed to assign task")

    print("\n🎉 Test completed!")


if __name__ == "__main__":
    test_queen_to_worker_assignment()
