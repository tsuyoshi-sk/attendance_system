"""
従業員モデル

従業員情報を管理するデータベースモデル
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, Enum, ForeignKey
from sqlalchemy.orm import relationship
from typing import Optional
import enum

from backend.app.database import Base


class WageType(str, enum.Enum):
    """賃金タイプ"""
    HOURLY = "HOURLY"      # 時給制
    MONTHLY = "MONTHLY"    # 月給制


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
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    position = Column(String(100), nullable=True)
    
    # 雇用形態
    employment_type = Column(String(20), nullable=False, default="正社員")  # 正社員、パート、アルバイト等
    hire_date = Column(Date, nullable=True)
    
    # 賃金情報
    wage_type = Column(Enum(WageType), nullable=False, default=WageType.MONTHLY)
    hourly_rate = Column(Numeric(10, 2), nullable=True)  # 時給 (時給制の場合)
    monthly_salary = Column(Integer, nullable=True)       # 月給 (月給制の場合)
    
    # ステータス
    is_active = Column(Boolean, default=True, nullable=False)
    
    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # リレーション
    department = relationship("Department", back_populates="employees")
    punch_records = relationship(
        "PunchRecord", 
        foreign_keys="PunchRecord.employee_id",
        back_populates="employee", 
        cascade="all, delete-orphan"
    )
    daily_summaries = relationship(
        "DailySummary", 
        foreign_keys="DailySummary.employee_id",
        back_populates="employee", 
        cascade="all, delete-orphan"
    )
    monthly_summaries = relationship(
        "MonthlySummary", 
        foreign_keys="MonthlySummary.employee_id",
        back_populates="employee", 
        cascade="all, delete-orphan"
    )
    cards = relationship("EmployeeCard", back_populates="employee", cascade="all, delete-orphan")
    user = relationship("User", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    
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
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "wage_type": self.wage_type.value.lower() if self.wage_type else None,
            "hourly_rate": float(self.hourly_rate) if self.hourly_rate else None,
            "monthly_salary": self.monthly_salary,
            "is_active": self.is_active,
            "has_card": bool(self.card_idm_hash),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
