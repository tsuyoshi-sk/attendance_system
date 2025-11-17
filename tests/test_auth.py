"""
認証システムのテスト
"""

import pytest
# conftest.pyのfixtureを使用するため、ここでは定義不要


def test_login_success(client, test_admin_user):
    """正常ログインテスト"""
    response = client.post(
        "/api/v1/auth/login", data={"username": "test_admin", "password": "test123"}
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
        "/api/v1/auth/login", data={"username": "test_admin", "password": "test123"}
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
        "/api/v1/auth/login", data={"username": "test_admin", "password": "test123"}
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
