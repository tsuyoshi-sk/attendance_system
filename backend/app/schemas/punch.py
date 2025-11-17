"""
打刻関連のPydanticスキーマ
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import ValidationInfo
import re


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
        """card_idmのバリデーション（SQLインジェクション対策含む）"""
        if value is None:
            return value

        # 文字列型チェック
        if not isinstance(value, str):
            raise ValueError("card_idmは文字列である必要があります")

        normalized = value.strip()
        if not normalized:
            raise ValueError("card_idmは必須です")

        # SQLインジェクション対策: 危険な文字を検出
        if re.search(r"['\";\\<>]", normalized):
            raise ValueError("card_idmに不正な文字が含まれています")

        # 16進数のみ許可（厳格化）
        if not re.match(r'^[0-9a-fA-F]+$', normalized):
            raise ValueError("card_idmは16進数のみ指定可能です")

        # 許可される長さ
        allowed_lengths = {16, 32, 64}
        if len(normalized) not in allowed_lengths:
            raise ValueError(f"card_idmの長さは{allowed_lengths}のいずれかである必要があります")

        return normalized.lower()

    @field_validator("card_idm_hash")
    @classmethod
    def validate_card_idm_hash(cls, value: Optional[str]) -> Optional[str]:
        """card_idm_hashのバリデーション（SHA256ハッシュ形式）"""
        if value is None:
            return value

        # 文字列型チェック
        if not isinstance(value, str):
            raise ValueError("card_idm_hashは文字列である必要があります")

        normalized = value.strip()

        # SQLインジェクション対策: 危険な文字を検出
        if re.search(r"['\";\\<>]", normalized):
            raise ValueError("card_idm_hashに不正な文字が含まれています")

        # SHA256ハッシュ: 正確に64文字の16進数
        if not re.match(r'^[0-9a-fA-F]{64}$', normalized):
            raise ValueError("card_idm_hashは64文字の16進数（SHA256ハッシュ）である必要があります")

        return normalized.lower()

    @model_validator(mode='after')
    def check_card_id_or_hash_present(self) -> 'PunchCreate':
        if not self.card_idm and not self.card_idm_hash:
            raise ValueError('card_idm または card_idm_hash のいずれかが必要です')
        return self
