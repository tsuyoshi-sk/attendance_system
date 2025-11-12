"""
認証関連のPydanticスキーマ
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic import ValidationInfo
from enum import Enum


class UserRoleEnum(str, Enum):
    """ユーザーロール列挙型"""
    ADMIN = "admin"
    EMPLOYEE = "employee"
    GUEST = "guest"


class UserLogin(BaseModel):
    """ユーザーログインスキーマ"""
    username: str = Field(..., min_length=3, max_length=50, description="ユーザー名")
    password: str = Field(..., min_length=8, description="パスワード")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        # ユーザー名は英数字とアンダースコアのみ
        if not all(c.isalnum() or c == '_' for c in v):
            raise ValueError('ユーザー名は英数字とアンダースコアのみ使用できます')
        return v.lower()


class PasswordChange(BaseModel):
    """パスワード変更スキーマ"""
    current_password: str = Field(..., min_length=8, description="現在のパスワード")
    new_password: str = Field(..., min_length=8, description="新しいパスワード")
    confirm_password: str = Field(..., min_length=8, description="新しいパスワード（確認）")

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        # パスワードの強度チェック
        if not any(c.isupper() for c in v):
            raise ValueError('パスワードには大文字を含める必要があります')
        if not any(c.islower() for c in v):
            raise ValueError('パスワードには小文字を含める必要があります')
        if not any(c.isdigit() for c in v):
            raise ValueError('パスワードには数字を含める必要があります')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('パスワードには記号を含める必要があります')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        new_password = info.data.get('new_password')
        if new_password is not None and v != new_password:
            raise ValueError('パスワードが一致しません')
        return v


class UserResponse(BaseModel):
    """ユーザー情報レスポンススキーマ"""
    id: int
    username: str
    role: UserRoleEnum
    employee_id: Optional[int] = None
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    permissions: List[str] = Field(default_factory=list, description="ユーザー権限リスト")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """トークンレスポンススキーマ"""
    access_token: str = Field(..., description="アクセストークン")
    token_type: str = Field(default="bearer", description="トークンタイプ")
    expires_in: int = Field(..., description="有効期限（秒）")
    user_info: UserResponse = Field(..., description="ユーザー情報")


class TokenPayload(BaseModel):
    """JWTトークンペイロードスキーマ"""
    sub: str  # ユーザーID
    username: str
    role: str
    exp: int  # 有効期限
    iat: int  # 発行時刻
    permissions: List[str] = Field(default_factory=list)
