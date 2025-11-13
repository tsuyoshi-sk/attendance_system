"""
PunchService - 深夜跨ぎの勤務境界テスト

NIGHT_SHIFT_CUTOFF_HOUR（5時）を跨ぐ打刻が同一勤務日として扱われることを検証
"""

from datetime import datetime
import hashlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.models import Employee, WageType
from backend.app.services.punch_service import PunchService
from backend.app.models.punch_record import PunchType
from config.config import config


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_punch_overnight.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def test_db():
    """テスト用DBスキーマを作成/破棄"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db):
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _prepare_employee(db_session, employee_code="OVERNIGHT_001"):
    """テスト用従業員（カード登録済み）を作成"""
    card_idm = "1234567890abcdef"
    card_hash = hashlib.sha256(
        f"{card_idm}{config.IDM_HASH_SECRET}".encode()
    ).hexdigest()

    employee = Employee(
        employee_code=employee_code,
        name="深夜テスト従業員",
        card_idm_hash=card_hash,
        wage_type=WageType.MONTHLY,
        monthly_salary=320000,
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee, card_idm


def test_work_date_rolls_back_before_cutoff(db_session):
    """5時未満の打刻は前日扱いになる"""
    employee, card_idm = _prepare_employee(db_session, "OVERNIGHT_ROLLBACK")
    service = PunchService(db_session)

    punch_time = datetime(2024, 5, 2, 2, 0, 0)  # 深夜（翌日2時）
    result = service.create_punch(
        card_idm=card_idm,
        punch_type=PunchType.IN,
        timestamp=punch_time,
    )

    assert result["success"] is True
    assert result["employee"]["id"] == employee.id
    # work_dateは前日の 2024-05-01 になる
    assert result["work_date"] == "2024-05-01"


def test_overnight_sequence_keeps_single_workday(db_session):
    """23時台→翌2時のシーケンスが同一勤務日として扱われる"""
    _, card_idm = _prepare_employee(db_session, "OVERNIGHT_SEQUENCE")
    service = PunchService(db_session)

    late_night = datetime(2024, 5, 1, 23, 10, 0)
    early_morning = datetime(2024, 5, 2, 2, 5, 0)

    first = service.create_punch(
        card_idm=card_idm,
        punch_type=PunchType.IN,
        timestamp=late_night,
    )
    second = service.create_punch(
        card_idm=card_idm,
        punch_type=PunchType.OUT,
        timestamp=early_morning,
    )

    assert first["success"] is True
    assert second["success"] is True
    # どちらも同じ勤務日扱い
    assert first["work_date"] == second["work_date"] == "2024-05-01"
