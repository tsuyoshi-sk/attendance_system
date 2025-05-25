"""
レポート関連のPydanticスキーマ

日次・月次レポート、賃金計算、分析用のスキーマを定義
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ReportType(str, Enum):
    """レポート種別"""
    DAILY = "daily"
    MONTHLY = "monthly"
    PAYROLL = "payroll"


class PunchRecordResponse(BaseModel):
    """打刻記録レスポンス"""
    punch_type: str
    timestamp: datetime
    processed: bool
    
    class Config:
        from_attributes = True


class DailySummaryData(BaseModel):
    """日次集計データ"""
    work_minutes: int = Field(description="労働時間（分）")
    overtime_minutes: int = Field(description="残業時間（分）")
    night_minutes: int = Field(description="深夜労働時間（分）")
    outside_minutes: int = Field(description="外出時間（分）")
    break_minutes: int = Field(description="休憩時間（分）")
    actual_work_minutes: int = Field(description="実労働時間（分）")


class DailyCalculations(BaseModel):
    """日次賃金計算"""
    regular_hours: float = Field(description="通常労働時間")
    overtime_hours: float = Field(description="残業時間")
    night_hours: float = Field(description="深夜労働時間")
    basic_wage: float = Field(description="基本給")
    overtime_wage: float = Field(description="残業代")
    night_wage: float = Field(description="深夜手当")
    total_wage: float = Field(description="合計賃金")


class DailyReportRequest(BaseModel):
    """日次レポートリクエスト"""
    target_date: date
    employee_ids: Optional[List[str]] = None


class DailyReportResponse(BaseModel):
    """日次レポートレスポンス"""
    date: date
    employee_id: str
    employee_name: str
    punch_records: List[PunchRecordResponse]
    summary: DailySummaryData
    calculations: DailyCalculations
    
    class Config:
        from_attributes = True


class MonthlySummaryData(BaseModel):
    """月次集計データ"""
    work_days: int = Field(description="出勤日数")
    total_work_hours: float = Field(description="総労働時間")
    regular_hours: float = Field(description="通常労働時間")
    overtime_hours: float = Field(description="残業時間")
    night_hours: float = Field(description="深夜労働時間")
    holiday_hours: float = Field(description="休日労働時間")


class MonthlyWageCalculation(BaseModel):
    """月次賃金計算"""
    basic_wage: float = Field(description="基本給")
    overtime_wage: float = Field(description="残業代")
    night_wage: float = Field(description="深夜手当")
    holiday_wage: float = Field(description="休日手当")
    total_wage: float = Field(description="総支給額")
    deductions: float = Field(description="控除額")
    net_wage: float = Field(description="手取り額")


class MonthlyReportRequest(BaseModel):
    """月次レポートリクエスト"""
    year: int
    month: int
    employee_ids: Optional[List[str]] = None


class MonthlyReportResponse(BaseModel):
    """月次レポートレスポンス"""
    year: int
    month: int
    employee_id: str
    employee_name: str
    monthly_summary: MonthlySummaryData
    wage_calculation: MonthlyWageCalculation
    daily_breakdown: List[DailyReportResponse]
    
    class Config:
        from_attributes = True


class ExportRequest(BaseModel):
    """エクスポートリクエスト"""
    report_type: ReportType
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    year: Optional[int] = None
    month: Optional[int] = None
    employee_ids: Optional[List[str]] = None
    format: str = Field(default="csv", pattern="^(csv|excel|pdf)$")


class DashboardSummary(BaseModel):
    """ダッシュボード集計"""
    total_employees: int
    present_employees: int
    total_work_hours: float
    average_work_hours: float


class DashboardAlert(BaseModel):
    """ダッシュボードアラート"""
    type: str
    employee_id: str
    message: str
    severity: str = Field(default="info", pattern="^(info|warning|error)$")


class DashboardResponse(BaseModel):
    """ダッシュボードレスポンス"""
    today_summary: DashboardSummary
    this_month: Dict[str, Any]
    alerts: List[DashboardAlert]


class AttendanceStats(BaseModel):
    """勤怠統計"""
    average_work_hours: float
    max_work_hours: float
    min_work_hours: float
    standard_deviation: float


class OvertimeAnalysis(BaseModel):
    """残業分析"""
    total_overtime_hours: float
    average_overtime_per_employee: float
    overtime_distribution: Dict[str, int]


class TrendAnalysis(BaseModel):
    """トレンド分析"""
    work_hours_trend: str = Field(pattern="^(increasing|decreasing|stable)$")
    overtime_trend: str = Field(pattern="^(increasing|decreasing|stable)$")
    attendance_trend: str = Field(pattern="^(improving|declining|stable)$")


class StatisticsResponse(BaseModel):
    """統計レスポンス"""
    attendance_stats: AttendanceStats
    overtime_analysis: OvertimeAnalysis
    trend_analysis: TrendAnalysis


class ChartDataset(BaseModel):
    """チャートデータセット"""
    label: str
    data: List[float]


class ChartDataResponse(BaseModel):
    """チャートデータレスポンス"""
    chart_type: str = Field(pattern="^(line|bar|pie)$")
    data: Dict[str, Any]