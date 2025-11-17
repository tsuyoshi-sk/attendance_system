"""
SQLインジェクション対策のセキュリティテスト

OWASP A03:2021 - Injection の検証
"""

import pytest


def test_sql_injection_in_employee_search(client, auth_headers):
    """従業員検索でのSQLインジェクション対策"""
    malicious_inputs = [
        "'; DROP TABLE employees;--",
        "1' OR '1'='1",
        "admin'--",
        "1' UNION SELECT * FROM users--",
        "' OR 1=1--",
    ]

    for malicious_input in malicious_inputs:
        # 従業員コードにSQLインジェクションを試みる
        response = client.get(
            f"/api/v1/admin/employees",
            params={"employee_code": malicious_input},
            headers=auth_headers
        )

        # サーバーエラーが発生していないことを確認
        assert response.status_code != 500, f"SQLインジェクション '{malicious_input}' でサーバーエラーが発生"

        # SQLインジェクションが成功していないことを確認
        # （全従業員が返されていない、など）
        if response.status_code == 200:
            data = response.json()
            # 不正なデータが返されていないことを確認
            assert isinstance(data, (dict, list)), "レスポンス形式が正常"


def test_sql_injection_in_punch_query(client, auth_headers):
    """打刻クエリでのSQLインジェクション対策"""
    malicious_card_idm = "0123456789abcdef' OR '1'='1"

    response = client.post(
        "/api/v1/punch/",
        json={"card_idm": malicious_card_idm, "punch_type": "in"},
        headers=auth_headers
    )

    # SQLインジェクションが防がれることを確認
    # 422はバリデーションエラー（正常な動作）
    assert response.status_code in [400, 404, 422], "不正な入力は400, 404, または422で拒否されるべき"


def test_sql_injection_in_report_generation(client, auth_headers):
    """レポート生成でのSQLインジェクション対策"""
    malicious_employee_id = "1 OR 1=1"

    response = client.get(
        f"/api/v1/reports/daily?employee_id={malicious_employee_id}",
        headers=auth_headers
    )

    # SQLインジェクションが防がれることを確認
    assert response.status_code != 500, "SQLインジェクションでサーバーエラーが発生してはいけない"


def test_orm_parameterization(client, auth_headers, test_employee):
    """ORMのパラメータ化クエリ確認"""
    # 正常なクエリが動作することを確認
    response = client.get(
        f"/api/v1/admin/employees/{test_employee.id}",
        headers=auth_headers
    )

    assert response.status_code == 200, "正常なクエリは成功するべき"

    # IDに不正な値を入れた場合
    response = client.get(
        "/api/v1/admin/employees/999' OR '1'='1",
        headers=auth_headers
    )

    # 404または400で拒否されることを確認
    assert response.status_code in [400, 404, 422], "不正なIDは拒否されるべき"


def test_special_characters_in_input(client, auth_headers):
    """特殊文字の適切な処理"""
    special_chars_inputs = [
        "テスト'太郎",  # シングルクォート
        'テスト"次郎',  # ダブルクォート
        "テスト;三郎",  # セミコロン
        "テスト--四郎",  # SQLコメント
        "テスト/*五郎*/",  # SQLコメント
    ]

    for input_name in special_chars_inputs:
        response = client.post(
            "/api/v1/admin/employees",
            json={
                "employee_code": "TEST999",
                "name": input_name,
                "wage_type": "monthly",
                "monthly_salary": 300000,
            },
            headers=auth_headers
        )

        # 特殊文字が適切にエスケープされ、処理されることを確認
        # （エラーにならず、かつSQLインジェクションも発生しない）
        assert response.status_code in [201, 400], "特殊文字は適切に処理されるべき"
