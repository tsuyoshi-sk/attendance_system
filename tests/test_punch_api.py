"""
打刻APIテスト

打刻APIエンドポイントの包括的なテストケース
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models import Employee, PunchRecord, PunchType
from backend.app.utils.security import CryptoUtils
from config.config import config


# テスト用データベース設定
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """テスト用データベースセッション"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    """テストクライアント"""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_employee():
    """テスト用従業員データ"""
    db = TestingSessionLocal()

    # IDmハッシュ化
    test_idm = "0123456789ABCDEF".lower()
    idm_hash = CryptoUtils.hash_idm(test_idm)

    employee = Employee(
        employee_code="TEST001",
        name="テスト太郎",
        email="test@example.com",
        card_idm_hash=idm_hash,
        is_active=True,
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)
    employee.card_idm_raw = test_idm

    yield employee

    # クリーンアップ
    db.query(PunchRecord).filter(PunchRecord.employee_id == employee.id).delete()
    db.query(Employee).filter(Employee.id == employee.id).delete()
    db.commit()
    db.close()


class TestPunchAPI:
    """打刻APIテストクラス"""

    def test_create_punch_success(self, client, test_employee):
        """正常な打刻のテスト"""
        card_idm = test_employee.card_idm_raw

        response = client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "IN",
                "card_idm": card_idm,
                "timestamp": datetime.now().isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "出勤" in data["message"]
        assert data["employee"]["id"] == test_employee.id

    def test_punch_types(self, client, test_employee):
        """全ての打刻タイプのテスト"""
        card_idm = test_employee.card_idm_raw

        # IN -> OUTSIDE -> RETURN -> OUT の順序でテスト
        punch_sequence = [
            ("IN", "出勤"),
            ("OUTSIDE", "外出"),
            ("RETURN", "戻り"),
            ("OUT", "退勤"),
        ]

        for punch_type, expected_message in punch_sequence:
            # 前の打刻から3分以上経過させる
            timestamp = datetime.now() + timedelta(minutes=5)

            response = client.post(
                "/api/v1/punch/",
                json={
                    "punch_type": punch_type,
                    "card_idm": card_idm,
                    "timestamp": timestamp.isoformat(),
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert expected_message in data["message"]

    def test_invalid_employee(self, client):
        """未登録カードのテスト"""
        invalid_card_idm = "ffffffffffffffff"

        response = client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "IN",
                "card_idm": invalid_card_idm,
                "timestamp": datetime.now().isoformat(),
            },
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["error"] == "EMPLOYEE_NOT_FOUND"

    def test_duplicate_punch(self, client, test_employee):
        """重複打刻のテスト（3分以内）"""
        card_idm = test_employee.card_idm_raw
        timestamp = datetime.now()

        # 1回目の打刻
        response1 = client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "IN",
                "card_idm": card_idm,
                "timestamp": timestamp.isoformat(),
            },
        )
        assert response1.status_code == 200

        # 2分後の重複打刻
        response2 = client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "IN",
                "card_idm": card_idm,
                "timestamp": (timestamp + timedelta(minutes=2)).isoformat(),
            },
        )

        assert response2.status_code == 409
        data = response2.json()
        assert data["error"]["error"] == "DUPLICATE_PUNCH"

    def test_daily_limit(self, client, test_employee):
        """日次制限のテスト"""
        card_idm = test_employee.card_idm_raw
        base_time = datetime.now()

        # IN打刻
        client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "IN",
                "card_idm": card_idm,
                "timestamp": base_time.isoformat(),
            },
        )

        # 外出/戻りを3回実行
        for i in range(3):
            # 外出
            client.post(
                "/api/v1/punch/",
                json={
                    "punch_type": "OUTSIDE",
                    "card_idm": card_idm,
                    "timestamp": (
                        base_time + timedelta(hours=i + 1, minutes=30)
                    ).isoformat(),
                },
            )

            # 戻り
            client.post(
                "/api/v1/punch/",
                json={
                    "punch_type": "RETURN",
                    "card_idm": card_idm,
                    "timestamp": (base_time + timedelta(hours=i + 2)).isoformat(),
                },
            )

        # 4回目の外出（制限超過）
        response = client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "OUTSIDE",
                "card_idm": card_idm,
                "timestamp": (base_time + timedelta(hours=7)).isoformat(),
            },
        )

        assert response.status_code == 429
        data = response.json()
        assert data["error"]["error"] == "DAILY_LIMIT_EXCEEDED"

    def test_invalid_punch_sequence(self, client, test_employee):
        """不正な打刻順序のテスト"""
        card_idm = test_employee.card_idm_raw

        # 出勤なしで退勤
        response = client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "OUT",
                "card_idm": card_idm,
                "timestamp": datetime.now().isoformat(),
            },
        )

        assert response.status_code == 400
        assert "最初の打刻は出勤" in response.json()["error"]["message"]

    def test_input_validation(self, client):
        """入力値検証のテスト"""
        # 不正なハッシュ形式
        response = client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "IN",
                "card_idm": "invalid_hash",
                "timestamp": datetime.now().isoformat(),
            },
        )

        assert response.status_code == 422

        # 不正な打刻タイプ
        valid_hash = hashlib.sha256("test".encode()).hexdigest()
        response = client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "INVALID",
                "card_idm": valid_hash,
                "timestamp": datetime.now().isoformat(),
            },
        )

        assert response.status_code == 422

    def test_performance(self, client, test_employee):
        """パフォーマンステスト（3秒以内）"""
        import time

        card_idm = test_employee.card_idm_raw

        start_time = time.time()
        response = client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "IN",
                "card_idm": card_idm,
                "timestamp": datetime.now().isoformat(),
            },
        )
        end_time = time.time()

        assert response.status_code == 200
        assert end_time - start_time < 3.0  # 3秒以内
        assert "X-Process-Time" in response.headers

    def test_get_punch_status(self, client, test_employee):
        """打刻状況取得のテスト"""
        card_idm = test_employee.card_idm_raw

        # 打刻実行
        client.post(
            "/api/v1/punch/",
            json={
                "punch_type": "IN",
                "card_idm": card_idm,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # 状況取得
        response = client.get(f"/api/v1/punch/status/{test_employee.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["current_status"] == "勤務中"
        assert data["employee"]["id"] == test_employee.id
        assert "remaining_punches" in data

    def test_get_punch_history(self, client, test_employee):
        """打刻履歴取得のテスト"""
        card_idm = test_employee.card_idm_raw

        # 複数の打刻を作成
        base_time = datetime.now()
        for i in range(3):
            client.post(
                "/api/v1/punch/",
                json={
                    "punch_type": "IN" if i == 0 else "OUT",
                    "card_idm": card_idm,
                    "timestamp": (base_time + timedelta(hours=i)).isoformat(),
                },
            )

        # 履歴取得
        response = client.get(
            f"/api/v1/punch/history/{test_employee.id}",
            params={"date": base_time.strftime("%Y-%m-%d")},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) >= 2
        assert data["employee"]["id"] == test_employee.id

    @patch("backend.app.utils.offline_queue_manager.add_punch")
    def test_offline_mode(self, mock_add_punch, client):
        """オフラインモードのテスト"""
        mock_add_punch.return_value = True

        # ネットワークエラーをシミュレート
        with patch(
            "backend.app.services.punch_service.PunchService.create_punch"
        ) as mock_create:
            mock_create.side_effect = ConnectionError("Network error")

            valid_hash = hashlib.sha256("test".encode()).hexdigest()
            response = client.post(
                "/api/v1/punch/",
                json={
                    "punch_type": "IN",
                    "card_idm": valid_hash,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "オフライン" in data["message"]
            assert data["punch_record"]["is_offline"] is True

    def test_offline_status(self, client):
        """オフライン状態取得のテスト"""
        response = client.get("/api/v1/punch/offline/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "statistics" in data
        assert "timestamp" in data
