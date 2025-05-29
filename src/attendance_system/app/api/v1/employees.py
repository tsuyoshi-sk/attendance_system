"""
従業員API v1

従業員管理のAPIエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ...database import get_db
from ...models.employee import Employee
from ...models.department import Department
from ...auth.dependencies import require_admin, require_manager, get_current_user
from ...schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse

router = APIRouter()


@router.get("/", response_model=List[EmployeeResponse])
async def get_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """
    従業員一覧取得（無制限対応）

    Args:
        skip: スキップ件数
        limit: 取得件数上限
        department_id: 部署IDでフィルター
        is_active: アクティブ状態でフィルター
        search: 名前・従業員コードで検索

    Returns:
        従業員一覧
    """
    query = db.query(Employee)

    # フィルター適用
    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)

    if is_active is not None:
        query = query.filter(Employee.is_active == is_active)

    if search:
        query = query.filter(
            (Employee.name.contains(search))
            | (Employee.employee_code.contains(search))
            | (Employee.email.contains(search))
        )

    # ページネーション
    employees = query.offset(skip).limit(limit).all()

    return [EmployeeResponse.from_orm(emp) for emp in employees]


@router.post("/", response_model=EmployeeResponse)
async def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    従業員作成

    Args:
        employee_data: 従業員作成データ

    Returns:
        作成された従業員情報
    """
    # 従業員コードの重複チェック
    existing = (
        db.query(Employee)
        .filter(Employee.employee_code == employee_data.employee_code)
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="この従業員コードは既に使用されています")

    # メールアドレスの重複チェック
    if employee_data.email:
        existing_email = (
            db.query(Employee).filter(Employee.email == employee_data.email).first()
        )

        if existing_email:
            raise HTTPException(status_code=400, detail="このメールアドレスは既に使用されています")

    # 部署の存在チェック
    if employee_data.department_id:
        department = (
            db.query(Department)
            .filter(Department.id == employee_data.department_id)
            .first()
        )

        if not department:
            raise HTTPException(status_code=400, detail="指定された部署が見つかりません")

    # 従業員作成
    employee = Employee(**employee_data.dict())
    db.add(employee)
    db.commit()
    db.refresh(employee)

    return EmployeeResponse.from_orm(employee)


@router.get("/departments", response_model=List[dict])
async def get_departments(
    db: Session = Depends(get_db), current_user=Depends(require_manager)
):
    """
    部署一覧取得

    Returns:
        部署一覧
    """
    departments = db.query(Department).filter(Department.is_active == True).all()

    return [
        {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "employee_count": len([emp for emp in dept.employees if emp.is_active]),
        }
        for dept in departments
    ]


@router.post("/departments")
async def create_department(
    name: str,
    code: str,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    部署作成

    Args:
        name: 部署名
        code: 部署コード
        description: 説明

    Returns:
        作成された部署情報
    """
    # 部署コードの重複チェック
    existing = db.query(Department).filter(Department.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail="この部署コードは既に使用されています")

    department = Department(name=name, code=code, description=description)

    db.add(department)
    db.commit()
    db.refresh(department)

    return department.to_dict()


@router.get("/stats")
async def get_employee_stats(
    db: Session = Depends(get_db), current_user=Depends(require_manager)
):
    """
    従業員統計情報取得

    Returns:
        従業員統計
    """
    total_employees = db.query(Employee).count()
    active_employees = db.query(Employee).filter(Employee.is_active == True).count()
    departments_count = (
        db.query(Department).filter(Department.is_active == True).count()
    )

    # 部署別従業員数
    dept_stats = (
        db.query(Department.name, db.func.count(Employee.id).label("employee_count"))
        .join(Employee, Department.id == Employee.department_id, isouter=True)
        .filter(Department.is_active == True, Employee.is_active == True)
        .group_by(Department.id, Department.name)
        .all()
    )

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "departments_count": departments_count,
        "department_breakdown": [
            {"department": name, "count": count} for name, count in dept_stats
        ],
        "capacity_utilization": {"message": "無制限対応済み", "unlimited": True},
    }
