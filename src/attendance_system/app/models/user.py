"""
ユーザー認証モデル

ユーザー認証情報を管理するデータベースモデル
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from backend.app.database import Base


class UserRole(enum.Enum):
    """ユーザーロール"""

    ADMIN = "admin"  # 管理者
    EMPLOYEE = "employee"  # 従業員
    GUEST = "guest"  # ゲスト（打刻のみ）


class User(Base):
    """ユーザー認証テーブル"""

    __tablename__ = "users"

    # 主キー
    id = Column(Integer, primary_key=True, index=True)

    # 認証情報
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # ロールと権限
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)

    # 従業員との関連（従業員アカウントの場合）
    employee_id = Column(
        Integer, ForeignKey("employees.id"), nullable=True, unique=True
    )

    # ステータス
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # リレーション
    employee = relationship("Employee", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.value if self.role else None,
            "employee_id": self.employee_id,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_permissions(self) -> list:
        """ロールに基づく権限を取得"""
        permissions_map = {
            UserRole.ADMIN: [
                "employee_manage",  # 従業員管理
                "card_manage",  # カード管理
                "report_view",  # レポート閲覧
                "report_export",  # レポートエクスポート
                "system_config",  # システム設定
                "user_manage",  # ユーザー管理
                "punch_all",  # 全員の打刻閲覧
                "punch_edit",  # 打刻編集
            ],
            UserRole.EMPLOYEE: [
                "report_view_self",  # 自分のレポート閲覧
                "punch_self",  # 自分の打刻
                "profile_view_self",  # 自分のプロフィール閲覧
            ],
            UserRole.GUEST: [
                "punch_self",  # 打刻のみ
            ],
        }
        return permissions_map.get(self.role, [])
