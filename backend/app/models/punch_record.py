"""
打刻記録モデル

従業員の打刻記録を管理するデータベースモデル
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Index
from sqlalchemy.orm import relationship
from typing import Optional

from backend.app.database import Base


class PunchType(str, Enum):
    """打刻種別"""
    IN = "in"              # 出勤
    OUT = "out"            # 退勤
    OUTSIDE = "outside"    # 外出
    RETURN = "return"      # 戻り


class PunchRecord(Base):
    """打刻記録テーブル"""
    
    __tablename__ = "punch_records"
    
    # 主キー
    id = Column(Integer, primary_key=True, index=True)
    
    # 外部キー
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # 打刻情報
    punch_type = Column(String(20), nullable=False)
    punch_time = Column(DateTime, nullable=False)
    
    # 位置情報（オプション）
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_name = Column(String(255), nullable=True)
    
    # デバイス情報
    device_type = Column(String(50), nullable=True)  # "pasori", "mobile", "web"等
    device_id = Column(String(100), nullable=True)
    
    # IPアドレス
    ip_address = Column(String(45), nullable=True)
    
    # オフライン打刻フラグ
    is_offline = Column(Boolean, default=False, nullable=False)
    synced_at = Column(DateTime, nullable=True)
    
    # 備考
    note = Column(String(500), nullable=True)
    
    # 修正情報
    is_modified = Column(Boolean, default=False, nullable=False)
    modified_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    modified_at = Column(DateTime, nullable=True)
    original_punch_time = Column(DateTime, nullable=True)
    modification_reason = Column(String(500), nullable=True)
    
    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # リレーション
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="punch_records")
    modifier = relationship("Employee", foreign_keys=[modified_by])
    
    # インデックス
    __table_args__ = (
        Index("idx_employee_punch_time", "employee_id", "punch_time"),
        Index("idx_punch_type_time", "punch_type", "punch_time"),
    )
    
    def __repr__(self) -> str:
        return f"<PunchRecord(id={self.id}, employee_id={self.employee_id}, type={self.punch_type}, time={self.punch_time})>"
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "punch_type": self.punch_type,
            "punch_time": self.punch_time.isoformat() if self.punch_time else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location_name": self.location_name,
            "device_type": self.device_type,
            "device_id": self.device_id,
            "is_offline": self.is_offline,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
            "note": self.note,
            "is_modified": self.is_modified,
            "modified_by": self.modified_by,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "original_punch_time": self.original_punch_time.isoformat() if self.original_punch_time else None,
            "modification_reason": self.modification_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def punch_type_display(self) -> str:
        """打刻種別の表示名を取得"""
        display_names = {
            PunchType.IN: "出勤",
            PunchType.OUT: "退勤",
            PunchType.OUTSIDE: "外出",
            PunchType.RETURN: "戻り",
        }
        return display_names.get(self.punch_type, self.punch_type)