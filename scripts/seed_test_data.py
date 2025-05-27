#!/usr/bin/env python3
"""
テストデータ投入スクリプト
6名の従業員データを投入します
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import date
import hashlib
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, engine
from backend.app.models import Employee, WageType
from backend.app.models.user import User, UserRole
from passlib.context import CryptContext

# パスワードハッシュ化の設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_idm(card_idm: str) -> str:
    """カードIDMをハッシュ化"""
    # 環境変数から秘密鍵を取得
    import os
    secret = os.getenv("IDM_HASH_SECRET", "ada74e23c2c4e991ccef427accebaf0d34b5b76963575ee84f34b0c27172b8d3")
    return hashlib.sha256(f"{card_idm}{secret}".encode()).hexdigest()


def create_test_employees(db: Session):
    """テスト用従業員データを作成"""
    
    test_employees = [
        {
            "employee_code": "AUTO_001",
            "name": "テスト太郎",
            "name_kana": "テストタロウ",
            "email": "test1@example.com",
            "card_idm": "AUTO_CARD_001",
            "department": "開発部",
            "position": "エンジニア",
            "employment_type": "正社員",
            "wage_type": WageType.MONTHLY,
            "monthly_salary": 300000,
        },
        {
            "employee_code": "AUTO_002",
            "name": "テスト花子",
            "name_kana": "テストハナコ",
            "email": "test2@example.com",
            "card_idm": "AUTO_CARD_002",
            "department": "営業部",
            "position": "マネージャー",
            "employment_type": "正社員",
            "wage_type": WageType.MONTHLY,
            "monthly_salary": 400000,
        },
        {
            "employee_code": "AUTO_003",
            "name": "テスト次郎",
            "name_kana": "テストジロウ",
            "email": "test3@example.com",
            "card_idm": "AUTO_CARD_003",
            "department": "開発部",
            "position": "エンジニア",
            "employment_type": "正社員",
            "wage_type": WageType.MONTHLY,
            "monthly_salary": 280000,
        },
        {
            "employee_code": "AUTO_004",
            "name": "テスト美咲",
            "name_kana": "テストミサキ",
            "email": "test4@example.com",
            "card_idm": "AUTO_CARD_004",
            "department": "人事部",
            "position": "スタッフ",
            "employment_type": "パート",
            "wage_type": WageType.HOURLY,
            "hourly_rate": 1200,
        },
        {
            "employee_code": "AUTO_005",
            "name": "テスト健太",
            "name_kana": "テストケンタ",
            "email": "test5@example.com",
            "card_idm": "AUTO_CARD_005",
            "department": "総務部",
            "position": "リーダー",
            "employment_type": "正社員",
            "wage_type": WageType.MONTHLY,
            "monthly_salary": 350000,
        },
        {
            "employee_code": "AUTO_006",
            "name": "テスト優子",
            "name_kana": "テストユウコ",
            "email": "test6@example.com",
            "card_idm": "AUTO_CARD_006",
            "department": "経理部",
            "position": "スタッフ",
            "employment_type": "アルバイト",
            "wage_type": WageType.HOURLY,
            "hourly_rate": 1000,
        },
    ]
    
    # 既存データを削除
    db.query(User).delete()
    db.query(Employee).delete()
    db.commit()
    
    # テストデータを投入
    for emp_data in test_employees:
        card_idm = emp_data.pop("card_idm")
        
        # 従業員を作成
        employee = Employee(
            **emp_data,
            card_idm_hash=hash_idm(card_idm),
            hire_date=date(2023, 4, 1),
            is_active=True
        )
        db.add(employee)
        db.flush()  # IDを取得
        
        # ユーザーアカウントを作成（従業員コードと同じパスワード）
        user = User(
            username=emp_data["employee_code"],
            password_hash=pwd_context.hash(emp_data["employee_code"]),
            employee_id=employee.id,
            role=UserRole.ADMIN if emp_data["employee_code"] == "AUTO_001" else UserRole.EMPLOYEE,
            is_active=True
        )
        db.add(user)
    
    db.commit()
    print(f"✅ {len(test_employees)}名の従業員データを投入しました")


def main():
    """メイン処理"""
    print("🔄 テストデータ投入を開始します...")
    
    db = SessionLocal()
    try:
        create_test_employees(db)
        
        # 確認
        employees = db.query(Employee).all()
        print("\n📋 投入された従業員データ:")
        for emp in employees:
            print(f"  - {emp.employee_code}: {emp.name} ({emp.department} {emp.position})")
        
        print("\n✅ テストデータ投入が完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()