"""
Pydantic schemas for Employee
"""
from pydantic import BaseModel
from typing import Optional, List

class EmployeeBase(BaseModel):
    employeeCode: str
    name: str
    departmentName: Optional[str] = None

class EmployeeCreate(EmployeeBase):
    """従業員作成用スキーマ"""
    pass

class EmployeeUpdate(BaseModel):
    """従業員更新用スキーマ"""
    employeeCode: Optional[str] = None
    name: Optional[str] = None
    departmentName: Optional[str] = None

class EmployeeResponse(EmployeeBase):
    """従業員レスポンス用スキーマ"""
    id: int

    class Config:
        orm_mode = True

class EmployeeWithStatus(EmployeeResponse):
    """ステータス付き従業員スキーマ"""
    status: str # "working", "on_break", "off"

class EmployeeListResponse(BaseModel):
    """従業員一覧レスポンス用スキーマ"""
    employees: List[EmployeeWithStatus]
    total: int

class EmployeeDetailResponse(EmployeeResponse):
    """従業員詳細レスポンス用スキーマ"""
    # 必要に応じて追加フィールドを定義
    pass