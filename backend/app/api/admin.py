"""
管理APIエンドポイント

従業員管理、カード管理などの管理機能のAPIエンドポイントを定義します。
"""

from datetime import date
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Response, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
import hashlib
import logging

from backend.app.database import get_db
from backend.app.models import Employee, EmployeeCard
from backend.app.schemas import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse,
    CardCreate, CardResponse, CardListResponse
)
from backend.app.services.employee_service import EmployeeService
from backend.app.api.auth import require_permission, get_current_active_user
from backend.app.models import User
#from backend.app.utils.auth_utils import get_current_user_or_bypass, require_permission_or_bypass
from config.config import config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def admin_health_check():
    """管理API ヘルスチェック"""
    return {"status": "healthy", "module": "admin"}


@router.get("/employees", response_model=EmployeeListResponse)
async def get_employees(
    skip: int = Query(0, ge=0, description="スキップ件数"),
    limit: int = Query(50, ge=1, le=100, description="取得件数"),
    is_active: Optional[bool] = Query(None, description="有効フラグフィルター"),
    department: Optional[str] = Query(None, description="部署フィルター"),
    search: Optional[str] = Query(None, description="検索文字列（名前、コード、メール）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> EmployeeListResponse:
    """
    従業員一覧を取得
    
    - **skip**: スキップ件数（ページネーション用）
    - **limit**: 取得件数上限（最大100件）
    - **is_active**: 有効な従業員のみ取得する場合はTrue
    - **department**: 特定部署の従業員のみ取得
    - **search**: 名前、従業員コード、メールアドレスで部分一致検索
    """
    try:
        service = EmployeeService(db)
        employees = await run_in_threadpool(
            service.get_employees,
            skip,
            limit,
            is_active,
            department,
            search
        )
        
        # カード数を追加
        employee_responses = []
        for emp in employees:
            emp_dict = emp.to_dict()
            emp_dict['card_count'] = len([c for c in emp.cards if c.is_active])
            emp_dict['has_user_account'] = bool(emp.user)
            employee_responses.append(EmployeeResponse(**emp_dict))
        
        total = db.query(Employee).count()
        
        return EmployeeListResponse(
            success=True,
            data=employee_responses,
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"従業員一覧取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="従業員一覧の取得に失敗しました。管理者にお問い合わせください。"
        )


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> EmployeeResponse:
    """
    従業員詳細を取得
    
    指定されたIDの従業員情報を取得します。
    """
    service = EmployeeService(db)
    employee = await run_in_threadpool(service.get_employee, employee_id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定した従業員が見つかりません。"
        )
    
    emp_dict = employee.to_dict()
    emp_dict['card_count'] = len([c for c in employee.cards if c.is_active])
    emp_dict['has_user_account'] = bool(employee.user)
    
    return EmployeeResponse(**emp_dict)


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> EmployeeResponse:
    """
    従業員を新規作成
    
    新しい従業員を作成します。従業員コードとメールアドレスは一意である必要があります。
    """
    try:
        service = EmployeeService(db)
        employee = await run_in_threadpool(
            service.create_employee,
            employee_data
        )
        
        emp_dict = employee.to_dict()
        emp_dict['card_count'] = 0
        emp_dict['has_user_account'] = False
        
        return EmployeeResponse(**emp_dict)
        
    except ValueError as exc:
        logger.warning("従業員作成バリデーションエラー: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="従業員を作成できませんでした。入力内容を確認してください。"
        )
    except Exception:
        logger.error("従業員作成エラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="従業員の作成に失敗しました。管理者にお問い合わせください。"
        )


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> EmployeeResponse:
    """
    従業員情報を更新
    
    指定されたIDの従業員情報を更新します。
    """
    try:
        service = EmployeeService(db)
        employee = await run_in_threadpool(
            service.update_employee,
            employee_id,
            employee_data
        )
        
        emp_dict = employee.to_dict()
        emp_dict['card_count'] = len([c for c in employee.cards if c.is_active])
        emp_dict['has_user_account'] = bool(employee.user)
        
        return EmployeeResponse(**emp_dict)
        
    except ValueError as exc:
        logger.warning("従業員更新バリデーションエラー: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="従業員情報を更新できませんでした。入力内容を確認してください。"
        )
    except Exception:
        logger.error("従業員更新エラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="従業員の更新に失敗しました。管理者にお問い合わせください。"
        )


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Response:
    """
    従業員を削除（論理削除）
    
    指定されたIDの従業員を論理削除します。関連するカードとユーザーアカウントも無効化されます。
    """
    try:
        service = EmployeeService(db)
        await run_in_threadpool(service.delete_employee, employee_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except ValueError as exc:
        logger.warning("従業員削除バリデーションエラー: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定した従業員が見つかりません。"
        )
    except Exception:
        logger.error("従業員削除エラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="従業員の削除に失敗しました。管理者にお問い合わせください。"
        )


@router.post("/employees/{employee_id}/cards", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
async def add_employee_card(
    employee_id: int,
    card_data: CardCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> CardResponse:
    """
    従業員にカードを追加
    
    指定された従業員に新しいICカードを登録します。
    カードIDmは事前にSHA256でハッシュ化されている必要があります。
    """
    try:
        service = EmployeeService(db)
        card = await run_in_threadpool(
            service.add_employee_card,
            employee_id,
            card_data
        )
        return CardResponse(**card.to_dict())
        
    except ValueError as exc:
        logger.warning("カード追加バリデーションエラー: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="カードを登録できませんでした。入力内容を確認してください。"
        )
    except Exception:
        logger.error("カード追加エラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="カードの追加に失敗しました。管理者にお問い合わせください。"
        )


@router.get("/employees/{employee_id}/cards", response_model=CardListResponse)
async def get_employee_cards(
    employee_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> CardListResponse:
    """
    従業員のカード一覧を取得
    
    指定された従業員に登録されているカードの一覧を取得します。
    """
    try:
        service = EmployeeService(db)
        
        # 従業員の存在確認
        employee = await run_in_threadpool(service.get_employee, employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定した従業員が見つかりません。"
            )
        
        cards = await run_in_threadpool(service.get_employee_cards, employee_id)
        card_responses = [CardResponse(**card.to_dict()) for card in cards]
        
        return CardListResponse(
            success=True,
            data=card_responses,
            total=len(card_responses)
        )
        
    except HTTPException:
        raise
    except Exception:
        logger.error("カード一覧取得エラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="カード一覧の取得に失敗しました。管理者にお問い合わせください。"
        )


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Response:
    """
    カードを削除（論理削除）
    
    指定されたIDのカードを論理削除します。
    """
    try:
        service = EmployeeService(db)
        await run_in_threadpool(service.delete_card, card_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except ValueError as exc:
        logger.warning("カード削除バリデーションエラー: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定したカードが見つかりません。"
        )
    except Exception:
        logger.error("カード削除エラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="カードの削除に失敗しました。管理者にお問い合わせください。"
        )


# 従来のカード登録エンドポイント（後方互換性のため残す）
@router.post("/employees/{employee_id}/card", response_model=Dict[str, Any], deprecated=True)
async def register_card_legacy(
    employee_id: int,
    card_idm: str = Query(..., description="カードIDm（ハッシュ化前）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    【非推奨】従業員にカードを登録（後方互換性用）
    
    新しいエンドポイント `/employees/{employee_id}/cards` を使用してください。
    """
    # IDmのハッシュ化
    idm_hash = hashlib.sha256(
        f"{card_idm}{config.IDM_HASH_SECRET}".encode()
    ).hexdigest()
    
    card_data = CardCreate(
        card_idm_hash=idm_hash,
        card_nickname="メインカード"
    )
    
    try:
        service = EmployeeService(db)
        card = await run_in_threadpool(
            service.add_employee_card,
            employee_id,
            card_data
        )
        
        return {
            "message": "カードの登録が完了しました",
            "card": card.to_dict()
        }
        
    except ValueError as exc:
        logger.warning("カード登録バリデーションエラー: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="カードの登録に失敗しました。入力内容を確認してください。"
        )
    except Exception:
        logger.error("カード登録エラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="カードの登録に失敗しました。管理者にお問い合わせください。"
        )
