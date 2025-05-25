#!/usr/bin/env python3
"""
データベース初期化スクリプト
テスト運用開始前にデータベースとディレクトリを準備
"""

import os
import sqlite3
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def init_database():
    """データベースとディレクトリの初期化"""
    print("🗄️ データベース初期化を開始します...")
    
    # 必要ディレクトリ作成
    for dir_name in ['data', 'logs', 'backup']:
        dir_path = project_root / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"✅ Directory created: {dir_name}")
    
    # データベース初期化
    db_path = project_root / "data" / "attendance.db"
    
    try:
        # データベース接続テスト
        with sqlite3.connect(str(db_path)) as conn:
            # 基本テーブル確認・作成
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"✅ Database connection OK: {db_path}")
            print(f"📊 Found {len(tables)} tables in database")
            
            # 基本的なテーブルが存在しない場合は警告
            table_names = [table[0] for table in tables]
            required_tables = ['employees', 'punch_records']
            missing_tables = [t for t in required_tables if t not in table_names]
            
            if missing_tables:
                print(f"⚠️ Missing tables detected: {missing_tables}")
                print("💡 Run 'alembic upgrade head' to create missing tables")
            else:
                print("✅ All required tables are present")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("🔧 Creating empty database file...")
        
        # 空のデータベースファイルを作成
        db_path.touch()
        
        # 再度接続テスト
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("SELECT 1")
                print(f"✅ Empty database created: {db_path}")
        except Exception as e2:
            print(f"❌ Failed to create database: {e2}")
            raise
    
    # オフラインキュー用データベースも初期化
    offline_db_path = project_root / "data" / "offline_queue.db"
    try:
        with sqlite3.connect(str(offline_db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offline_punches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT NOT NULL,
                    punch_type TEXT NOT NULL,
                    card_idm_hash TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    device_type TEXT,
                    ip_address TEXT,
                    location_lat REAL,
                    location_lon REAL,
                    note TEXT,
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_at TEXT,
                    error_message TEXT,
                    data_hash TEXT NOT NULL UNIQUE
                )
            """)
            conn.commit()
            print(f"✅ Offline queue database initialized: {offline_db_path}")
    except Exception as e:
        print(f"⚠️ Failed to initialize offline queue database: {e}")
    
    print("🎉 データベース初期化が完了しました！")


def check_environment():
    """環境チェック"""
    print("🔍 環境チェックを実行します...")
    
    # Python バージョンチェック
    python_version = sys.version_info
    print(f"🐍 Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("⚠️ Python 3.8+ required")
    
    # 設定ファイルチェック
    config_file = project_root / "config" / "config.py"
    if config_file.exists():
        print(f"✅ Config file found: {config_file}")
    else:
        print(f"❌ Config file not found: {config_file}")
    
    # requirements.txt チェック
    requirements_file = project_root / "requirements.txt"
    if requirements_file.exists():
        print(f"✅ Requirements file found: {requirements_file}")
    else:
        print(f"⚠️ Requirements file not found: {requirements_file}")
    
    print("✅ 環境チェック完了")


if __name__ == "__main__":
    check_environment()
    init_database()