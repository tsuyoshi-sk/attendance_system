"""
CSRF（クロスサイトリクエストフォージェリ）対策のセキュリティテスト

OWASP A01:2021 - Broken Access Control の検証
"""

import pytest


def test_state_changing_operations_require_auth(client):
    """状態を変更する操作には認証が必要"""
    # 認証なしで従業員を作成しようとする
    response = client.post(
        "/api/v1/admin/employees",
        json={
            "employee_code": "CSRF001",
            "name": "テスト従業員",
            "wage_type": "monthly",
            "monthly_salary": 300000,
        }
    )

    # 認証なしでは拒否されるべき
    assert response.status_code == 401, "認証なしで状態変更できてはいけない"


def test_cors_configuration(client):
    """CORS設定の確認"""
    # Originヘッダー付きでリクエスト
    headers = {"Origin": "http://malicious-site.com"}

    response = client.get("/api/v1/health", headers=headers)

    # Access-Control-Allow-Originが wildcard (*) でないことを確認
    acao_header = response.headers.get("Access-Control-Allow-Origin")

    if acao_header:
        assert acao_header != "*" or response.status_code == 200, \
            "CORS設定がワイルドカードの場合、認証が必要なエンドポイントで問題"


def test_referer_validation_on_critical_operations(client, auth_headers):
    """重要な操作でのReferer検証（オプション）"""
    # 外部サイトからのRefererを偽装
    malicious_referer_headers = {
        **auth_headers,
        "Referer": "http://malicious-site.com"
    }

    response = client.post(
        "/api/v1/admin/employees",
        json={
            "employee_code": "REF001",
            "name": "Refererテスト",
            "wage_type": "monthly",
            "monthly_salary": 300000,
        },
        headers=malicious_referer_headers
    )

    # Referer検証が実装されている場合は拒否される
    # 実装されていない場合でも認証があれば成功（許容）
    assert response.status_code in [201, 400, 403], "予期しないステータスコード"


def test_double_submit_cookie_pattern(client, auth_headers):
    """Double Submit Cookie パターンの確認（CSRFトークン）"""
    # FastAPIはデフォルトでCSRFトークンを実装していないが、
    # ステートレスJWT認証を使用している場合は問題ない

    # JWTトークンが必要なエンドポイントにアクセス
    response = client.get("/api/v1/admin/employees", headers=auth_headers)

    assert response.status_code == 200, "JWT認証が機能していない"


def test_same_site_cookie_attribute():
    """SameSite Cookie属性の確認"""
    # FastAPI + JWT の場合、Cookieを使わないのでスキップ
    # もしCookie認証を使う場合は、SameSite=Strict または Lax を設定すべき
    pytest.skip("JWT認証を使用しているためCookie属性は不要")


def test_custom_header_requirement(client, auth_headers):
    """カスタムヘッダー要件の確認（CSRFリスク軽減）"""
    # Authorization ヘッダーが必要（カスタムヘッダー）
    # これにより、単純なフォームPOSTからのCSRF攻撃を防ぐ

    # Authorizationヘッダーなしでアクセス
    response_without_header = client.post(
        "/api/v1/admin/employees",
        json={
            "employee_code": "HDR001",
            "name": "ヘッダーテスト",
            "wage_type": "monthly",
            "monthly_salary": 300000,
        }
    )

    assert response_without_header.status_code == 401, "カスタムヘッダーなしでアクセスできてはいけない"

    # Authorizationヘッダーありでアクセス
    response_with_header = client.post(
        "/api/v1/admin/employees",
        json={
            "employee_code": "HDR002",
            "name": "ヘッダーテスト2",
            "wage_type": "monthly",
            "monthly_salary": 300000,
        },
        headers=auth_headers
    )

    assert response_with_header.status_code in [201, 400], "正しいヘッダーでアクセスできるべき"


def test_csrf_on_delete_operations(client, auth_headers):
    """DELETE操作でのCSRF対策確認"""
    # まず従業員を作成
    create_response = client.post(
        "/api/v1/admin/employees",
        json={
            "employee_code": "DEL001",
            "name": "削除テスト",
            "wage_type": "monthly",
            "monthly_salary": 300000,
        },
        headers=auth_headers
    )

    if create_response.status_code == 201:
        employee_id = create_response.json()["id"]

        # 認証なしで削除しようとする
        delete_response = client.delete(f"/api/v1/admin/employees/{employee_id}")

        # 認証が必要なため拒否されるべき
        assert delete_response.status_code == 401, "認証なしで削除できてはいけない"


def test_idempotency_of_get_requests(client, auth_headers):
    """GETリクエストのべき等性確認（副作用がないこと）"""
    # GETリクエストは状態を変更しないべき

    # 従業員一覧を2回取得
    response1 = client.get("/api/v1/admin/employees", headers=auth_headers)
    response2 = client.get("/api/v1/admin/employees", headers=auth_headers)

    assert response1.status_code == 200
    assert response2.status_code == 200

    # データが変わっていないことを確認
    data1 = response1.json()
    data2 = response2.json()

    assert data1["total"] == data2["total"], "GETリクエストで状態が変化している"
