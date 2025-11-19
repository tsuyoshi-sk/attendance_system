"""
API router for Employees
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date

from backend.app.auth.dependencies import get_current_active_user, require_employee_access
from backend.app.database_async import get_async_db
from backend.app.schemas.employee import EmployeeWithStatus
from backend.app.schemas.report import EmployeeMonthlySummary, EmployeeDailyTimeline
from backend.app.services.employee_service_async import AsyncEmployeeService
from backend.app.services.report_service_async import AsyncReportService
from backend.app.models import User

router = APIRouter()

@router.get(
    "/",
    response_model=List[EmployeeWithStatus],
    summary="Get Employees with Status",
    description="Retrieves a list of active employees with their current attendance status.",
)
async def get_employees_with_status(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    q: Optional[str] = Query(None, description="Search term for name or employee code"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> List[EmployeeWithStatus]:
    """
    Retrieves a list of active employees with their current attendance status.
    - Requires authentication.
    - Supports search and pagination.
    """
    try:
        service = AsyncEmployeeService(db)
        employees = await service.search_employees_with_status(q=q, offset=offset, limit=limit)
        return employees
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@router.get(
    "/{employee_id}/attendance/monthly",
    response_model=EmployeeMonthlySummary,
    summary="Get Monthly Attendance Summary for an Employee",
    dependencies=[Depends(require_employee_access)],
)
async def get_employee_monthly_summary(
    employee_id: int,
    month: Optional[str] = Query(None, description="Month in YYYY-MM format. Defaults to current month."),
    db: AsyncSession = Depends(get_async_db),
) -> EmployeeMonthlySummary:
    """
    Retrieves the monthly attendance summary for a specific employee.
    """
    try:
        service = AsyncReportService(db)
        summary = await service.get_monthly_summary(employee_id, month)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@router.get(
    "/{employee_id}/attendance/daily",
    response_model=EmployeeDailyTimeline,
    summary="Get Daily Punch Timeline for an Employee",
    dependencies=[Depends(require_employee_access)],
)
async def get_employee_daily_timeline(
    employee_id: int,
    date: str = Query(..., description="Date in YYYY-MM-DD format."),
    db: AsyncSession = Depends(get_async_db),
) -> EmployeeDailyTimeline:
    """
    Retrieves the daily punch timeline for a specific employee.
    """
    try:
        service = AsyncReportService(db)
        timeline = await service.get_daily_timeline(employee_id, date)
        return timeline
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
