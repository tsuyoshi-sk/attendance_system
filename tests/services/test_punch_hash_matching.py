"""
PunchService - BIN/STRハッシュマッチングテスト

カードIDmのBIN方式とSTR方式の両方のハッシュ照合が正しく動作することを確認
"""

import hashlib
import binascii
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.models import Employee, WageType
from backend.app.services.punch_service import PunchService, PunchServiceError
from backend.app.models.punch_record import PunchType
from config.config import config


# テスト用データベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_hash_matching.db"

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
    """DBセッションを提供"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_bin_hash_matching(db_session):
    """
    BIN方式のハッシュマッチングが正しく動作すること

    BIN方式: hex文字列をバイトに変換してからハッシュ
    """
    # 準備: 従業員をBIN方式ハッシュで登録
    card_idm = "0123456789abcdef"
    card_idm_bytes = binascii.unhexlify(card_idm)
    bin_hash = hashlib.sha256(
        card_idm_bytes + config.IDM_HASH_SECRET.encode()
    ).hexdigest()

    employee = Employee(
        employee_code="BIN_TEST_001",
        name="BIN方式テスト太郎",
        card_idm_hash=bin_hash,
        wage_type=WageType.MONTHLY,
        monthly_salary=300000,
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    # 実行: BIN方式で打刻
    service = PunchService(db_session)
    result = service.create_punch(
        card_idm=card_idm,
        punch_type=PunchType.IN,
    )

    # 検証
    assert result["success"] is True
    assert result["employee"]["id"] == employee.id
    assert result["employee"]["name"] == "BIN方式テスト太郎"


def test_str_hash_matching(db_session):
    """
    STR方式のハッシュマッチングが正しく動作すること

    STR方式: 文字列として結合してからハッシュ（互換性用）
    """
    # 準備: 従業員をSTR方式ハッシュで登録
    card_idm = "fedcba9876543210"
    str_hash = hashlib.sha256(
        f"{card_idm}{config.IDM_HASH_SECRET}".encode()
    ).hexdigest()

    employee = Employee(
        employee_code="STR_TEST_001",
        name="STR方式テスト花子",
        card_idm_hash=str_hash,
        wage_type=WageType.MONTHLY,
        monthly_salary=300000,
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    # 実行: STR方式で打刻
    service = PunchService(db_session)
    result = service.create_punch(
        card_idm=card_idm,
        punch_type=PunchType.IN,
    )

    # 検証
    assert result["success"] is True
    assert result["employee"]["id"] == employee.id
    assert result["employee"]["name"] == "STR方式テスト花子"


def test_bin_str_fallback(db_session):
    """
    BIN方式でマッチしない場合、STR方式でフォールバックすること
    """
    # 準備: STR方式のみで登録された従業員
    card_idm = "1122334455667788"
    str_hash = hashlib.sha256(
        f"{card_idm}{config.IDM_HASH_SECRET}".encode()
    ).hexdigest()

    employee = Employee(
        employee_code="FALLBACK_TEST_001",
        name="フォールバックテスト次郎",
        card_idm_hash=str_hash,
        wage_type=WageType.HOURLY,
        hourly_rate=1500,
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    # 実行: カードIDmで打刻（内部でBIN→STRの順に試行）
    service = PunchService(db_session)
    result = service.create_punch(
        card_idm=card_idm,
        punch_type=PunchType.IN,
    )

    # 検証: STR方式でマッチして成功
    assert result["success"] is True
    assert result["employee"]["id"] == employee.id


def test_unknown_card_error(db_session):
    """
    未登録のカードIDmでエラーが発生すること
    """
    # 準備: 未登録のカードIDm
    unknown_card_idm = "9999999999999999"

    # 実行 & 検証
    service = PunchService(db_session)
    with pytest.raises(PunchServiceError) as exc_info:
        service.create_punch(
            card_idm=unknown_card_idm,
            punch_type=PunchType.IN,
        )

    assert exc_info.value.code == "EMPLOYEE_NOT_FOUND"


def test_direct_hash_matching(db_session):
    """
    ハッシュを直接渡した場合も正しく動作すること
    """
    # 準備: ハッシュ値を事前計算
    card_idm = "aabbccddeeff0011"
    card_idm_bytes = binascii.unhexlify(card_idm)
    bin_hash = hashlib.sha256(
        card_idm_bytes + config.IDM_HASH_SECRET.encode()
    ).hexdigest()

    employee = Employee(
        employee_code="HASH_TEST_001",
        name="ハッシュ直接テスト三郎",
        card_idm_hash=bin_hash,
        wage_type=WageType.MONTHLY,
        monthly_salary=400000,
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    # 実行: ハッシュ値を直接渡す
    service = PunchService(db_session)
    result = service.create_punch(
        card_idm_hash=bin_hash,
        punch_type=PunchType.IN,
    )

    # 検証
    assert result["success"] is True
    assert result["employee"]["id"] == employee.id
