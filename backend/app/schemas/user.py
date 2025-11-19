"""
Pydantic schemas for User
"""
from pydantic import BaseModel
from typing import Optional

class UserResponse(BaseModel):
    """Schema for user's own information."""
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool
    employee_id: Optional[int] = None
    name: Optional[str] = None
    employee_code: Optional[str] = None
    department_name: Optional[str] = None

    class Config:
        from_attributes = True
