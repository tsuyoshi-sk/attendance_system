"""
PunchType遷移の単体テストと統合テスト
"""

import hashlib
from enum import Enum

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.models import User, UserRole
from backend.app.services.auth_service import AuthService
from backend.app.utils.punch_helpers import VALID_TRANSITIONS
from config.config import config

try:
    from backend.app.models.punch_record import PunchType  # type: ignore
except Exception:
    class PunchType(str, Enum):
        IN = "in"
        OUT = "out"
        OUTSIDE = "outside"
        RETURN = "return"


# ===== テスト用データベース設定 =====

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_transitions.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """FastAPI依存性をテスト用DBに差し替え"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# ===== 単体テスト =====

def test_valid_transitions():
    """有効な遷移パターンを確認"""
    assert PunchType.OUT in VALID_TRANSITIONS[PunchType.IN]
    assert PunchType.RETURN in VALID_TRANSITIONS[PunchType.OUTSIDE]
    assert PunchType.OUT in VALID_TRANSITIONS[PunchType.RETURN]
    assert VALID_TRANSITIONS[PunchType.OUT] == []


def test_invalid_paths():
    """無効な遷移パターンを確認"""
    assert PunchType.RETURN not in VALID_TRANSITIONS[PunchType.IN]
    assert PunchType.IN not in VALID_TRANSITIONS[PunchType.OUTSIDE]


# ===== 統合テスト（FastAPIクライアント使用）=====

@pytest.fixture
def test_db():
    """テスト用にDBスキーマを作成/破棄"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """依存性を差し替えたテストクライアントを作成"""
    from backend.app.main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_admin_user(test_db):
    """ログイン用の管理者ユーザーをseed"""
    db = TestingSessionLocal()
    try:
        auth_service = AuthService(db)
        admin = User(
            username="admin",
            password_hash=auth_service.get_password_hash("admin123!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    finally:
        db.close()


@pytest.fixture
def test_employee_and_token(client, test_admin_user):
    """テスト用従業員とトークンを作成"""
    # 管理者でログイン
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123!"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # テスト用従業員を作成
    employee_data = {
        "employee_code": "TEST_TRANSITION_001",
        "name": "遷移テスト太郎",
        "email": "transition.test@example.com",
        "wage_type": "monthly",
        "monthly_salary": 300000,
        "is_active": True
    }

    headers = {"Authorization": f"Bearer {token}"}
    emp_response = client.post(
        "/api/v1/admin/employees",
        json=employee_data,
        headers=headers
    )
    assert emp_response.status_code == 201
    employee = emp_response.json()

    # カードを登録
    card_idm = "abcdef0123456789"
    card_hash = hashlib.sha256(f"{card_idm}{config.IDM_HASH_SECRET}".encode()).hexdigest()

    card_response = client.post(
        f"/api/v1/admin/employees/{employee['id']}/cards",
        json={"card_idm_hash": card_hash, "card_nickname": "遷移テストカード"},
        headers=headers,
    )
    assert card_response.status_code == 201

    return {
        "employee_id": employee["id"],
        "card_idm": card_idm,
        "token": token,
        "headers": headers
    }


def test_happy_path_full_flow(client, test_employee_and_token):
    """
    ハッピーパス: IN → OUTSIDE → RETURN → OUT の完全フロー
    """
    data = test_employee_and_token
    card_idm = data["card_idm"]

    # 1. 出勤 (IN)
    response = client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "in"}
    )
    assert response.status_code == 200
    assert response.json()["punch"]["punch_type"] == "in"
    assert "出勤" in response.json()["message"]

    # 2. 外出 (OUTSIDE)
    response = client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "outside"}
    )
    assert response.status_code == 200
    assert response.json()["punch"]["punch_type"] == "outside"
    assert "外出" in response.json()["message"]

    # 3. 戻り (RETURN)
    response = client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "return"}
    )
    assert response.status_code == 200
    assert response.json()["punch"]["punch_type"] == "return"
    assert "戻り" in response.json()["message"]

    # 4. 退勤 (OUT)
    response = client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "out"}
    )
    assert response.status_code == 200
    assert response.json()["punch"]["punch_type"] == "out"
    assert "退勤" in response.json()["message"]


def test_duplicate_punch_same_type(client, test_employee_and_token):
    """
    同一種別の連続打刻は409エラーを返すこと
    """
    data = test_employee_and_token
    card_idm = data["card_idm"]

    # 事前に出勤
    client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "in"}
    )

    # 1回目の外出
    response1 = client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "outside"}
    )
    assert response1.status_code == 200

    # 即座に2回目の外出（同じタイプ）→ 409 Conflict
    response2 = client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "outside"}
    )
    assert response2.status_code == 409
    assert "DUPLICATE_PUNCH" in response2.json().get("error", {}).get("error", "")


def test_punch_status_japanese_display(client, test_employee_and_token):
    """
    status/{employee_id} エンドポイントが期待の日本語表示を返すこと
    """
    data = test_employee_and_token
    employee_id = data["employee_id"]
    card_idm = data["card_idm"]
    headers = data["headers"]

    # 出勤
    client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "in"}
    )

    # ステータス取得
    response = client.get(
        f"/api/v1/punch/status/{employee_id}",
        headers=headers
    )
    assert response.status_code == 200
    status_data = response.json()

    # 日本語表示を確認
    assert "current_status" in status_data
    # "出勤中" や similar Japanese status
    assert any(keyword in status_data["current_status"] for keyword in ["出勤", "勤務中", "在席"])

    # 外出
    client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "outside"}
    )

    # ステータス再取得
    response = client.get(
        f"/api/v1/punch/status/{employee_id}",
        headers=headers
    )
    assert response.status_code == 200
    status_data = response.json()
    assert "外出" in status_data["current_status"]

    # 退勤
    client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "return"}
    )
    client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "out"}
    )

    # 最終ステータス
    response = client.get(
        f"/api/v1/punch/status/{employee_id}",
        headers=headers
    )
    assert response.status_code == 200
    status_data = response.json()
    assert "退勤" in status_data["current_status"]


def test_invalid_sequence(client, test_employee_and_token):
    """
    無効な遷移シーケンス（IN → RETURN）はエラーを返すこと
    """
    data = test_employee_and_token
    card_idm = data["card_idm"]

    # 出勤
    response = client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "in"}
    )
    assert response.status_code == 200

    # IN → RETURN は無効
    response = client.post(
        "/api/v1/punch/",
        json={"card_idm": card_idm, "punch_type": "return"}
    )
    assert response.status_code == 400
    assert "INVALID_SEQUENCE" in response.json().get("error", {}).get("error", "")
