"""
API router for Users
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_active_user
from backend.app.database_async import get_async_db
from backend.app.schemas.user import UserResponse
from backend.app.models import User

router = APIRouter()

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Retrieves information for the currently authenticated user.",
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
) -> UserResponse:
    """
    Get the current user's profile information.
    """
    # Eagerly load related employee and department data in a single query
    # Note: get_current_active_user already fetches the user, but without relations.
    # To get relations, we need a fresh query with options.
    user_with_relations_stmt = (
        select(User)
        .options(
            selectinload(User.employee).selectinload(Employee.department)
        )
        .where(User.id == current_user.id)
    )
    result = await db.execute(user_with_relations_stmt)
    user_with_relations = result.scalar_one_or_none()

    if not user_with_relations:
        # This should theoretically not happen if get_current_active_user passed
        raise HTTPException(status_code=404, detail="User not found.")

    employee = user_with_relations.employee
    response_data = {
        "id": user_with_relations.id,
        "username": user_with_relations.username,
        "email": user_with_relations.email,
        "is_active": user_with_relations.is_active,
        "is_admin": user_with_relations.role == 'admin', # Assuming role is a string
        "employee_id": employee.id if employee else None,
        "name": employee.name if employee else None,
        "employee_code": employee.employee_code if employee else None,
        "department_name": employee.department.name if employee and employee.department else None,
    }
    
    return UserResponse(**response_data)
