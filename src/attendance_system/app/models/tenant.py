"""
テナントモデル

マルチテナント対応のためのテナント管理
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from typing import Dict, Any

from backend.app.database import Base


class Tenant(Base):
    """テナント（組織）テーブル"""

    __tablename__ = "tenants"

    # 主キー
    id = Column(Integer, primary_key=True, index=True)

    # テナント基本情報
    name = Column(String(200), nullable=False)
    domain = Column(String(100), unique=True, nullable=False, index=True)
    subdomain = Column(String(50), unique=True, nullable=True, index=True)

    # 連絡先情報
    contact_email = Column(String(254), nullable=False)
    contact_phone = Column(String(20), nullable=True)

    # 住所情報
    address = Column(Text, nullable=True)

    # プラン・制限
    plan = Column(
        String(50), nullable=False, default="basic"
    )  # basic, standard, premium
    max_employees = Column(Integer, nullable=False, default=100)
    max_departments = Column(Integer, nullable=False, default=10)

    # 機能フラグ
    features = Column(JSON, nullable=True, default={})

    # テナント固有設定
    settings = Column(JSON, nullable=True, default={})

    # ステータス
    is_active = Column(Boolean, default=True, nullable=False)
    is_trial = Column(Boolean, default=False, nullable=False)
    trial_expires_at = Column(DateTime, nullable=True)

    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # リレーション（将来の実装用）
    # employees = relationship("Employee", back_populates="tenant")
    # departments = relationship("Department", back_populates="tenant")
    # users = relationship("User", back_populates="tenant")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, domain={self.domain}, name={self.name})>"

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "address": self.address,
            "plan": self.plan,
            "max_employees": self.max_employees,
            "max_departments": self.max_departments,
            "features": self.features or {},
            "settings": self.settings or {},
            "is_active": self.is_active,
            "is_trial": self.is_trial,
            "trial_expires_at": self.trial_expires_at.isoformat()
            if self.trial_expires_at
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_feature_flag(self, feature_name: str, default: bool = False) -> bool:
        """機能フラグを取得"""
        if not self.features:
            return default
        return self.features.get(feature_name, default)

    def get_setting(self, setting_name: str, default: Any = None) -> Any:
        """設定値を取得"""
        if not self.settings:
            return default
        return self.settings.get(setting_name, default)

    def can_add_employee(self, current_count: int) -> bool:
        """従業員追加可能かチェック"""
        return current_count < self.max_employees

    def can_add_department(self, current_count: int) -> bool:
        """部署追加可能かチェック"""
        return current_count < self.max_departments

    def is_trial_expired(self) -> bool:
        """トライアル期間が終了しているかチェック"""
        if not self.is_trial or not self.trial_expires_at:
            return False
        return datetime.utcnow() > self.trial_expires_at
