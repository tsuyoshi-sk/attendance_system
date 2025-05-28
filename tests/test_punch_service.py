"""
打刻サービステスト

打刻ビジネスロジックの包括的なテストケース
"""

import pytest
from datetime import datetime, timedelta, date, time
from unittest.mock import Mock, patch
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models import Employee, PunchRecord, PunchType
from backend.app.services.punch_service import PunchService
from backend.app.database import Base
from config.config import config


# テスト用データベース設定
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_service.db"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db():
    """テスト用データベースセッション"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def punch_service(db):
    """打刻サービスインスタンス"""
    return PunchService(db)


@pytest.fixture
def test_employee(db):
    """テスト用従業員データ"""
    # IDmハッシュ化
    test_idm = "0123456789ABCDEF"
    idm_hash = hashlib.sha256(
        f"{test_idm}{config.IDM_HASH_SECRET}".encode()
    ).hexdigest()

    employee = Employee(
        employee_code="SVC001",
        name="サービステスト",
        email="service@test.com",
        card_idm_hash=idm_hash,
        is_active=True,
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    yield employee

    # クリーンアップ
    db.query(PunchRecord).filter(PunchRecord.employee_id == employee.id).delete()
    db.query(Employee).filter(Employee.id == employee.id).delete()
    db.commit()


class TestPunchService:
    """打刻サービステストクラス"""

    @pytest.mark.asyncio
    async def test_create_punch_basic(self, punch_service, test_employee):
        """基本的な打刻作成のテスト"""
        result = await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.IN,
            timestamp=datetime.now(),
        )

        assert result["success"] is True
        assert "出勤" in result["message"]
        assert result["employee"]["id"] == test_employee.id
        assert result["punch"]["punch_type"] == "in"

    @pytest.mark.asyncio
    async def test_duplicate_punch_prevention(self, punch_service, test_employee):
        """重複打刻防止のテスト"""
        timestamp = datetime.now()

        # 1回目の打刻
        await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.IN,
            timestamp=timestamp,
        )

        # 2分後の重複打刻（3分以内なので拒否される）
        with pytest.raises(ValueError, match="重複打刻エラー"):
            await punch_service.create_punch(
                card_idm_hash=test_employee.card_idm_hash,
                punch_type=PunchType.OUT,
                timestamp=timestamp + timedelta(minutes=2),
            )

        # 4分後の打刻（3分以上経過なのでOK）
        result = await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.OUT,
            timestamp=timestamp + timedelta(minutes=4),
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_daily_limits(self, punch_service, test_employee):
        """日次制限のテスト"""
        base_time = datetime.now()

        # IN打刻（1日1回まで）
        await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.IN,
            timestamp=base_time,
        )

        # 2回目のIN打刻（制限超過）
        with pytest.raises(ValueError, match="日次制限エラー.*出勤.*1回まで"):
            await punch_service.create_punch(
                card_idm_hash=test_employee.card_idm_hash,
                punch_type=PunchType.IN,
                timestamp=base_time + timedelta(hours=1),
            )

        # OUTSIDE/RETURNは3回まで
        for i in range(3):
            await punch_service.create_punch(
                card_idm_hash=test_employee.card_idm_hash,
                punch_type=PunchType.OUTSIDE,
                timestamp=base_time + timedelta(hours=2 + i, minutes=30),
            )

            await punch_service.create_punch(
                card_idm_hash=test_employee.card_idm_hash,
                punch_type=PunchType.RETURN,
                timestamp=base_time + timedelta(hours=3 + i),
            )

        # 4回目のOUTSIDE（制限超過）
        with pytest.raises(ValueError, match="日次制限エラー.*外出.*3回まで"):
            await punch_service.create_punch(
                card_idm_hash=test_employee.card_idm_hash,
                punch_type=PunchType.OUTSIDE,
                timestamp=base_time + timedelta(hours=10),
            )

    @pytest.mark.asyncio
    async def test_punch_sequence_validation(self, punch_service, test_employee):
        """打刻順序検証のテスト"""
        # 最初の打刻はINである必要がある
        with pytest.raises(ValueError, match="最初の打刻は出勤"):
            await punch_service.create_punch(
                card_idm_hash=test_employee.card_idm_hash,
                punch_type=PunchType.OUT,
                timestamp=datetime.now(),
            )

        # 正しい順序: IN -> OUTSIDE -> RETURN -> OUT
        base_time = datetime.now()

        # IN
        await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.IN,
            timestamp=base_time,
        )

        # OUTSIDEの前にRETURNは不可
        with pytest.raises(ValueError):
            await punch_service.create_punch(
                card_idm_hash=test_employee.card_idm_hash,
                punch_type=PunchType.RETURN,
                timestamp=base_time + timedelta(minutes=5),
            )

        # OUTSIDE
        await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.OUTSIDE,
            timestamp=base_time + timedelta(minutes=10),
        )

        # RETURN
        await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.RETURN,
            timestamp=base_time + timedelta(minutes=15),
        )

        # OUT
        await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.OUT,
            timestamp=base_time + timedelta(minutes=20),
        )

        # OUT後は何も打刻できない
        with pytest.raises(ValueError):
            await punch_service.create_punch(
                card_idm_hash=test_employee.card_idm_hash,
                punch_type=PunchType.IN,
                timestamp=base_time + timedelta(minutes=25),
            )

    @pytest.mark.asyncio
    async def test_night_shift_handling(self, punch_service, test_employee):
        """深夜勤務対応のテスト"""
        # 22:00に出勤
        night_in = datetime.combine(date.today(), time(22, 0))

        result = await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.IN,
            timestamp=night_in,
        )

        assert result["work_date"] == date.today().isoformat()

        # 翌日の2:00に退勤（前日の勤務として扱う）
        next_day_out = night_in + timedelta(hours=4)  # 翌日2:00

        result = await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.OUT,
            timestamp=next_day_out,
        )

        # 深夜勤務のため、勤務日は前日扱い
        assert result["work_date"] == date.today().isoformat()

    @pytest.mark.asyncio
    async def test_invalid_employee(self, punch_service):
        """無効な従業員のテスト"""
        invalid_hash = hashlib.sha256("INVALID".encode()).hexdigest()

        with pytest.raises(ValueError, match="未登録のカード"):
            await punch_service.create_punch(
                card_idm_hash=invalid_hash,
                punch_type=PunchType.IN,
                timestamp=datetime.now(),
            )

    @pytest.mark.asyncio
    async def test_inactive_employee(self, punch_service, db):
        """非アクティブ従業員のテスト"""
        # 非アクティブな従業員を作成
        inactive_employee = Employee(
            employee_code="INACTIVE001",
            name="非アクティブ",
            card_idm_hash=hashlib.sha256("inactive".encode()).hexdigest(),
            is_active=False,
        )
        db.add(inactive_employee)
        db.commit()

        with pytest.raises(ValueError, match="無効な従業員"):
            await punch_service.create_punch(
                card_idm_hash=inactive_employee.card_idm_hash,
                punch_type=PunchType.IN,
                timestamp=datetime.now(),
            )

        # クリーンアップ
        db.query(Employee).filter(Employee.id == inactive_employee.id).delete()
        db.commit()

    @pytest.mark.asyncio
    async def test_get_employee_status(self, punch_service, test_employee):
        """従業員状態取得のテスト"""
        # 打刻前の状態
        status = await punch_service.get_employee_status(test_employee.id)
        assert status["current_status"] == "未出勤"
        assert status["punch_count"] == 0

        # 出勤打刻
        await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.IN,
            timestamp=datetime.now(),
        )

        # 打刻後の状態
        status = await punch_service.get_employee_status(test_employee.id)
        assert status["current_status"] == "勤務中"
        assert status["punch_count"] == 1
        assert status["remaining_punches"]["in"] == 0  # IN残り0回
        assert status["remaining_punches"]["outside"] == 3  # OUTSIDE残り3回

    @pytest.mark.asyncio
    async def test_get_punch_history(self, punch_service, test_employee):
        """打刻履歴取得のテスト"""
        base_time = datetime.now()

        # 複数の打刻を作成
        await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.IN,
            timestamp=base_time,
        )

        await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.OUT,
            timestamp=base_time + timedelta(hours=8),
        )

        # 履歴取得
        history = await punch_service.get_punch_history(
            employee_id=test_employee.id, date=base_time.strftime("%Y-%m-%d")
        )

        assert len(history["records"]) == 2
        assert history["records"][0]["punch_type"] == "out"  # 新しい順
        assert history["records"][1]["punch_type"] == "in"

    @pytest.mark.asyncio
    async def test_performance(self, punch_service, test_employee):
        """パフォーマンステスト"""
        import time

        start_time = time.time()

        result = await punch_service.create_punch(
            card_idm_hash=test_employee.card_idm_hash,
            punch_type=PunchType.IN,
            timestamp=datetime.now(),
        )

        end_time = time.time()
        processing_time = end_time - start_time

        assert result["success"] is True
        assert processing_time < 1.0  # 1秒以内に処理完了
