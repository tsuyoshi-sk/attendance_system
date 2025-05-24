"""
従業員モデル

従業員情報を管理するデータベースモデル
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from typing import Optional

from backend.app.database import Base


class Employee(Base):
    """従業員テーブル"""
    
    __tablename__ = "employees"
    
    # 主キー
    id = Column(Integer, primary_key=True, index=True)
    
    # 従業員情報
    employee_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_kana = Column(String(100), nullable=True)
    email = Column(String(254), unique=True, nullable=True, index=True)
    
    # カード情報（ハッシュ化されたIDm）
    card_idm_hash = Column(String(64), unique=True, nullable=True, index=True)
    
    # 部署・役職
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    
    # 雇用形態
    employment_type = Column(String(20), nullable=False, default="正社員")  # 正社員、パート、アルバイト等
    
    # ステータス
    is_active = Column(Boolean, default=True, nullable=False)
    
    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # リレーション
    punch_records = relationship("PunchRecord", back_populates="employee", cascade="all, delete-orphan")
    daily_summaries = relationship("DailySummary", back_populates="employee", cascade="all, delete-orphan")
    monthly_summaries = relationship("MonthlySummary", back_populates="employee", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, code={self.employee_code}, name={self.name})>"
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "employee_code": self.employee_code,
            "name": self.name,
            "name_kana": self.name_kana,
            "email": self.email,
            "department": self.department,
            "position": self.position,
            "employment_type": self.employment_type,
            "is_active": self.is_active,
            "has_card": bool(self.card_idm_hash),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }