"""
管理APIエンドポイント

従業員管理、レポート生成などの管理機能のAPIエンドポイントを定義します。
"""

from datetime import date
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from backend.app.database import get_db
from backend.app.models import Employee


router = APIRouter()


class EmployeeCreate(BaseModel):
    """従業員作成用スキーマ"""
    employee_code: str
    name: str
    name_kana: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    position: Optional[str] = None
    employment_type: str = "正社員"


class EmployeeUpdate(BaseModel):
    """従業員更新用スキーマ"""
    name: Optional[str] = None
    name_kana: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    position: Optional[str] = None
    employment_type: Optional[str] = None
    is_active: Optional[bool] = None


class CardRegister(BaseModel):
    """カード登録用スキーマ"""
    card_idm: str


@router.get("/employees", response_model=List[Dict[str, Any]])
async def get_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    従業員一覧を取得
    
    Args:
        skip: スキップ件数
        limit: 取得件数上限
        is_active: アクティブフィルター
        department: 部署フィルター
        db: データベースセッション
    
    Returns:
        List[Dict[str, Any]]: 従業員一覧
    """
    query = db.query(Employee)
    
    if is_active is not None:
        query = query.filter(Employee.is_active == is_active)
    
    if department:
        query = query.filter(Employee.department == department)
    
    employees = query.offset(skip).limit(limit).all()
    return [emp.to_dict() for emp in employees]


@router.get("/employees/{employee_id}", response_model=Dict[str, Any])
async def get_employee(
    employee_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    従業員詳細を取得
    
    Args:
        employee_id: 従業員ID
        db: データベースセッション
    
    Returns:
        Dict[str, Any]: 従業員情報
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"従業員ID {employee_id} が見つかりません"
        )
    return employee.to_dict()


@router.post("/employees", response_model=Dict[str, Any])
async def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    従業員を新規作成
    
    Args:
        employee_data: 従業員データ
        db: データベースセッション
    
    Returns:
        Dict[str, Any]: 作成された従業員情報
    """
    # 従業員コードの重複チェック
    existing = db.query(Employee).filter(
        Employee.employee_code == employee_data.employee_code
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"従業員コード {employee_data.employee_code} は既に使用されています"
        )
    
    # メールアドレスの重複チェック
    if employee_data.email:
        existing_email = db.query(Employee).filter(
            Employee.email == employee_data.email
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"メールアドレス {employee_data.email} は既に使用されています"
            )
    
    # 従業員作成
    employee = Employee(**employee_data.dict())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    
    return employee.to_dict()


@router.put("/employees/{employee_id}", response_model=Dict[str, Any])
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    従業員情報を更新
    
    Args:
        employee_id: 従業員ID
        employee_data: 更新データ
        db: データベースセッション
    
    Returns:
        Dict[str, Any]: 更新された従業員情報
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"従業員ID {employee_id} が見つかりません"
        )
    
    # 更新データの適用
    update_data = employee_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    db.commit()
    db.refresh(employee)
    
    return employee.to_dict()


@router.post("/employees/{employee_id}/card", response_model=Dict[str, Any])
async def register_card(
    employee_id: int,
    card_data: CardRegister,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    従業員にカードを登録
    
    Args:
        employee_id: 従業員ID
        card_data: カードデータ
        db: データベースセッション
    
    Returns:
        Dict[str, Any]: 更新結果
    """
    import hashlib
    from config.config import config
    
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"従業員ID {employee_id} が見つかりません"
        )
    
    # IDmのハッシュ化
    idm_hash = hashlib.sha256(
        f"{card_data.card_idm}{config.IDM_HASH_SECRET}".encode()
    ).hexdigest()
    
    # 既存のカード登録チェック
    existing = db.query(Employee).filter(
        Employee.card_idm_hash == idm_hash,
        Employee.id != employee_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このカードは既に他の従業員に登録されています"
        )
    
    # カード登録
    employee.card_idm_hash = idm_hash
    db.commit()
    db.refresh(employee)
    
    return {
        "message": "カードの登録が完了しました",
        "employee": employee.to_dict()
    }


@router.delete("/employees/{employee_id}/card", response_model=Dict[str, Any])
async def unregister_card(
    employee_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    従業員のカード登録を解除
    
    Args:
        employee_id: 従業員ID
        db: データベースセッション
    
    Returns:
        Dict[str, Any]: 更新結果
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"従業員ID {employee_id} が見つかりません"
        )
    
    if not employee.card_idm_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この従業員にはカードが登録されていません"
        )
    
    # カード登録解除
    employee.card_idm_hash = None
    db.commit()
    db.refresh(employee)
    
    return {
        "message": "カード登録を解除しました",
        "employee": employee.to_dict()
    }