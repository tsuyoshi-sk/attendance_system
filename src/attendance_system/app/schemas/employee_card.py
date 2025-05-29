"""
従業員カード関連のPydanticスキーマ
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator, ConfigDict


class CardCreate(BaseModel):
    """カード作成スキーマ"""

    card_idm_hash: str = Field(
        ..., min_length=64, max_length=64, description="カードIDmのSHA256ハッシュ値"
    )
    card_nickname: Optional[str] = Field(None, max_length=50, description="カードのニックネーム")
    issued_date: Optional[date] = Field(None, description="発行日")

    @validator("card_idm_hash")
    def validate_hash(cls, v):
        # SHA256ハッシュの形式チェック（64文字の16進数）
        if len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("カードIDmは正しくハッシュ化された値である必要があります")
        return v.lower()

    model_config = ConfigDict(from_attributes=True)


class CardResponse(BaseModel):
    """カード情報レスポンススキーマ"""

    id: int
    employee_id: int
    card_nickname: Optional[str] = None
    issued_date: Optional[date] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CardListResponse(BaseModel):
    """カード一覧レスポンススキーマ"""

    success: bool = True
    data: List[CardResponse]
    total: int
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
