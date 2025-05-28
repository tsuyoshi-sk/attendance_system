"""
従業員関連のPydanticスキーマ
"""

from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict
from enum import Enum


class WageTypeEnum(str, Enum):
    """賃金タイプ列挙型"""

    HOURLY = "hourly"
    MONTHLY = "monthly"


class EmployeeBase(BaseModel):
    """従業員基本スキーマ"""

    employee_code: str = Field(..., min_length=1, max_length=20, description="従業員コード")
    name: str = Field(..., min_length=1, max_length=100, description="氏名")
    name_kana: Optional[str] = Field(None, max_length=100, description="氏名（カナ）")
    email: Optional[EmailStr] = Field(None, description="メールアドレス")
    department: Optional[str] = Field(None, max_length=100, description="部署")
    position: Optional[str] = Field(None, max_length=100, description="役職")
    employment_type: str = Field("正社員", max_length=20, description="雇用形態")
    hire_date: Optional[date] = Field(None, description="入社日")
    wage_type: WageTypeEnum = Field(WageTypeEnum.MONTHLY, description="賃金タイプ")
    hourly_rate: Optional[Decimal] = Field(None, ge=0, description="時給")
    monthly_salary: Optional[int] = Field(None, ge=0, description="月給")
    is_active: bool = Field(True, description="有効フラグ")

    @validator("employee_code")
    def validate_employee_code(cls, v):
        if not v.strip():
            raise ValueError("従業員コードは必須です")
        # 英数字とハイフンのみ許可
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("従業員コードは英数字とハイフンのみ使用できます")
        return v.upper()

    @validator("hourly_rate", "monthly_salary")
    def validate_wage(cls, v, values):
        if "wage_type" in values:
            if (
                values["wage_type"] == WageTypeEnum.HOURLY
                and values.get("hourly_rate") is None
            ):
                raise ValueError("時給制の場合、時給は必須です")
            elif (
                values["wage_type"] == WageTypeEnum.MONTHLY
                and values.get("monthly_salary") is None
            ):
                raise ValueError("月給制の場合、月給は必須です")
        return v

    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(EmployeeBase):
    """従業員作成スキーマ"""

    pass


class EmployeeUpdate(BaseModel):
    """従業員更新スキーマ"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    name_kana: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    employment_type: Optional[str] = Field(None, max_length=20)
    hire_date: Optional[date] = None
    wage_type: Optional[WageTypeEnum] = None
    hourly_rate: Optional[Decimal] = Field(None, ge=0)
    monthly_salary: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeResponse(EmployeeBase):
    """従業員レスポンススキーマ"""

    id: int
    has_card: bool = Field(False, description="カード登録済みフラグ")
    card_count: int = Field(0, description="登録カード数")
    has_user_account: bool = Field(False, description="ユーザーアカウント作成済みフラグ")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeListResponse(BaseModel):
    """従業員一覧レスポンススキーマ"""

    success: bool = True
    data: List[EmployeeResponse]
    total: int
    page: int = 1
    page_size: int = 50
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeDetailResponse(EmployeeResponse):
    """従業員詳細レスポンススキーマ"""

    user_info: Optional[dict] = None  # ユーザー情報（権限がある場合のみ）
    recent_punches: Optional[List[dict]] = None  # 最近の打刻記録
    monthly_summary: Optional[dict] = None  # 今月の勤怠サマリー

    model_config = ConfigDict(from_attributes=True)
