"""
Dashboard Service

ダッシュボード表示に必要なサマリーデータを集計するサービス。
"""
import logging
from datetime import datetime, date, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from backend.app.models import Employee, PunchRecord, DailySummary, Department, PunchType

logger = logging.getLogger(__name__)

class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self) -> dict:
        today = date.today()
        
        # (1) 従業員数の基本サマリー
        total_employees_stmt = select(func.count(Employee.id)).where(Employee.is_active == True)
        total_employees = (await self.db.execute(total_employees_stmt)).scalar_one()

        # (2) 勤務状況のサマリー
        # 最新の打刻記録を取得
        latest_punches_subquery = select(
            PunchRecord.employee_id,
            func.max(PunchRecord.punch_time).label('max_punch_time')
        ).where(
            func.date(PunchRecord.punch_time) == today
        ).group_by(PunchRecord.employee_id).subquery()

        latest_punches_stmt = select(PunchRecord).join(
            latest_punches_subquery,
            and_(
                PunchRecord.employee_id == latest_punches_subquery.c.employee_id,
                PunchRecord.punch_time == latest_punches_subquery.c.max_punch_time
            )
        )
        
        latest_punches = (await self.db.execute(latest_punches_stmt)).scalars().all()

        working_count = 0
        on_break_count = 0
        
        for p in latest_punches:
            if p.punch_type in (PunchType.IN.value, PunchType.RETURN.value):
                working_count += 1
            elif p.punch_type == PunchType.OUTSIDE.value:
                on_break_count += 1
        
        off_count = total_employees - working_count - on_break_count

        # (3) 本日の勤怠統計
        daily_summary_stmt = select(
            func.sum(func.cast(DailySummary.is_late, Integer)).label("late_count"),
            func.sum(func.cast(DailySummary.is_early_leave, Integer)).label("early_leave_count"),
            func.sum(func.cast(DailySummary.is_absent, Integer)).label("absence_count")
        ).where(DailySummary.work_date == today)
        
        daily_stats = (await self.db.execute(daily_summary_stmt)).first()
        
        # (4) 欠勤疑い
        # DailySummaryがまだ作られていない可能性を考慮
        punched_employees_stmt = select(func.distinct(PunchRecord.employee_id)).where(func.date(PunchRecord.punch_time) == today)
        punched_employee_ids = (await self.db.execute(punched_employees_stmt)).scalars().all()
        
        all_active_employees_stmt = select(Employee.id).where(Employee.is_active == True)
        all_active_employee_ids = (await self.db.execute(all_active_employees_stmt)).scalars().all()
        
        absence_suspicious_count = len(set(all_active_employee_ids) - set(punched_employee_ids))


        # (5) アラート (仮実装)
        alerts = [
            # { "id": "alert-1", "type": "MISSING_PUNCH", "message": "E0003 山田太郎 さんの退勤打刻がありません", "severity": "high" }
        ]
        
        # (6) 部門別残業時間 (仮実装: 今月)
        current_month = today.month
        current_year = today.year
        
        overtime_stmt = select(
            Department.name.label("dept_name"),
            func.sum(DailySummary.overtime_minutes).label("total_overtime")
        ).join(
            Employee, Employee.department_id == Department.id
        ).join(
            DailySummary, DailySummary.employee_id == Employee.id
        ).where(
            and_(
                func.extract('year', DailySummary.work_date) == current_year,
                func.extract('month', DailySummary.work_date) == current_month
            )
        ).group_by(
            Department.name
        ).order_by(
            func.sum(DailySummary.overtime_minutes).desc()
        )
        
        overtime_results = (await self.db.execute(overtime_stmt)).all()
        
        overtime_by_dept = [
            {"deptName": row.dept_name, "overtimeHours": round((row.total_overtime or 0) / 60, 1)}
            for row in overtime_results
        ]

        return {
            "totalEmployees": total_employees,
            "workingCount": working_count,
            "onBreakCount": on_break_count,
            "offCount": off_count,
            "lateCount": daily_stats.late_count or 0,
            "earlyLeaveCount": daily_stats.early_leave_count or 0,
            "absenceSuspiciousCount": absence_suspicious_count,
            "alerts": alerts,
            "overtimeByDept": overtime_by_dept,
        }
