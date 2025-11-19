"""
打刻APIエンドポイント

打刻関連のAPIエンドポイントを定義します。
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Employee, PunchRecord, PunchType
from backend.app.services.punch_service import PunchService, PunchServiceError
from backend.app.schemas.punch import PunchCreate
from backend.app.utils import offline_queue_manager
from backend.app.utils.security import CryptoUtils
from backend.app.security.ratelimit import limiter

ERROR_STATUS_MAP = {
    "EMPLOYEE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "DUPLICATE_PUNCH": status.HTTP_409_CONFLICT,
    "DAILY_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
    "INVALID_SEQUENCE": status.HTTP_400_BAD_REQUEST,
    "INVALID_REQUEST": status.HTTP_400_BAD_REQUEST,
}

logger = logging.getLogger(__name__)

router = APIRouter()


def _prepare_card_identifiers(
    card_idm: Optional[str],
    card_idm_hash: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    カード識別子を正規化し、必要に応じてハッシュを導出
    """
    normalized_idm = card_idm.lower() if card_idm else None
    normalized_hash = card_idm_hash.lower() if card_idm_hash else None

    if normalized_idm and not normalized_hash and len(normalized_idm) in (16, 32):
        normalized_hash = CryptoUtils.hash_idm(normalized_idm)

    return normalized_idm, normalized_hash


@router.get("/health")
async def punch_health_check():
    """打刻API ヘルスチェック"""
    return {"status": "healthy", "module": "punch"}


@router.post("/", response_model=Dict[str, Any])
@router.post("", response_model=Dict[str, Any])
@limiter.limit("10/minute")
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
        card_idm, card_idm_hash = _prepare_card_identifiers(
            payload.card_idm,
            payload.card_idm_hash,
        )

        # 同期サービスメソッドを非同期コンテキストで実行
        result = await run_in_threadpool(
            service.create_punch,
            card_idm=card_idm,
            punch_type=PunchType(payload.punch_type.value),
            device_type=payload.device_type or "pasori",
            note=payload.note,
            card_idm_hash=card_idm_hash,
            timestamp=payload.timestamp
        )
        return result
    except PunchServiceError as e:
        logger.warning("Punch service error: %s", e.code)
        status_code = ERROR_STATUS_MAP.get(e.code, status.HTTP_400_BAD_REQUEST)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "error": e.code,
                    "message": str(e) or "打刻処理でエラーが発生しました。入力内容を確認してください。"
                }
            }
        )
    except ConnectionError as e:
        logger.error("Punch creation failed due to network error", exc_info=True)
        punch_time = payload.timestamp or datetime.now()
        offline_queue_manager.add_punch({
            "employee_id": None,
            "punch_type": payload.punch_type.value,
            "card_idm": card_idm or card_idm_hash,
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
    except ValueError:
        logger.error("Validation error during punch creation", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="打刻リクエストを処理できませんでした。入力値を確認してください。"
        )
    except Exception:
        logger.error("Unexpected error during punch creation", exc_info=True)
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
        status_response = await run_in_threadpool(
            service.get_employee_status,
            employee_id
        )
        return status_response
    except ValueError:
        logger.error("Employee not found while fetching status", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定した従業員の打刻情報が見つかりません。"
        )
    except Exception:
        logger.error("Unexpected error in get_punch_status", exc_info=True)
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
        history = await run_in_threadpool(
            service.get_punch_history,
            employee_id,
            date,
            limit
        )
        return history
    except ValueError:
        logger.error("Validation error in get_punch_history", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="打刻履歴を取得できませんでした。入力パラメータを確認してください。"
        )
    except Exception:
        logger.error("Unexpected error in get_punch_history", exc_info=True)
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
