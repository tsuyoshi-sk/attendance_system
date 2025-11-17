"""
従業員管理システムのテスト
"""

import pytest
# conftest.pyのfixtureを使用するため、ここでは定義不要


def test_create_employee(client, auth_headers):
    """従業員作成テスト"""
    employee_data = {
        "employee_code": "EMP001",
        "name": "田中太郎",
        "email": "tanaka@example.com",
        # "department": "開発部",  # TODO: Department処理の実装後に有効化
        "position": "エンジニア",
        "employment_type": "正社員",
        "hire_date": "2024-01-15",
        "wage_type": "monthly",
        "monthly_salary": 400000,
        "is_active": True,
    }

    response = client.post(
        "/api/v1/admin/employees", json=employee_data, headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["employee_code"] == "EMP001"
    assert data["name"] == "田中太郎"
    assert data["monthly_salary"] == 400000


def test_get_employees(client, auth_headers):
    """従業員一覧取得テスト"""
    response = client.get("/api/v1/admin/employees", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data


def test_get_employee_by_id(client, auth_headers):
    """従業員詳細取得テスト"""
    # まず従業員を作成
    employee_data = {
        "employee_code": "EMP002",
        "name": "佐藤花子",
        "wage_type": "hourly",
        "hourly_rate": 2500,
    }

    create_response = client.post(
        "/api/v1/admin/employees", json=employee_data, headers=auth_headers
    )
    employee_id = create_response.json()["id"]

    # 詳細を取得
    response = client.get(
        f"/api/v1/admin/employees/{employee_id}", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["employee_code"] == "EMP002"
    assert data["name"] == "佐藤花子"


def test_update_employee(client, auth_headers):
    """従業員更新テスト"""
    # まず従業員を作成
    employee_data = {
        "employee_code": "EMP003",
        "name": "山田太郎",
        "wage_type": "monthly",
        "monthly_salary": 350000,
    }

    create_response = client.post(
        "/api/v1/admin/employees", json=employee_data, headers=auth_headers
    )
    employee_id = create_response.json()["id"]

    # 更新
    update_data = {"name": "山田次郎", "monthly_salary": 380000}

    response = client.put(
        f"/api/v1/admin/employees/{employee_id}", json=update_data, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "山田次郎"
    assert data["monthly_salary"] == 380000


def test_employee_validation_errors(client, auth_headers):
    """従業員バリデーションエラーテスト"""
    # 不正なデータ
    invalid_data = {
        "employee_code": "",  # 空のコード
        "name": "",  # 空の名前
        "wage_type": "monthly"
        # 月給制なのに月給が未設定
    }

    response = client.post(
        "/api/v1/admin/employees", json=invalid_data, headers=auth_headers
    )
    assert response.status_code == 422  # バリデーションエラー


def test_duplicate_employee_code(client, auth_headers):
    """従業員コード重複テスト"""
    employee_data = {
        "employee_code": "EMP004",
        "name": "テスト従業員",
        "wage_type": "monthly",
        "monthly_salary": 300000,
    }

    # 最初の作成は成功
    response1 = client.post(
        "/api/v1/admin/employees", json=employee_data, headers=auth_headers
    )
    assert response1.status_code == 201

    # 同じコードで再作成は失敗
    response2 = client.post(
        "/api/v1/admin/employees", json=employee_data, headers=auth_headers
    )
    assert response2.status_code == 400


def test_unauthorized_access(client):
    """認証なしでのアクセステスト"""
    response = client.get("/api/v1/admin/employees")
    assert response.status_code == 401


def test_add_employee_card(client, auth_headers):
    """従業員カード追加テスト"""
    # まず従業員を作成
    employee_data = {
        "employee_code": "EMP005",
        "name": "カード テスト",
        "wage_type": "monthly",
        "monthly_salary": 300000,
    }

    create_response = client.post(
        "/api/v1/admin/employees", json=employee_data, headers=auth_headers
    )
    employee_id = create_response.json()["id"]

    # カードを追加
    card_data = {
        "card_idm_hash": "a" * 64,  # 64文字のハッシュ
        "card_nickname": "社員証",
        "issued_date": "2024-01-15",
    }

    response = client.post(
        f"/api/v1/admin/employees/{employee_id}/cards",
        json=card_data,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["card_nickname"] == "社員証"
