#!/usr/bin/env python3
"""
FeliCa対応のためのデータベースマイグレーション
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.attendance_system.database import engine

def migrate_database():
    """データベースにFeliCa関連カラムを追加"""
    print("🔄 データベースマイグレーション開始...")
    
    with engine.connect() as conn:
        try:
            # attendance_records テーブルに felica_idm カラムを追加
            conn.execute(text("""
                ALTER TABLE attendance_records 
                ADD COLUMN felica_idm VARCHAR(16)
            """))
            conn.commit()
            print("✅ attendance_records.felica_idm カラム追加完了")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  felica_idm カラムは既に存在します")
            else:
                print(f"❌ エラー: {e}")
                raise
    
    print("✅ マイグレーション完了")

if __name__ == "__main__":
    migrate_database()