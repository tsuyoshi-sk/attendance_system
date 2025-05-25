"""
打刻APIエンドポイント

打刻関連のAPIエンドポイントを定義します。
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Employee, PunchRecord, PunchType
from backend.app.services.punch_service import PunchService


router = APIRouter()


@router.get("/health")
async def punch_health_check():
    """打刻API ヘルスチェック"""
    return {"status": "healthy", "module": "punch"}


@router.post("/", response_model=Dict[str, Any])
async def create_punch(
    card_idm: str,
    punch_type: PunchType,
    db: Session = Depends(get_db),
    device_type: Optional[str] = "pasori",
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    打刻を記録する
    
    Args:
        card_idm: カードのIDm（ハッシュ化前）
        punch_type: 打刻種別
        db: データベースセッション
        device_type: デバイス種別
        note: 備考
    
    Returns:
        Dict[str, Any]: 打刻結果
    
    Raises:
        HTTPException: エラー発生時
    """
    try:
        service = PunchService(db)
        result = await service.create_punch(
            card_idm=card_idm,
            punch_type=punch_type,
            device_type=device_type,
            note=note
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
            detail=f"打刻処理中にエラーが発生しました: {str(e)}"
        )


@router.get("/status/{employee_id}", response_model=Dict[str, Any])
async def get_punch_status(
    employee_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    従業員の現在の打刻状況を取得
    
    Args:
        employee_id: 従業員ID
        db: データベースセッション
    
    Returns:
        Dict[str, Any]: 打刻状況
    """
    try:
        service = PunchService(db)
        status = await service.get_employee_status(employee_id)
        return status
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"状況取得中にエラーが発生しました: {str(e)}"
        )


@router.get("/history/{employee_id}", response_model=Dict[str, Any])
async def get_punch_history(
    employee_id: int,
    date: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    従業員の打刻履歴を取得
    
    Args:
        employee_id: 従業員ID
        date: 対象日（YYYY-MM-DD形式）
        limit: 取得件数上限
        db: データベースセッション
    
    Returns:
        Dict[str, Any]: 打刻履歴
    """
    try:
        service = PunchService(db)
        history = await service.get_punch_history(
            employee_id=employee_id,
            date=date,
            limit=limit
        )
        return history
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"履歴取得中にエラーが発生しました: {str(e)}"
        )