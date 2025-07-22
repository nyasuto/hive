#!/usr/bin/env python3
"""
Database initialization for testing
"""

import sqlite3
from pathlib import Path


def init_database():
    """テスト用データベースを初期化"""
    project_root = Path(__file__).parent.parent
    db_path = project_root / "hive" / "hive_memory.db"
    schema_path = project_root / "hive" / "schema.sql"

    # hiveディレクトリが存在しない場合は作成
    db_path.parent.mkdir(exist_ok=True)

    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_path}")
        return False

    print(f"Initializing database: {db_path}")

    try:
        # データベース作成・初期化
        conn = sqlite3.connect(str(db_path))

        # スキーマファイルを実行
        with open(schema_path, encoding="utf-8") as f:
            schema_sql = f.read()

        conn.executescript(schema_sql)
        conn.commit()
        conn.close()

        print("✅ Database initialized successfully!")
        return True

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    init_database()
