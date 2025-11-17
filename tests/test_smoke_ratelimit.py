"""
スモークテスト: レート制限とAuth動作確認

レート制限が正しく動作することを確認する最小限のテスト。
他のテストはレート制限を無効化して実行する。
"""

import hashlib
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from time import sleep

from backend.app.database import Base, get_db
from backend.app.models import User, UserRole, Employee, WageType
from backend.app.services.auth_service import AuthService
from config.config import config


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_smoke.db"

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
def test_employee(test_db):
    """テスト用従業員を作成"""
    db = TestingSessionLocal()
    try:
        # 16進数形式のcard_idm
        card_idm = "0123456789abcdef"
        card_hash = hashlib.sha256(
            f"{card_idm}{config.IDM_HASH_SECRET}".encode()
        ).hexdigest()

        employee = Employee(
            employee_code="SMOKE_001",
            name="スモークテスト太郎",
            card_idm_hash=card_hash,
            wage_type=WageType.MONTHLY,
            monthly_salary=300000,
            is_active=True,
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return {"employee": employee, "card_idm": card_idm, "card_hash": card_hash}
    finally:
        db.close()


def test_auth_200_success(client, test_admin_user):
    """Auth: 正常ログインで200を返すこと"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123!"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_auth_401_invalid_credentials(client, test_admin_user):
    """Auth: 不正な認証情報で401を返すこと"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrong_password"}
    )
    assert response.status_code == 401


@pytest.mark.skipif(
    os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "false",
    reason="レート制限が無効化されているためスキップ"
)
def test_punch_ratelimit_429(client, test_employee):
    """Punch: レート制限（10/minute）が正しく動作し429を返すこと"""
    card_idm = test_employee["card_idm"]

    # 12回連続で打刻リクエスト（レート制限は10/minute）
    responses = []
    for i in range(12):
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm": card_idm, "punch_type": "in"}
        )
        responses.append(response.status_code)

    # 最初の1回は成功（200）
    assert responses[0] == 200, "最初のリクエストは成功すべき"

    # 11回目以降は429（Too Many Requests）が返されるはず
    count_429 = sum(1 for status in responses if status == 429)
    assert count_429 >= 1, f"レート制限超過時に少なくとも1回は429が返されるべき（実際: {count_429}回）"


def test_health_no_ratelimit(client):
    """Health: レート制限が適用されないこと"""
    # 20回連続でヘルスチェック（レート制限があれば429になるはず）
    for _ in range(20):
        response = client.get("/health")
        assert response.status_code == 200, "ヘルスチェックはレート制限から除外されるべき"
