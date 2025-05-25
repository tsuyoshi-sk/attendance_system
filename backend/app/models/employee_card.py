"""
従業員カード管理モデル

従業員のICカード情報を管理するデータベースモデル
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship

from backend.app.database import Base


class EmployeeCard(Base):
    """従業員カードテーブル"""
    
    __tablename__ = "employee_cards"
    
    # 主キー
    id = Column(Integer, primary_key=True, index=True)
    
    # 従業員との関連
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # カード情報
    card_idm_hash = Column(String(64), unique=True, nullable=False, index=True)
    card_nickname = Column(String(50), nullable=True)  # "社員証", "予備カード" など
    
    # 発行情報
    issued_date = Column(Date, nullable=True)
    
    # ステータス
    is_active = Column(Boolean, default=True, nullable=False)
    
    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # リレーション
    employee = relationship("Employee", back_populates="cards")
    
    def __repr__(self) -> str:
        return f"<EmployeeCard(id={self.id}, employee_id={self.employee_id}, nickname={self.card_nickname})>"
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "card_nickname": self.card_nickname,
            "issued_date": self.issued_date.isoformat() if self.issued_date else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }