"""
打刻関連のPydanticスキーマ
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationInfo


class PunchTypeEnum(str, Enum):
    """API用打刻種別"""
    IN = "in"
    OUT = "out"
    OUTSIDE = "outside"
    RETURN = "return"


class PunchCreate(BaseModel):
    """打刻作成リクエスト"""
    card_idm: Optional[str] = Field(default=None, description="カードのIDm（任意）")
    card_idm_hash: Optional[str] = Field(default=None, description="ハッシュ化済みカードIDm")
    punch_type: PunchTypeEnum = Field(..., description="打刻種別")
    device_type: Optional[str] = Field(default=None, description="クライアント識別（任意）")
    note: Optional[str] = Field(default=None, description="備考")
    timestamp: Optional[datetime] = Field(default=None, description="打刻タイムスタンプ（ISO8601）")

    @field_validator("punch_type", mode="before")
    @classmethod
    def normalize_punch_type(cls, value):
        if isinstance(value, str):
            return value.lower()
        return value
    
    @field_validator("card_idm")
    @classmethod
    def validate_card_idm(cls, value: Optional[str], info: ValidationInfo) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("card_idmは必須です")
        allowed_lengths = {16, 32, 64}
        if len(normalized) not in allowed_lengths or not all(c in "0123456789abcdefABCDEF" for c in normalized):
            raise ValueError("card_idmは16進数で指定してください")
        return normalized.lower()
