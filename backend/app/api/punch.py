"""
打刻APIエンドポイント

打刻関連のAPIエンドポイントを定義します。
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app.database import get_db
from backend.app.models import Employee, PunchRecord, PunchType
from backend.app.services.punch_service import PunchService, PunchServiceError
from backend.app.schemas.punch import PunchCreate
from backend.app.utils import offline_queue_manager

ERROR_STATUS_MAP = {
    "EMPLOYEE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "DUPLICATE_PUNCH": status.HTTP_409_CONFLICT,
    "DAILY_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
    "INVALID_SEQUENCE": status.HTTP_400_BAD_REQUEST,
    "INVALID_REQUEST": status.HTTP_400_BAD_REQUEST,
}

logger = logging.getLogger(__name__)

# レート制限の設定
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.get("/health")
async def punch_health_check():
    """打刻API ヘルスチェック"""
    return {"status": "healthy", "module": "punch"}


@router.post("/", response_model=Dict[str, Any])
@limiter.limit("30/minute")  # 1分間に30回まで（テスト考慮）
async def create_punch(
    request: Request,
    payload: PunchCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    打刻を記録する
    
    Args:
        payload: 打刻リクエスト
        db: データベースセッション
    
    Returns:
        Dict[str, Any]: 打刻結果
    
    Raises:
        HTTPException: エラー発生時
    """
    try:
        service = PunchService(db)

        result = await service.create_punch(
            card_idm=payload.card_idm,
            card_idm_hash=payload.card_idm_hash,
            punch_type=PunchType(payload.punch_type.value),
            device_type=payload.device_type or "pasori",
            note=payload.note,
            timestamp=payload.timestamp
        )
        return result
    except PunchServiceError as e:
        logger.warning(f"Punch service error: {e.code} - {e}")
        status_code = ERROR_STATUS_MAP.get(e.code, status.HTTP_400_BAD_REQUEST)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "error": e.code,
                    "message": str(e)
                }
            }
        )
    except ConnectionError as e:
        logger.error(f"Punch creation failed due to network error: {e}")
        punch_time = payload.timestamp or datetime.now()
        offline_queue_manager.add_punch({
            "employee_id": None,
            "punch_type": payload.punch_type.value,
            "card_idm": payload.card_idm or payload.card_idm_hash,
            "timestamp": punch_time.isoformat(),
            "device_type": payload.device_type or "pasori",
            "note": payload.note,
        })
        return {
            "success": True,
            "message": "オフラインモードで打刻を受け付けました。ネットワーク復旧後に自動同期します。",
            "punch_record": {
                "punch_type": payload.punch_type.value,
                "timestamp": punch_time.isoformat(),
                "is_offline": True
            }
        }
    except ValueError as e:
        # ValueErrorは通常、バリデーションエラーなので詳細を返す
        logger.warning(f"Validation error during punch creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # 予期しないエラーはログに詳細を記録し、ユーザーには汎用メッセージ
        logger.error(f"Unexpected error during punch creation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="打刻処理中にエラーが発生しました。管理者にお問い合わせください。"
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
        status_response = await service.get_employee_status(employee_id)
        return status_response
    except ValueError as e:
        logger.warning(f"Validation error in get_punch_status: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_punch_status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="状況取得中にエラーが発生しました。管理者にお問い合わせください。"
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
        logger.warning(f"Validation error in get_punch_history: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_punch_history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="履歴取得中にエラーが発生しました。管理者にお問い合わせください。"
        )


@router.get("/offline/status", response_model=Dict[str, Any])
async def get_offline_status() -> Dict[str, Any]:
    """オフラインキューの状態を取得"""
    stats = offline_queue_manager.get_stats()
    status_text = "ready" if "error" not in stats else "error"
    return {
        "status": status_text,
        "statistics": stats,
        "timestamp": datetime.utcnow().isoformat()
    }
