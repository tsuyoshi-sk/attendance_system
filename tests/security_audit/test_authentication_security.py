"""
認証・認可のセキュリティテスト

OWASP A01:2021 - Broken Access Control の検証
"""

import pytest
from fastapi.testclient import TestClient


def test_unauthorized_access_to_admin_endpoint(client):
    """認証なしで管理者エンドポイントにアクセスできないことを確認"""
    response = client.get("/api/v1/admin/employees")
    assert response.status_code == 401, "認証なしのアクセスは401で拒否されるべき"


def test_employee_cannot_access_admin_endpoint(client, test_employee_user, employee_auth_headers):
    """一般従業員が管理者エンドポイントにアクセスできないことを確認"""
    response = client.get("/api/v1/admin/employees", headers=employee_auth_headers)
    assert response.status_code == 403, "権限不足のアクセスは403で拒否されるべき"


def test_invalid_jwt_token(client):
    """不正なJWTトークンが拒否されることを確認"""
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
    headers = {"Authorization": f"Bearer {invalid_token}"}

    response = client.get("/api/v1/admin/employees", headers=headers)
    assert response.status_code == 401, "不正なトークンは401で拒否されるべき"


def test_expired_token_rejected(client):
    """期限切れトークンが拒否されることを確認"""
    # TODO: 期限切れトークンを生成してテスト
    pass


def test_brute_force_protection(client, test_admin_user):
    """ブルートフォース攻撃対策（連続ログイン失敗）"""
    # 10回連続で間違ったパスワードでログイン試行
    failed_attempts = 0
    for i in range(15):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test_admin", "password": f"wrong_password_{i}"}
        )
        if response.status_code == 429:  # Too Many Requests
            failed_attempts += 1

    # レート制限が働いていることを確認
    assert failed_attempts > 0, "ブルートフォース攻撃はレート制限で防がれるべき"


def test_sql_injection_in_login(client):
    """ログイン時のSQLインジェクション対策"""
    malicious_inputs = [
        "admin' OR '1'='1",
        "admin'--",
        "admin' OR 1=1--",
        "' OR ''='",
    ]

    for malicious_input in malicious_inputs:
        response = client.post(
            "/api/v1/auth/login",
            data={"username": malicious_input, "password": "password"}
        )
        # SQLインジェクションが成功していないことを確認（200で認証成功してはいけない）
        assert response.status_code != 200, f"SQLインジェクション '{malicious_input}' が防がれるべき"


def test_password_strength_requirements():
    """パスワード強度要件のテスト"""
    from backend.app.services.auth_service import AuthService

    # TODO: パスワード強度チェックが実装されている場合のテスト
    # 弱いパスワード: "123", "password", "admin"
    # 強いパスワード: "Str0ng!Pass#123"
    pass


def test_session_fixation_prevention(client, auth_headers):
    """セッション固定攻撃の防止"""
    # 1回目のログインでトークン取得
    response1 = client.post(
        "/api/v1/auth/login",
        data={"username": "test_admin", "password": "test123"}
    )
    token1 = response1.json()["access_token"]

    # 2回目のログインでトークン取得
    response2 = client.post(
        "/api/v1/auth/login",
        data={"username": "test_admin", "password": "test123"}
    )
    token2 = response2.json()["access_token"]

    # トークンが異なることを確認（セッション固定を防ぐ）
    assert token1 != token2, "ログインごとに新しいトークンが発行されるべき"


def test_horizontal_privilege_escalation(client):
    """水平権限昇格の防止（他ユーザーのデータアクセス）"""
    # TODO: 従業員Aが従業員Bのデータにアクセスできないことを確認
    pass


def test_vertical_privilege_escalation(client):
    """垂直権限昇格の防止（一般ユーザーが管理者権限を取得）"""
    # TODO: 一般ユーザーが管理者APIにアクセスできないことを確認
    pass
