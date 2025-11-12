#!/usr/bin/env python3
"""
データベースセットアップスクリプト
勤怠管理システムのテーブル作成とサンプルデータ投入
"""
import os
import sys
from pathlib import Path

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import random

from attendance_system.models import Base, User, SuicaRegistration, AttendanceRecord
from attendance_system.security.security_manager import SecurityManager, SecurityContext

# データベース設定
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./attendance.db")

def create_database():
    """データベースとテーブルを作成"""
    print("📊 データベース作成中...")
    
    # エンジン作成
    engine = create_engine(DATABASE_URL, echo=False)
    
    # テーブル作成
    Base.metadata.create_all(bind=engine)
    
    print("✅ テーブル作成完了")
    return engine

def create_sample_data(engine):
    """サンプルデータ作成"""
    print("📝 サンプルデータ作成中...")
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # サンプルユーザー作成
        users = [
            User(name="田中太郎", employee_id="E001", department="開発部"),
            User(name="佐藤花子", employee_id="E002", department="営業部"),
            User(name="鈴木一郎", employee_id="E003", department="総務部"),
            User(name="高橋美咲", employee_id="E004", department="開発部"),
            User(name="伊藤健二", employee_id="E005", department="営業部"),
        ]
        
        for user in users:
            session.add(user)
        
        session.commit()
        
        # Suica登録（最初の3人）
        security_manager = SecurityManager()
        
        for i, user in enumerate(users[:3]):
            # ダミーIDM（実際はSuicaから読み取る）- 16文字
            dummy_idm = f"SUICA{i+1:011X}"  # SUICA + 11桁の16進数 = 16文字
            context = SecurityContext(user_id=str(user.id), timestamp=datetime.now())
            hashed_idm = security_manager.secure_nfc_idm(dummy_idm, context)
            
            suica_reg = SuicaRegistration(
                user_id=user.id,
                suica_idm_hash=hashed_idm,
                is_active=True
            )
            session.add(suica_reg)
        
        session.commit()
        
        # 過去7日間の勤怠記録を生成
        today = datetime.now().date()
        for user in users[:3]:  # Suica登録済みユーザーのみ
            for days_ago in range(7):
                date = today - timedelta(days=days_ago)
                
                # 週末はスキップ
                if date.weekday() >= 5:
                    continue
                
                # 出勤時刻（8:00-9:30のランダム）
                check_in_hour = 8 + random.randint(0, 1)
                check_in_minute = random.randint(0, 59) if check_in_hour == 8 else random.randint(0, 30)
                check_in_time = datetime.combine(
                    date,
                    datetime.min.time().replace(
                        hour=check_in_hour,
                        minute=check_in_minute
                    )
                )
                
                # 退勤時刻（17:00-20:00のランダム）
                check_out_time = datetime.combine(
                    date,
                    datetime.min.time().replace(
                        hour=17 + random.randint(0, 3),
                        minute=random.randint(0, 59)
                    )
                )
                
                # 勤怠記録作成
                check_in = AttendanceRecord(
                    user_id=user.id,
                    timestamp=check_in_time,
                    type="check_in",
                    location="本社"
                )
                
                check_out = AttendanceRecord(
                    user_id=user.id,
                    timestamp=check_out_time,
                    type="check_out",
                    location="本社"
                )
                
                session.add(check_in)
                session.add(check_out)
        
        session.commit()
        
        print("✅ サンプルデータ作成完了")
        
        # 作成結果表示
        user_count = session.query(User).count()
        suica_count = session.query(SuicaRegistration).filter(SuicaRegistration.is_active).count()
        record_count = session.query(AttendanceRecord).count()
        
        print(f"\n📊 データベース統計:")
        print(f"  - ユーザー数: {user_count}人")
        print(f"  - Suica登録数: {suica_count}枚")
        print(f"  - 勤怠記録数: {record_count}件")
        
    except Exception as e:
        session.rollback()
        print(f"❌ エラー: {e}")
        raise
    finally:
        session.close()

def show_database_info(engine):
    """データベース情報表示"""
    print("\n📋 テーブル一覧:")
    
    with engine.connect() as conn:
        # SQLiteの場合
        if DATABASE_URL.startswith("sqlite"):
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ))
            tables = [row[0] for row in result]
        else:
            # PostgreSQL/MySQLの場合
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            ))
            tables = [row[0] for row in result]
        
        for table in tables:
            print(f"  - {table}")

def main():
    """メイン処理"""
    print("🚀 勤怠管理システム データベースセットアップ")
    print("=" * 50)
    
    # コマンドライン引数チェック
    force_create = "--force" in sys.argv
    with_sample = "--with-sample" in sys.argv or "-s" in sys.argv
    
    # 既存のデータベースファイルチェック
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        if os.path.exists(db_path):
            if force_create:
                print(f"\n⚠️  {db_path} を上書きします...")
                os.remove(db_path)
            else:
                response = input(f"\n⚠️  {db_path} は既に存在します。上書きしますか？ (y/N): ")
                if response.lower() != 'y':
                    print("セットアップを中止しました")
                    return
                os.remove(db_path)
    
    try:
        # データベース作成
        engine = create_database()
        
        # サンプルデータ作成
        if with_sample:
            create_sample_data(engine)
        else:
            response = input("\nサンプルデータを作成しますか？ (Y/n): ")
            if response.lower() != 'n':
                create_sample_data(engine)
        
        # データベース情報表示
        show_database_info(engine)
        
        print("\n✅ セットアップ完了！")
        print("\n💡 使い方:")
        print("  1. ~/start-attendance.sh でシステム起動")
        print("  2. ブラウザで /admin にアクセスして管理")
        
    except Exception as e:
        print(f"\n❌ セットアップ失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()