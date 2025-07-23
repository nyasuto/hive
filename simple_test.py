#!/usr/bin/env python3
"""
Simple Test Suite for Test Implementation Verification
Issue #23: テストスイート強化とコード品質向上
"""

import pytest
import sqlite3
import tempfile
import os

def test_test_files_exist():
    """テストファイルが作成されていることを確認"""
    test_files = [
        "bees/test_queen_bee_unit.py",
        "bees/test_worker_bee_unit.py", 
        "bees/test_full_workflow_integration.py",
        "bees/conftest.py",
        "pytest.ini"
    ]
    
    for file_path in test_files:
        assert os.path.exists(file_path), f"Test file {file_path} not found"
        assert os.path.getsize(file_path) > 0, f"Test file {file_path} is empty"


def test_pytest_configuration():
    """pytest設定ファイルの内容確認"""
    with open("pytest.ini", "r") as f:
        content = f.read()
    
    # 重要な設定項目が含まれていることを確認
    assert "testpaths" in content
    assert "cov-fail-under=90" in content
    assert "markers" in content


def test_database_schema_creation():
    """データベーススキーマ作成の基本テスト"""
    from bees.conftest import _create_test_schema
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # スキーマ作成
        _create_test_schema(conn)
        
        # テーブルが作成されていることを確認
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            "tasks", "task_assignments", "task_activity", 
            "bee_states", "bee_messages", "context_snapshots", "decision_log"
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found"
        
        conn.close()
        
    finally:
        os.unlink(db_path)


def test_makefile_commands():
    """Makefileのテストコマンドが存在することを確認"""
    with open("Makefile", "r") as f:
        content = f.read()
    
    # 新しく追加したテストコマンドが存在することを確認
    assert "test-all:" in content
    assert "test-unit:" in content
    assert "test-integration:" in content
    assert "test-coverage:" in content


if __name__ == "__main__":
    # 基本的なテスト実行
    test_test_files_exist()
    test_pytest_configuration() 
    test_database_schema_creation()
    test_makefile_commands()
    print("✅ All basic tests passed!")