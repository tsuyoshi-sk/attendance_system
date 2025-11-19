"""
Pydantic schemas for Dashboard
"""
from pydantic import BaseModel
from typing import List

class Alert(BaseModel):
    id: str
    type: str
    message: str
    severity: str # "high", "medium", "low"

class OvertimeByDept(BaseModel):
    deptName: str
    overtimeHours: float

class DashboardSummary(BaseModel):
    totalEmployees: int
    workingCount: int
    onBreakCount: int
    offCount: int
    lateCount: int
    earlyLeaveCount: int
    absenceSuspiciousCount: int
    alerts: List[Alert]
    overtimeByDept: List[OvertimeByDept]
