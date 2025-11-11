"""
打刻関連のPydanticスキーマ
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PunchTypeEnum(str, Enum):
    """API用打刻種別"""
    IN = "in"
    OUT = "out"
    OUTSIDE = "outside"
    RETURN = "return"


class PunchCreate(BaseModel):
    """打刻作成リクエスト"""
    card_idm: Optional[str] = Field(default=None, description="カードのIDm（任意）")
    punch_type: PunchTypeEnum = Field(..., description="打刻種別")
    device_type: Optional[str] = Field(default=None, description="クライアント識別（任意）")
    note: Optional[str] = Field(default=None, description="備考")
