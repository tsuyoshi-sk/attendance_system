"""
認証システムのテスト
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database import get_db, Base
from backend.app.models import User, UserRole


# テスト用データベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_admin_user(test_db):
    """テスト用管理者ユーザーを作成"""
    db = TestingSessionLocal()
    user = User(
        username="test_admin",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: test
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def test_login_success(client, test_admin_user):
    """正常ログインテスト"""
    response = client.post(
        "/api/v1/auth/login", data={"username": "test_admin", "password": "test"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_info"]["username"] == "test_admin"
    assert data["user_info"]["role"] == "admin"


def test_login_invalid_credentials(client, test_admin_user):
    """無効な認証情報でのログインテスト"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test_admin", "password": "wrong_password"},
    )
    assert response.status_code == 401


def test_login_user_not_found(client):
    """存在しないユーザーでのログインテスト"""
    response = client.post(
        "/api/v1/auth/login", data={"username": "nonexistent", "password": "password"}
    )
    assert response.status_code == 401


def test_get_current_user(client, test_admin_user):
    """現在のユーザー情報取得テスト"""
    # ログイン
    login_response = client.post(
        "/api/v1/auth/login", data={"username": "test_admin", "password": "test"}
    )
    token = login_response.json()["access_token"]

    # ユーザー情報取得
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "test_admin"
    assert data["role"] == "admin"


def test_unauthorized_access(client):
    """認証なしでのアクセステスト"""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_invalid_token(client):
    """無効なトークンでのアクセステスト"""
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_token_verification(client, test_admin_user):
    """トークン検証テスト"""
    # ログイン
    login_response = client.post(
        "/api/v1/auth/login", data={"username": "test_admin", "password": "test"}
    )
    token = login_response.json()["access_token"]

    # トークン検証
    response = client.post(
        "/api/v1/auth/verify-token", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["username"] == "test_admin"
    assert data["role"] == "admin"


def test_init_admin(client):
    """初期管理者作成テスト"""
    response = client.post("/api/v1/auth/init-admin")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
