"""
Async Report Service
"""
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models import Employee, PunchRecord, DailySummary, PunchType

logger = logging.getLogger(__name__)

class AsyncReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_monthly_summary(self, employee_id: int, month_str: Optional[str]) -> Dict[str, Any]:
        """
        Get a summary of attendance for a specific employee and month.
        """
        if month_str:
            try:
                year, month = map(int, month_str.split('-'))
            except (ValueError, TypeError):
                raise ValueError("Invalid month format. Use YYYY-MM.")
        else:
            today = date.today()
            year, month = today.year, today.month

        # Get employee info
        employee_stmt = select(Employee).options(selectinload(Employee.department)).where(Employee.id == employee_id)
        employee = (await self.db.execute(employee_stmt)).scalar_one_or_none()
        if not employee:
            raise ValueError("Employee not found")

        # Get daily summaries for the month
        summaries_stmt = select(DailySummary).where(
            and_(
                DailySummary.employee_id == employee_id,
                DailySummary.work_date >= date(year, month, 1),
                DailySummary.work_date < (date(year, month, 1).replace(month=month % 12 + 1, year=year + (month // 12)))
            )
        ).order_by(asc(DailySummary.work_date))
        
        summaries = (await self.db.execute(summaries_stmt)).scalars().all()

        days_data = []
        for summary in summaries:
            status = "normal"
            if summary.is_absent:
                status = "absence"
            elif summary.is_late or summary.is_early_leave:
                status = "need_fix"
            elif summary.is_holiday or summary.is_paid_leave:
                status = "holiday"
            
            days_data.append({
                "date": summary.work_date.isoformat(),
                "totalWorkMinutes": summary.actual_work_minutes,
                "status": status,
            })

        return {
            "employee": {
                "id": employee.id,
                "employeeCode": employee.employee_code,
                "name": employee.name,
                "departmentName": employee.department.name if employee.department else None,
            },
            "month": f"{year}-{month:02d}",
            "days": days_data,
        }

    async def get_daily_timeline(self, employee_id: int, date_str: str) -> Dict[str, Any]:
        """
        Get the punch timeline for a specific employee and day.
        """
        try:
            target_date = date.fromisoformat(date_str)
        except (ValueError, TypeError):
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
        
        # Get employee info
        employee_stmt = select(Employee).where(Employee.id == employee_id)
        employee = (await self.db.execute(employee_stmt)).scalar_one_or_none()
        if not employee:
            raise ValueError("Employee not found")
        
        # Get punches for the day
        punches_stmt = select(PunchRecord).where(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= datetime.combine(target_date, datetime.min.time()),
                PunchRecord.punch_time < datetime.combine(target_date + timedelta(days=1), datetime.min.time())
            )
        ).order_by(asc(PunchRecord.punch_time))
        
        punches = (await self.db.execute(punches_stmt)).scalars().all()

        punches_data = []
        for punch in punches:
            punches_data.append({
                "id": punch.id,
                "type": punch.punch_type,
                "time": punch.punch_time.strftime("%H:%M:%S"),
                "source": punch.device_type or "unknown"
            })
        
        # Calculate total work minutes for the day (simple version)
        summary_stmt = select(DailySummary).where(
            and_(
                DailySummary.employee_id == employee_id,
                DailySummary.work_date == target_date
            )
        ).limit(1)
        summary = (await self.db.execute(summary_stmt)).scalar_one_or_none()

        return {
            "employee": {
                "id": employee.id,
                "employeeCode": employee.employee_code,
                "name": employee.name,
            },
            "date": target_date.isoformat(),
            "punches": punches_data,
            "totalWorkMinutes": summary.actual_work_minutes if summary else 0,
            "needFix": summary.is_late or summary.is_early_leave if summary else False,
        }
