"""
モバイルアプリ用APIエンドポイント

従業員向けモバイルアプリの機能を提供するAPIエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.services.mobile_service import MobileService


router = APIRouter(prefix="/api/v1/mobile", tags=["mobile"])


# リクエスト/レスポンスモデル

class PunchRequest(BaseModel):
    """打刻リクエスト"""
    punch_type: str  # "in", "out", "outside", "return"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    note: Optional[str] = None


@router.get("/me/today")
async def get_today_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    今日の勤怠ステータスを取得

    Returns:
        今日の勤怠状況
    """
    try:
        result = MobileService.get_today_status(db, current_user.id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"今日の勤怠情報の取得に失敗しました: {str(e)}"
        )


@router.post("/me/punch")
async def create_punch(
    request: PunchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    打刻を記録

    Args:
        request: 打刻リクエスト

    Returns:
        打刻結果
    """
    try:
        # 打刻種別のバリデーション
        valid_types = ["in", "out", "outside", "return"]
        if request.punch_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無効な打刻種別です。有効な値: {', '.join(valid_types)}"
            )

        result = MobileService.create_punch(
            db=db,
            user_id=current_user.id,
            punch_type=request.punch_type,
            latitude=request.latitude,
            longitude=request.longitude,
            location_name=request.location_name,
            device_type="mobile",
            note=request.note
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"打刻の記録に失敗しました: {str(e)}"
        )


@router.get("/me/attendance/monthly")
async def get_monthly_summary(
    month: str,  # YYYY-MM形式
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    月次サマリーを取得

    Args:
        month: 対象月（YYYY-MM形式）

    Returns:
        月次サマリー
    """
    try:
        # 月の形式をバリデーション
        if len(month) != 7 or month[4] != "-":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="月の形式が不正です。YYYY-MM形式で指定してください"
            )

        result = MobileService.get_monthly_summary(db, current_user.id, month)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"月次サマリーの取得に失敗しました: {str(e)}"
        )


@router.get("/me/attendance/daily")
async def get_daily_timeline(
    date: str,  # YYYY-MM-DD形式
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    特定日のタイムラインを取得

    Args:
        date: 対象日（YYYY-MM-DD形式）

    Returns:
        日次タイムライン
    """
    try:
        # 日付の形式をバリデーション
        if len(date) != 10 or date[4] != "-" or date[7] != "-":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="日付の形式が不正です。YYYY-MM-DD形式で指定してください"
            )

        result = MobileService.get_daily_timeline(db, current_user.id, date)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"タイムラインの取得に失敗しました: {str(e)}"
        )


@router.get("/me/profile")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    自分のプロフィール情報を取得

    Returns:
        プロフィール情報
    """
    try:
        if not current_user.employee_id:
            return {
                "username": current_user.username,
                "role": current_user.role,
                "message": "従業員情報が紐付けられていません"
            }

        from backend.app.models.employee import Employee
        employee = db.query(Employee).filter(Employee.id == current_user.employee_id).first()

        if not employee:
            return {
                "username": current_user.username,
                "role": current_user.role,
                "message": "従業員情報が見つかりません"
            }

        return {
            "username": current_user.username,
            "employee_id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "department": employee.department,
            "position": employee.position,
            "role": current_user.role,
            "has_nfc_card": bool(employee.nfc_card_id)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プロフィール情報の取得に失敗しました: {str(e)}"
        )
