#!/usr/bin/env python3
"""
テーブル作成とテストデータ投入スクリプト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import engine, Base, get_db
from backend.app.models import Employee, PunchRecord, DailySummary, MonthlySummary
from backend.app.utils.security import CryptoUtils
from sqlalchemy.orm import Session
from datetime import datetime, date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_all_tables():
    """全テーブルを作成"""
    logger.info("テーブルを作成しています...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ テーブル作成完了")

def create_test_employees(db: Session):
    """テスト用従業員データを作成"""
    test_employees = [
        {
            "employee_code": f"AUTO_{i:03d}",
            "name": f"テスト従業員{i}",
            "name_kana": f"テストジュウギョウイン{i}",
            "email": f"test{i}@example.com",
            "card_idm": f"AUTO_CARD_{i:03d}",
            "department": "開発部" if i <= 3 else "営業部",
            "position": "一般" if i <= 4 else "主任",
            "employment_type": "正社員",
            "wage_type": "MONTHLY",
            "monthly_salary": 300000 + (i * 10000),
            "is_active": True
        }
        for i in range(1, 7)
    ]
    
    for emp_data in test_employees:
        # カードIDMをハッシュ化
        card_idm = emp_data.pop("card_idm")
        emp_data["card_idm_hash"] = CryptoUtils.hash_idm(card_idm)
        
        # 従業員を作成
        employee = Employee(**emp_data)
        db.add(employee)
        logger.info(f"✅ 従業員作成: {employee.name} (カードIDM: {card_idm})")
    
    db.commit()
    logger.info(f"✅ {len(test_employees)}名の従業員データを作成しました")

def main():
    """メイン処理"""
    logger.info("=== データベース初期化開始 ===")
    
    # テーブル作成
    create_all_tables()
    
    # データベースセッション取得
    db = next(get_db())
    
    try:
        # 既存データ確認
        existing_count = db.query(Employee).count()
        if existing_count > 0:
            logger.info(f"既存の従業員データが {existing_count} 件存在します")
        else:
            # テスト従業員作成
            create_test_employees(db)
        
        # 作成結果確認
        total_employees = db.query(Employee).count()
        logger.info(f"📊 総従業員数: {total_employees}")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
    logger.info("=== データベース初期化完了 ===")

if __name__ == "__main__":
    main()