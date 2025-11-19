"""
Pydantic schemas for Reports
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, time
from enum import Enum

class EmployeeInfo(BaseModel):
    id: int
    employeeCode: str
    name: str
    departmentName: Optional[str] = None

class MonthlySummaryDay(BaseModel):
    date: date
    totalWorkMinutes: int
    status: str # "normal", "need_fix", "absence_suspicious", "holiday"

class EmployeeMonthlySummary(BaseModel):
    employee: EmployeeInfo
    month: str
    days: List[MonthlySummaryDay]

class DailyPunch(BaseModel):
    id: int
    type: str
    time: str
    source: str

class EmployeeDailyTimeline(BaseModel):
    employee: EmployeeInfo
    date: date
    punches: List[DailyPunch]
    totalWorkMinutes: int
    needFix: bool

class DailyReportRequest(BaseModel):
    """日次レポートリクエスト"""
    target_date: date
    employee_id: Optional[int] = None

class DailyReportResponse(BaseModel):
    """日次レポートレスポンス"""
    target_date: date
    reports: List[EmployeeDailyTimeline]

class MonthlyReportRequest(BaseModel):
    """月次レポートリクエスト"""
    year: int
    month: int
    employee_id: Optional[int] = None

class MonthlyReportResponse(BaseModel):
    """月次レポートレスポンス"""
    year: int
    month: int
    reports: List[EmployeeMonthlySummary]

class ReportType(str, Enum):
    """レポートタイプ"""
    DAILY = "daily"
    MONTHLY = "monthly"
    CUSTOM = "custom"

class ExportRequest(BaseModel):
    """エクスポートリクエスト"""
    report_type: ReportType
    start_date: date
    end_date: Optional[date] = None
    employee_id: Optional[int] = None
    format: str = "csv"  # csv, xlsx, pdf

class PunchRecordResponse(BaseModel):
    """打刻記録レスポンス"""
    id: int
    employee_id: int
    punch_type: str
    punch_time: str
    source: str

    class Config:
        from_attributes = True

class DailyCalculations(BaseModel):
    """日次計算結果"""
    work_minutes: int
    overtime_minutes: int
    break_minutes: int
    total_minutes: int

class DailySummaryData(BaseModel):
    """日次サマリーデータ"""
    date: date
    employee_id: int
    calculations: DailyCalculations
    punches: List[PunchRecordResponse]

class MonthlyWageCalculation(BaseModel):
    """月次給与計算結果"""
    base_wage: float
    overtime_wage: float
    total_wage: float

class MonthlySummaryData(BaseModel):
    """月次サマリーデータ"""
    year: int
    month: int
    employee_id: int
    total_work_minutes: int
    total_overtime_minutes: int
    wage_calculation: MonthlyWageCalculation
    daily_summaries: List[DailySummaryData]

class DashboardResponse(BaseModel):
    """ダッシュボードレスポンス"""
    total_employees: int
    present_count: int
    absent_count: int
    late_count: int
    recent_punches: List[PunchRecordResponse]

class ChartDataPoint(BaseModel):
    """チャートデータポイント"""
    label: str
    value: float

class ChartDataResponse(BaseModel):
    """チャートデータレスポンス"""
    title: str
    data: List[ChartDataPoint]

class StatisticsResponse(BaseModel):
    """統計レスポンス"""
    period: str
    total_work_hours: float
    average_work_hours: float
    overtime_hours: float
    charts: List[ChartDataResponse]

class DashboardAlert(BaseModel):
    """ダッシュボードアラート"""
    id: str
    type: str
    message: str
    severity: str  # "high", "medium", "low"
    employee_id: Optional[int] = None

class DashboardSummary(BaseModel):
    """ダッシュボードサマリー"""
    total_employees: int
    present_count: int
    absent_count: int
    late_count: int
    on_time_count: int
    alerts: List[DashboardAlert]

class AttendanceStats(BaseModel):
    """勤怠統計"""
    average_work_hours: float
    total_overtime_hours: float
    attendance_rate: float
    punctuality_rate: float

class OvertimeAnalysis(BaseModel):
    """残業分析"""
    department: str
    total_overtime_hours: float
    average_per_employee: float
    trend: str  # "increasing", "decreasing", "stable"

class TrendAnalysis(BaseModel):
    """トレンド分析"""
    period: str
    metric: str
    values: List[float]
    trend: str  # "increasing", "decreasing", "stable"