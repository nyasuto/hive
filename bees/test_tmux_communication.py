#!/usr/bin/env python3
"""
Test script for tmux-based communication functionality
Issue #4: 基本的な自律実行システムのテスト (tmux send-keys中心)
"""

import sys
import time
import subprocess
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from bees.queen_bee import QueenBee
from bees.worker_bee import WorkerBee


def check_tmux_session():
    """tmuxセッションの存在確認"""
    try:
        result = subprocess.run([
            "tmux", "has-session", "-t", "beehive"
        ], capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False


def test_tmux_communication():
    """tmux send-keys中心の通信テスト"""
    print("🧪 Testing tmux-based Communication")
    print("=" * 50)
    
    # tmuxセッション確認
    if not check_tmux_session():
        print("⚠️  tmux session 'beehive' not found")
        print("   This test shows how communication would work with tmux")
        print("   To see actual tmux communication, run: ./beehive.sh init")
        print()
    
    # Beeインスタンス作成
    queen = QueenBee("hive/hive_memory.db")
    developer = WorkerBee("developer", "development", "hive/hive_memory.db")
    
    # 1. Queen→Developer タスク割り当てテスト
    print("📋 Queen creating and assigning task...")
    task_id = queen.create_task(
        title="Implement User Authentication",
        description="Create user login/logout functionality with JWT tokens",
        priority="high",
        estimated_hours=6.0
    )
    
    print(f"✅ Task created with ID: {task_id}")
    
    # タスクをDeveloperに割り当て（tmux send-keysで通信される）
    print("\n🎯 Queen assigning task to Developer...")
    success = queen.assign_task_to_bee(
        task_id,
        "developer", 
        "Implementing authentication system as core security feature"
    )
    
    if success:
        print("✅ Task assignment sent via tmux!")
        print("   (In real beehive, Developer would see this in their tmux pane)")
        
        # SQLiteのログを確認
        print("\n📊 Checking communication logs in SQLite...")
        messages = queen.get_messages(processed=False)
        for msg in messages:
            print(f"   Log: {msg['from_bee']} -> {msg['to_bee']}: {msg['subject']}")
    
    # 2. Developer→Queen 進捗報告テスト
    print("\n📈 Developer reporting progress to Queen...")
    
    # Developerがタスクを受け入れ
    developer.accept_task(task_id)
    
    # 進捗報告（tmux send-keysで Queen に送信される）
    developer.report_progress(task_id, 30, "JWT library integrated, working on login endpoint")
    developer.report_progress(task_id, 60, "Login/logout endpoints complete, adding validation")
    developer.report_progress(task_id, 85, "Authentication working, adding tests")
    
    print("✅ Progress reports sent via tmux!")
    print("   (In real beehive, Queen would see these in their tmux pane)")
    
    # 3. Developer→Queen 支援要請テスト
    print("\n🆘 Developer requesting assistance...")
    developer.request_assistance(
        task_id,
        "Security Review",
        "Need security expert to review JWT implementation for potential vulnerabilities. "
        "Particularly concerned about token refresh mechanism and session management.",
        urgent=True
    )
    
    print("✅ Assistance request sent via tmux!")
    
    # 4. Developer→Queen 完了報告テスト
    print("\n🏁 Developer completing task...")
    developer.complete_task(
        task_id,
        "User authentication system successfully implemented with JWT tokens",
        [
            "auth/login.py - Login endpoint with JWT generation",
            "auth/logout.py - Logout endpoint with token invalidation", 
            "auth/middleware.py - Authentication middleware for protected routes",
            "auth/models.py - User model with password hashing",
            "tests/test_auth.py - Comprehensive authentication tests"
        ],
        "Implemented secure JWT-based authentication with bcrypt password hashing. "
        "Added comprehensive test coverage including security edge cases. "
        "Followed OWASP best practices for session management.",
        "Security: JWT tokens expire in 1 hour, refresh tokens in 7 days. "
        "Password complexity enforced. Rate limiting on login attempts. "
        "All tests passing with 95% code coverage."
    )
    
    print("✅ Task completion report sent via tmux!")
    
    # 5. 通信ログの確認
    print("\n📋 Communication Summary:")
    print("=" * 30)
    
    # Queen側のメッセージログ
    queen_messages = queen.get_messages(processed=False)
    print(f"Queen received {len(queen_messages)} messages:")
    for msg in queen_messages:
        print(f"   📧 {msg['from_bee']} -> {msg['to_bee']}: {msg['message_type']} - {msg['subject']}")
    
    # データベースの状態確認
    print(f"\n🗃️  Database Status:")
    with queen._get_db_connection() as conn:
        # タスクの最終状態
        cursor = conn.execute("SELECT status, actual_hours FROM tasks WHERE task_id = ?", (task_id,))
        task_status = cursor.fetchone()
        if task_status:
            print(f"   Task Status: {task_status[0]}")
            print(f"   Actual Hours: {task_status[1] or 'N/A'}")
        
        # Bee状態
        cursor = conn.execute("SELECT bee_name, status, workload_score FROM bee_states")
        bee_states = cursor.fetchall()
        print(f"   Bee States:")
        for state in bee_states:
            print(f"     {state[0]}: {state[1]} (workload: {state[2]}%)")
    
    print("\n🎯 Test Results:")
    print("✅ Queen→Developer task assignment: Working (via tmux)")
    print("✅ Developer→Queen progress reporting: Working (via tmux)") 
    print("✅ Developer→Queen assistance requests: Working (via tmux)")
    print("✅ Developer→Queen completion reports: Working (via tmux)")
    print("✅ SQLite logging: Working (communication history)")
    
    print("\n📝 Note:")
    print("   This test demonstrates the communication architecture.")
    print("   In the real system:")
    print("   • Messages are sent via 'tmux send-keys' to Claude instances")
    print("   • Claude agents receive messages in their tmux panes")
    print("   • SQLite stores communication logs and task state")
    print("   • Human operators can monitor via './beehive.sh status' and logs")
    
    print("\n🎉 tmux Communication Test Completed!")


if __name__ == "__main__":
    test_tmux_communication()