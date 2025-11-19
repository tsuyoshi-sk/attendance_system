"""
Async Employee Service
"""
import logging
from datetime import date
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased

from backend.app.models import Employee, PunchRecord, Department, PunchType

logger = logging.getLogger(__name__)

class AsyncEmployeeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_employees_with_status(
        self,
        q: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search for employees and get their latest attendance status.
        """
        # Subquery to get the latest punch record for each employee on the current day
        today = date.today()
        
        latest_punch_subquery = (
            select(
                PunchRecord.employee_id,
                PunchRecord.punch_type,
                func.row_number().over(
                    partition_by=PunchRecord.employee_id,
                    order_by=PunchRecord.punch_time.desc()
                ).label("row_num")
            )
            .where(func.date(PunchRecord.punch_time) == today)
            .subquery()
        )
        
        lp = aliased(latest_punch_subquery)

        # Main query to get employee details and join with the latest punch status
        stmt = (
            select(
                Employee.id,
                Employee.employee_code,
                Employee.name,
                Department.name.label("department_name"),
                lp.c.punch_type
            )
            .select_from(Employee)
            .outerjoin(Department, Employee.department_id == Department.id)
            .outerjoin(
                lp,
                and_(
                    Employee.id == lp.c.employee_id,
                    lp.c.row_num == 1
                )
            )
            .where(Employee.is_active == True)
        )

        # Apply search filter if query is provided
        if q:
            search_term = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Employee.name.ilike(search_term),
                    Employee.employee_code.ilike(search_term)
                )
            )

        stmt = stmt.order_by(Employee.employee_code).limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        rows = result.all()

        # Format the result
        employees_with_status = []
        for row in rows:
            status = "off" # Default to off
            if row.punch_type:
                if row.punch_type in (PunchType.IN.value, PunchType.RETURN.value):
                    status = "working"
                elif row.punch_type == PunchType.OUTSIDE.value:
                    status = "on_break"
            
            employees_with_status.append({
                "id": row.id,
                "employeeCode": row.employee_code,
                "name": row.name,
                "departmentName": row.department_name,
                "status": status,
            })
            
        return employees_with_status
