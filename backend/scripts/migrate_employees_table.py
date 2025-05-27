#!/usr/bin/env python3
"""
従業員テーブルのマイグレーションスクリプト

現在のテーブル構造:
- id INTEGER PRIMARY KEY
- name TEXT NOT NULL
- employee_code TEXT UNIQUE
- card_idm_hash TEXT
- is_active INTEGER DEFAULT 1
- created_at TIMESTAMP

追加する必要があるカラム:
- name_kana TEXT
- email TEXT UNIQUE
- department TEXT
- position TEXT
- employment_type TEXT DEFAULT '正社員'
- hire_date DATE
- wage_type TEXT DEFAULT 'monthly'
- hourly_rate DECIMAL(10,2)
- monthly_salary INTEGER
- updated_at TIMESTAMP
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートのパスを追加
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

def migrate_employees_table():
    """従業員テーブルに不足しているカラムを追加"""
    db_path = project_root / "attendance.db"
    
    if not db_path.exists():
        print(f"エラー: データベースファイルが見つかりません: {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 現在のカラムを確認
        cursor.execute("PRAGMA table_info(employees)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"現在のカラム: {existing_columns}")
        
        # 追加するカラムとそのSQL
        columns_to_add = [
            ("name_kana", "ALTER TABLE employees ADD COLUMN name_kana TEXT"),
            ("email", "ALTER TABLE employees ADD COLUMN email TEXT UNIQUE"),
            ("department", "ALTER TABLE employees ADD COLUMN department TEXT"),
            ("position", "ALTER TABLE employees ADD COLUMN position TEXT"),
            ("employment_type", "ALTER TABLE employees ADD COLUMN employment_type TEXT DEFAULT '正社員'"),
            ("hire_date", "ALTER TABLE employees ADD COLUMN hire_date DATE"),
            ("wage_type", "ALTER TABLE employees ADD COLUMN wage_type TEXT DEFAULT 'monthly'"),
            ("hourly_rate", "ALTER TABLE employees ADD COLUMN hourly_rate DECIMAL(10,2)"),
            ("monthly_salary", "ALTER TABLE employees ADD COLUMN monthly_salary INTEGER"),
            ("updated_at", "ALTER TABLE employees ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]
        
        # 不足しているカラムを追加
        for column_name, sql in columns_to_add:
            if column_name not in existing_columns:
                print(f"カラムを追加: {column_name}")
                cursor.execute(sql)
            else:
                print(f"カラムは既に存在: {column_name}")
        
        # 既存のレコードのupdated_atを現在時刻に設定
        if "updated_at" not in existing_columns:
            cursor.execute("UPDATE employees SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        
        # 変更をコミット
        conn.commit()
        print("\nマイグレーションが正常に完了しました")
        
        # 更新後のスキーマを確認
        cursor.execute("PRAGMA table_info(employees)")
        print("\n更新後のテーブル構造:")
        for row in cursor.fetchall():
            print(f"  {row[1]} {row[2]} {'NOT NULL' if row[3] else ''} {'DEFAULT ' + str(row[4]) if row[4] is not None else ''}")
        
        return True
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("従業員テーブルのマイグレーションを開始します...")
    success = migrate_employees_table()
    sys.exit(0 if success else 1)