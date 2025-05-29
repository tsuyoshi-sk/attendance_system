"""
部署モデル

部署情報を管理するデータベースモデル
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.database import Base


class Department(Base):
    """部署テーブル"""

    __tablename__ = "departments"

    # 主キー
    id = Column(Integer, primary_key=True, index=True)

    # 部署情報
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)

    # 管理者
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # ステータス
    is_active = Column(Boolean, default=True, nullable=False)

    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # リレーション
    employees = relationship("Employee", back_populates="department")

    def __repr__(self) -> str:
        return f"<Department(id={self.id}, code={self.code}, name={self.name})>"

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "manager_id": self.manager_id,
            "is_active": self.is_active,
            "employee_count": len(self.employees) if self.employees else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
