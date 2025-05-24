"""
勤怠集計モデル

日次・月次の勤怠集計データを管理するデータベースモデル
"""

from datetime import date, datetime, time
from sqlalchemy import Column, Integer, Date, Time, Float, ForeignKey, Boolean, String, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship

from backend.app.database import Base


class DailySummary(Base):
    """日次勤怠集計テーブル"""
    
    __tablename__ = "daily_summaries"
    
    # 主キー
    id = Column(Integer, primary_key=True, index=True)
    
    # 外部キー
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # 対象日
    work_date = Column(Date, nullable=False, index=True)
    
    # 出退勤時刻
    clock_in_time = Column(Time, nullable=True)
    clock_out_time = Column(Time, nullable=True)
    
    # 休憩時間
    break_minutes = Column(Integer, default=0, nullable=False)
    
    # 勤務時間（分）
    work_minutes = Column(Integer, default=0, nullable=False)
    actual_work_minutes = Column(Integer, default=0, nullable=False)  # 休憩を除いた実労働時間
    
    # 残業時間（分）
    overtime_minutes = Column(Integer, default=0, nullable=False)
    late_night_minutes = Column(Integer, default=0, nullable=False)  # 深夜残業
    holiday_work_minutes = Column(Integer, default=0, nullable=False)  # 休日出勤
    
    # 勤怠状況
    is_holiday = Column(Boolean, default=False, nullable=False)
    is_paid_leave = Column(Boolean, default=False, nullable=False)
    is_absent = Column(Boolean, default=False, nullable=False)
    is_late = Column(Boolean, default=False, nullable=False)
    is_early_leave = Column(Boolean, default=False, nullable=False)
    
    # 遅刻・早退時間（分）
    late_minutes = Column(Integer, default=0, nullable=False)
    early_leave_minutes = Column(Integer, default=0, nullable=False)
    
    # 備考
    note = Column(String(500), nullable=True)
    
    # 承認状況
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # リレーション
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="daily_summaries")
    approver = relationship("Employee", foreign_keys=[approved_by])
    
    # ユニーク制約
    __table_args__ = (
        UniqueConstraint("employee_id", "work_date", name="uq_employee_date"),
    )
    
    def __repr__(self) -> str:
        return f"<DailySummary(id={self.id}, employee_id={self.employee_id}, date={self.work_date})>"
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "work_date": self.work_date.isoformat() if self.work_date else None,
            "clock_in_time": self.clock_in_time.isoformat() if self.clock_in_time else None,
            "clock_out_time": self.clock_out_time.isoformat() if self.clock_out_time else None,
            "break_minutes": self.break_minutes,
            "work_minutes": self.work_minutes,
            "actual_work_minutes": self.actual_work_minutes,
            "overtime_minutes": self.overtime_minutes,
            "late_night_minutes": self.late_night_minutes,
            "holiday_work_minutes": self.holiday_work_minutes,
            "is_holiday": self.is_holiday,
            "is_paid_leave": self.is_paid_leave,
            "is_absent": self.is_absent,
            "is_late": self.is_late,
            "is_early_leave": self.is_early_leave,
            "late_minutes": self.late_minutes,
            "early_leave_minutes": self.early_leave_minutes,
            "note": self.note,
            "is_approved": self.is_approved,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }


class MonthlySummary(Base):
    """月次勤怠集計テーブル"""
    
    __tablename__ = "monthly_summaries"
    
    # 主キー
    id = Column(Integer, primary_key=True, index=True)
    
    # 外部キー
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # 対象年月
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    
    # 勤務日数
    work_days = Column(Integer, default=0, nullable=False)
    actual_work_days = Column(Integer, default=0, nullable=False)  # 実出勤日数
    
    # 休暇日数
    paid_leave_days = Column(Float, default=0, nullable=False)
    absent_days = Column(Integer, default=0, nullable=False)
    holiday_work_days = Column(Integer, default=0, nullable=False)
    
    # 遅刻・早退回数
    late_count = Column(Integer, default=0, nullable=False)
    early_leave_count = Column(Integer, default=0, nullable=False)
    
    # 勤務時間（分）
    total_work_minutes = Column(Integer, default=0, nullable=False)
    total_actual_work_minutes = Column(Integer, default=0, nullable=False)
    
    # 残業時間（分）
    total_overtime_minutes = Column(Integer, default=0, nullable=False)
    total_late_night_minutes = Column(Integer, default=0, nullable=False)
    total_holiday_work_minutes = Column(Integer, default=0, nullable=False)
    
    # 休憩時間（分）
    total_break_minutes = Column(Integer, default=0, nullable=False)
    
    # 月次丸め後の時間（分）
    rounded_work_minutes = Column(Integer, default=0, nullable=False)
    rounded_overtime_minutes = Column(Integer, default=0, nullable=False)
    
    # 承認状況
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # 締め状況
    is_closed = Column(Boolean, default=False, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    
    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # リレーション
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="monthly_summaries")
    approver = relationship("Employee", foreign_keys=[approved_by])
    
    # ユニーク制約
    __table_args__ = (
        UniqueConstraint("employee_id", "year", "month", name="uq_employee_year_month"),
    )
    
    def __repr__(self) -> str:
        return f"<MonthlySummary(id={self.id}, employee_id={self.employee_id}, year={self.year}, month={self.month})>"
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "year": self.year,
            "month": self.month,
            "work_days": self.work_days,
            "actual_work_days": self.actual_work_days,
            "paid_leave_days": self.paid_leave_days,
            "absent_days": self.absent_days,
            "holiday_work_days": self.holiday_work_days,
            "late_count": self.late_count,
            "early_leave_count": self.early_leave_count,
            "total_work_minutes": self.total_work_minutes,
            "total_actual_work_minutes": self.total_actual_work_minutes,
            "total_overtime_minutes": self.total_overtime_minutes,
            "total_late_night_minutes": self.total_late_night_minutes,
            "total_holiday_work_minutes": self.total_holiday_work_minutes,
            "total_break_minutes": self.total_break_minutes,
            "rounded_work_minutes": self.rounded_work_minutes,
            "rounded_overtime_minutes": self.rounded_overtime_minutes,
            "is_approved": self.is_approved,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "is_closed": self.is_closed,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }