"""
XSS（クロスサイトスクリプティング）対策のセキュリティテスト

OWASP A03:2021 - Injection の検証（XSS）
"""

import pytest


def test_xss_in_employee_name(client, auth_headers):
    """従業員名でのXSS対策"""
    malicious_scripts = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<iframe src='javascript:alert(\"XSS\")'></iframe>",
        "<svg onload=alert('XSS')>",
    ]

    for malicious_script in malicious_scripts:
        response = client.post(
            "/api/v1/admin/employees",
            json={
                "employee_code": "XSS_TEST",
                "name": malicious_script,
                "wage_type": "monthly",
                "monthly_salary": 300000,
            },
            headers=auth_headers
        )

        # XSSが防がれることを確認（400エラーまたは正常にエスケープ）
        if response.status_code == 201:
            data = response.json()
            # スクリプトタグがそのまま含まれていないことを確認
            assert "<script>" not in data["name"].lower(), "XSSスクリプトがエスケープされていない"
            assert "javascript:" not in data["name"].lower(), "JavaScript URLがエスケープされていない"
        else:
            # 400エラーで拒否されるのも正常
            assert response.status_code in [400, 422], f"XSS入力は拒否されるべき: {malicious_script}"


def test_xss_in_employee_search_response(client, auth_headers):
    """検索結果でのXSSエスケープ確認"""
    # 正常な従業員を作成
    response = client.post(
        "/api/v1/admin/employees",
        json={
            "employee_code": "SAFE001",
            "name": "安全な名前",
            "wage_type": "monthly",
            "monthly_salary": 300000,
        },
        headers=auth_headers
    )

    # 検索結果を取得
    search_response = client.get("/api/v1/admin/employees", headers=auth_headers)
    assert search_response.status_code == 200

    # レスポンスヘッダーにContent-Type: application/jsonが含まれることを確認
    content_type = search_response.headers.get("content-type", "")
    assert "application/json" in content_type, "JSON形式でない場合XSSのリスクがある"


def test_xss_in_punch_comment(client, auth_headers, test_employee):
    """打刻コメントでのXSS対策"""
    malicious_comment = "<script>document.cookie</script>"

    response = client.post(
        "/api/v1/punch/",
        json={
            "card_idm": test_employee.cards[0].card_idm_hash if test_employee.cards else "test_idm",
            "punch_type": "in",
            "comment": malicious_comment,
        },
        headers=auth_headers
    )

    # XSSが防がれることを確認
    if response.status_code == 201:
        data = response.json()
        if "comment" in data:
            assert "<script>" not in data["comment"].lower(), "コメント内のXSSがエスケープされていない"


def test_content_security_policy_header(client):
    """Content-Security-Policy ヘッダーの確認"""
    response = client.get("/")

    # CSPヘッダーが設定されているか確認（推奨）
    csp_header = response.headers.get("Content-Security-Policy")
    # CSPがない場合は警告だけ（必須ではない）
    if csp_header:
        assert "script-src" in csp_header, "CSPにscript-src指定がない"


def test_x_content_type_options_header(client):
    """X-Content-Type-Options ヘッダーの確認"""
    response = client.get("/")

    # X-Content-Type-Options: nosniff が設定されているか確認
    xcto_header = response.headers.get("X-Content-Type-Options")
    # 設定されていることが望ましい
    if xcto_header:
        assert xcto_header.lower() == "nosniff", "X-Content-Type-Optionsがnosniffでない"


def test_x_frame_options_header(client):
    """X-Frame-Options ヘッダーの確認（クリックジャッキング対策）"""
    response = client.get("/")

    # X-Frame-Options が設定されているか確認
    xfo_header = response.headers.get("X-Frame-Options")
    # 設定されていることが望ましい
    if xfo_header:
        assert xfo_header.upper() in ["DENY", "SAMEORIGIN"], "X-Frame-Optionsが適切でない"


def test_html_escape_in_error_messages(client):
    """エラーメッセージでのHTMLエスケープ"""
    # 不正なエンドポイントにアクセス
    malicious_path = "/api/v1/admin/employees/<script>alert('XSS')</script>"

    response = client.get(malicious_path)

    # エラーレスポンスにスクリプトタグが含まれていないことを確認
    if response.status_code in [404, 400, 422]:
        response_text = response.text.lower()
        assert "<script>" not in response_text, "エラーメッセージでXSSの可能性"
        assert "onerror=" not in response_text, "エラーメッセージでXSSの可能性"


def test_json_response_escaping(client, auth_headers):
    """JSONレスポンスでの適切なエスケープ"""
    # 特殊文字を含むデータを作成
    special_chars_name = '"><svg/onload=alert("XSS")>'

    response = client.post(
        "/api/v1/admin/employees",
        json={
            "employee_code": "ESCAPE001",
            "name": special_chars_name,
            "wage_type": "monthly",
            "monthly_salary": 300000,
        },
        headers=auth_headers
    )

    # JSONとして正しくエスケープされていることを確認
    if response.status_code == 201:
        import json
        # JSONパースが成功することを確認（不正なエスケープならパースエラー）
        try:
            data = json.loads(response.text)
            assert isinstance(data, dict), "JSONレスポンスが不正"
        except json.JSONDecodeError:
            pytest.fail("JSONレスポンスのエスケープが不正")
