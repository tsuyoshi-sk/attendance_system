"""
開発用のテスト従業員とカードを作成するスクリプト。

テスト用の従業員 (employee_code=E0001) とカード IDm (0123456789ABCDEF) を
データベースに登録し、存在しない場合のみ作成します。
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path
from typing import Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.app.database import SessionLocal  # noqa: E402
from backend.app.models import Employee, EmployeeCard, WageType  # noqa: E402
from backend.app.utils.security import CryptoUtils  # noqa: E402


EMPLOYEE_CODE = "E0001"
EMPLOYEE_NAME = "テスト太郎"
CARD_IDM = "0123456789ABCDEF"
CARD_NICKNAME = "開発用テストカード"
NORMALIZED_CARD_IDM = CARD_IDM.lower()


def ensure_test_employee() -> Tuple[Employee, bool]:
    """従業員を作成/取得する"""
    db = SessionLocal()
    created = False
    try:
        employee = (
            db.query(Employee)
            .filter(Employee.employee_code == EMPLOYEE_CODE)
            .first()
        )
        card_hash = CryptoUtils.hash_idm(NORMALIZED_CARD_IDM)

        if not employee:
            employee = Employee(
                employee_code=EMPLOYEE_CODE,
                name=EMPLOYEE_NAME,
                name_kana="テストタロウ",
                employment_type="正社員",
                wage_type=WageType.MONTHLY,
                monthly_salary=300000,
                hire_date=date(2024, 1, 1),
                is_active=True,
                card_idm_hash=card_hash,
            )
            db.add(employee)
            db.flush()
            created = True
        else:
            # 従業員が存在する場合もカード情報とステータスを整備
            if not employee.card_idm_hash or employee.card_idm_hash != card_hash:
                employee.card_idm_hash = card_hash
            if not employee.is_active:
                employee.is_active = True

        primary_card = (
            db.query(EmployeeCard)
            .filter(EmployeeCard.card_idm_hash == card_hash)
            .first()
        )

        if primary_card:
            if primary_card.employee_id != employee.id:
                primary_card.employee_id = employee.id
        else:
            primary_card = (
                db.query(EmployeeCard)
                .filter(EmployeeCard.employee_id == employee.id)
                .order_by(EmployeeCard.id.asc())
                .first()
            )
            if primary_card:
                primary_card.card_idm_hash = card_hash
            else:
                primary_card = EmployeeCard(
                    employee_id=employee.id,
                    card_idm_hash=card_hash,
                    card_nickname=CARD_NICKNAME,
                    is_active=True,
                )
                db.add(primary_card)

        primary_card.card_nickname = primary_card.card_nickname or CARD_NICKNAME
        primary_card.is_active = True

        extra_cards = (
            db.query(EmployeeCard)
            .filter(
                EmployeeCard.employee_id == employee.id,
                EmployeeCard.id != primary_card.id,
            )
            .all()
        )
        for extra_card in extra_cards:
            db.delete(extra_card)

        db.commit()
        db.refresh(employee)
        return employee, created
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    employee, created = ensure_test_employee()
    if created:
        logging.info(
            "Created test employee %s (id=%s) with card %s",
            employee.employee_code,
            employee.id,
            CARD_IDM,
        )
        print(
            f"Test employee '{employee.employee_code}' was created with card IDm {CARD_IDM}."
        )
    else:
        logging.info(
            "Test employee %s already exists (id=%s)",
            employee.employee_code,
            employee.id,
        )
        print(
            f"Test employee '{employee.employee_code}' already exists (id={employee.id})."
        )


if __name__ == "__main__":
    main()
