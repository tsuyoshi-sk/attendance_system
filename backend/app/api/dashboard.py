"""
API router for Dashboard
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_active_user
from backend.app.database_async import get_async_db
from backend.app.schemas.dashboard import DashboardSummary
from backend.app.services.dashboard_service import DashboardService
from backend.app.models import User

router = APIRouter()

@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get Dashboard Summary",
    description="Retrieves a summary of attendance data for the dashboard.",
)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> DashboardSummary:
    """
    Retrieves a summary of attendance data for the dashboard.
    - Requires authentication.
    """
    try:
        service = DashboardService(db)
        summary_data = await service.get_summary()
        return DashboardSummary(**summary_data)
    except Exception as e:
        # In a real app, you'd have more specific error handling
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
