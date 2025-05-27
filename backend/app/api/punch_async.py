"""
打刻APIエンドポイント（非同期版）

非同期データベース操作を使用した打刻関連のAPIエンドポイントを定義します。
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, validator

from backend.app.database_async import get_async_db
from backend.app.models import PunchType
from backend.app.services.punch_service_async import AsyncPunchService

logger = logging.getLogger(__name__)

router = APIRouter()


class PunchRequest(BaseModel):
    """打刻リクエストモデル"""
    card_idm: str
    punch_type: str
    device_type: str = "pasori"
    note: Optional[str] = None
    
    @validator('punch_type')
    def validate_punch_type(cls, v):
        try:
            PunchType(v)
        except ValueError:
            raise ValueError(f"Invalid punch_type: {v}. Valid values are: {[e.value for e in PunchType]}")
        return v


class PunchResponse(BaseModel):
    """打刻レスポンスモデル"""
    success: bool
    message: str
    punch: Dict[str, Any]
    employee: Dict[str, Any]


@router.get("/health")
async def punch_health_check():
    """打刻API ヘルスチェック"""
    return {"status": "healthy", "module": "punch_async", "timestamp": datetime.now().isoformat()}


@router.post("/", response_model=PunchResponse)
async def create_punch(
    request: PunchRequest,
    db: AsyncSession = Depends(get_async_db)
) -> PunchResponse:
    """
    打刻を記録する（非同期版）
    
    Args:
        request: 打刻リクエスト
        db: 非同期データベースセッション
    
    Returns:
        PunchResponse: 打刻結果
    
    Raises:
        HTTPException: エラー発生時
    """
    try:
        logger.debug(f"Received punch request: {request.dict()}")
        
        # PunchTypeに変換
        punch_type_enum = PunchType(request.punch_type)
        
        service = AsyncPunchService(db)
        result = await service.create_punch(
            card_idm=request.card_idm,
            punch_type=punch_type_enum,
            device_type=request.device_type,
            note=request.note
        )
        
        logger.info(f"Punch created successfully: employee_id={result['employee']['id']}")
        return PunchResponse(**result)
        
    except ValueError as e:
        logger.error(f"ValueError during punch creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during punch creation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"打刻処理中にエラーが発生しました: {str(e)}"
        )


@router.get("/status/{employee_id}")
async def get_punch_status(
    employee_id: int,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    従業員の現在の打刻状況を取得（非同期版）
    
    Args:
        employee_id: 従業員ID
        db: 非同期データベースセッション
    
    Returns:
        Dict[str, Any]: 打刻状況
    """
    try:
        service = AsyncPunchService(db)
        result = await service.get_punch_status(employee_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting punch status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"状況取得中にエラーが発生しました: {str(e)}"
        )


@router.get("/history")
async def get_punch_history(
    employee_id: Optional[int] = Query(None, description="従業員ID"),
    start_date: Optional[date] = Query(None, description="開始日"),
    end_date: Optional[date] = Query(None, description="終了日"),
    limit: int = Query(100, le=1000, description="取得件数上限"),
    db: AsyncSession = Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """
    打刻履歴を取得（非同期版）
    
    Args:
        employee_id: 従業員ID（オプション）
        start_date: 開始日（オプション）
        end_date: 終了日（オプション）
        limit: 取得件数上限
        db: 非同期データベースセッション
    
    Returns:
        List[Dict[str, Any]]: 打刻履歴
    """
    try:
        service = AsyncPunchService(db)
        result = await service.get_punch_history(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error getting punch history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"履歴取得中にエラーが発生しました: {str(e)}"
        )


@router.post("/batch")
async def create_batch_punches(
    punches: List[PunchRequest],
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    複数の打刻を一括処理（非同期版）
    
    Args:
        punches: 打刻リクエストのリスト
        db: 非同期データベースセッション
    
    Returns:
        Dict[str, Any]: バッチ処理結果
    """
    if len(punches) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="一度に処理できる打刻は100件までです"
        )
    
    results = []
    errors = []
    
    service = AsyncPunchService(db)
    
    for i, punch_request in enumerate(punches):
        try:
            punch_type_enum = PunchType(punch_request.punch_type)
            result = await service.create_punch(
                card_idm=punch_request.card_idm,
                punch_type=punch_type_enum,
                device_type=punch_request.device_type,
                note=punch_request.note
            )
            results.append(result)
        except Exception as e:
            errors.append({
                "index": i,
                "request": punch_request.dict(),
                "error": str(e)
            })
            logger.error(f"Error in batch punch {i}: {e}")
    
    return {
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
        "total": len(punches)
    }