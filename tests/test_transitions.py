"""
PunchType遷移の単体テストと統合テスト
"""

import pytest
from enum import Enum
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

try:
    from backend.app.models.punch_record import PunchType  # type: ignore
except Exception:
    class PunchType(str, Enum):
        IN = "in"
        OUT = "out"
        OUTSIDE = "outside"
        RETURN = "return"

from backend.app.utils.punch_helpers import VALID_TRANSITIONS


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
def client():
    """テストクライアントを作成"""
    from backend.app.main import app
    return TestClient(app)


@pytest.fixture
def test_employee_and_token(client):
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
        "department": "テスト部",
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
    punch_data = {"card_idm": card_idm, "punch_type": "in"}

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
    assert "status" in status_data
    # "出勤中" や similar Japanese status
    assert any(keyword in status_data["status"] for keyword in ["出勤", "勤務中", "在席"])

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
    assert "外出" in status_data["status"]

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
    assert "退勤" in status_data["status"]


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
