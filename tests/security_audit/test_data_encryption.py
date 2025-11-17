"""
データ暗号化・保護のセキュリティテスト

OWASP A02:2021 - Cryptographic Failures の検証
"""

import pytest
import hashlib


def test_password_hashing(test_db):
    """パスワードがハッシュ化されて保存されることを確認"""
    from backend.app.models.user import User, UserRole
    from backend.app.services.auth_service import AuthService

    db = test_db.SessionLocal()
    try:
        auth_service = AuthService(db)

        # ユーザーを作成
        plain_password = "SecurePass123!"
        password_hash = auth_service.get_password_hash(plain_password)

        user = User(
            username="hash_test_user",
            password_hash=password_hash,
            role=UserRole.ADMIN
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # パスワードが平文で保存されていないことを確認
        assert user.password_hash != plain_password, "パスワードが平文で保存されている"

        # bcryptハッシュ形式であることを確認（$2b$で始まる）
        assert user.password_hash.startswith("$2b$"), "bcryptハッシュ形式でない"

        # ハッシュの長さが適切（bcryptは60文字）
        assert len(user.password_hash) == 60, "bcryptハッシュの長さが不正"

        # パスワード検証が機能することを確認
        assert auth_service.verify_password(plain_password, user.password_hash), \
            "パスワード検証が失敗"

    finally:
        db.close()


def test_idm_hashing(test_db):
    """FeliCa IDmがハッシュ化されて保存されることを確認"""
    from backend.app.models.employee import Employee, EmployeeCard
    from backend.app.utils.security import CryptoUtils

    db = test_db.SessionLocal()
    try:
        # 従業員を作成
        employee = Employee(
            employee_code="IDM001",
            name="IDMテスト",
            wage_type="monthly",
            monthly_salary=300000
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)

        # カードIDmをハッシュ化
        plain_idm = "0123456789ABCDEF"
        hashed_idm = CryptoUtils.hash_idm(plain_idm)

        # カードを追加
        card = EmployeeCard(
            employee_id=employee.id,
            card_idm_hash=hashed_idm,
            card_nickname="テストカード"
        )
        db.add(card)
        db.commit()

        # IDmが平文で保存されていないことを確認
        assert card.card_idm_hash != plain_idm, "IDmが平文で保存されている"

        # SHA256ハッシュ形式であることを確認（64文字の16進数）
        assert len(card.card_idm_hash) == 64, "SHA256ハッシュの長さが不正"
        assert all(c in '0123456789abcdef' for c in card.card_idm_hash.lower()), \
            "SHA256ハッシュ形式でない"

    finally:
        db.close()


def test_jwt_token_not_stored_in_database(test_db):
    """JWTトークンがデータベースに保存されないことを確認"""
    from backend.app.models.user import User

    db = test_db.SessionLocal()
    try:
        # ユーザーモデルにトークンフィールドがないことを確認
        user_columns = [column.name for column in User.__table__.columns]

        # トークン関連のフィールドが存在しないことを確認
        dangerous_fields = ["token", "access_token", "refresh_token", "jwt"]
        for field in dangerous_fields:
            assert field not in user_columns, f"データベースに{field}フィールドが存在する"

    finally:
        db.close()


def test_sensitive_data_not_in_logs(client, auth_headers):
    """ログに機密情報が記録されないことを確認"""
    import logging
    from io import StringIO

    # ログキャプチャ
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    logger = logging.getLogger("backend")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        # 従業員を作成
        response = client.post(
            "/api/v1/admin/employees",
            json={
                "employee_code": "LOG001",
                "name": "ログテスト",
                "wage_type": "monthly",
                "monthly_salary": 300000,
            },
            headers=auth_headers
        )

        # ログ内容を取得
        log_contents = log_capture.getvalue()

        # Authorization ヘッダーの内容（JWTトークン）がログに記録されていないことを確認
        if "Authorization" in str(auth_headers):
            token = auth_headers.get("Authorization", "").replace("Bearer ", "")
            if token:
                assert token not in log_contents, "JWTトークンがログに記録されている"

    finally:
        logger.removeHandler(handler)


def test_https_enforcement_headers(client):
    """HTTPS強制ヘッダーの確認"""
    response = client.get("/")

    # Strict-Transport-Security ヘッダーの確認（HSTS）
    hsts_header = response.headers.get("Strict-Transport-Security")

    # 本番環境ではHSTSが設定されているべき
    # テスト環境では設定されていなくても許容
    if hsts_header:
        assert "max-age=" in hsts_header, "HSTSのmax-ageが設定されていない"


def test_secret_key_strength():
    """シークレットキーの強度確認"""
    from config.config import config

    # JWT秘密鍵の長さを確認
    jwt_secret = config.JWT_SECRET_KEY

    # 本番環境では十分に長い秘密鍵を使用すべき（最低32文字）
    assert len(jwt_secret) >= 32, "JWT秘密鍵が短すぎる（最低32文字必要）"

    # IDMハッシュ秘密鍵の確認
    idm_secret = config.IDM_HASH_SECRET
    assert len(idm_secret) >= 32, "IDMハッシュ秘密鍵が短すぎる"


def test_no_sensitive_data_in_error_responses(client):
    """エラーレスポンスに機密情報が含まれないことを確認"""
    # 不正なエンドポイントにアクセス
    response = client.get("/api/v1/admin/employees/99999", headers={"Authorization": "Bearer invalid_token"})

    # エラーレスポンス
    if response.status_code >= 400:
        error_text = response.text.lower()

        # データベース接続情報が漏れていないことを確認
        dangerous_keywords = [
            "password=", "database=", "host=", "user=", "postgres",
            "mysql", "connection string", "secret", "private key"
        ]

        for keyword in dangerous_keywords:
            assert keyword not in error_text, f"エラーレスポンスに機密情報が含まれている: {keyword}"


def test_hmac_verification():
    """HMAC検証機能のテスト"""
    from backend.app.utils.security import CryptoUtils

    # データとHMACを生成
    test_data = "important_data"
    hmac_value = CryptoUtils.generate_hmac(test_data)

    # HMAC検証が成功することを確認
    assert CryptoUtils.verify_hmac(test_data, hmac_value), "HMAC検証が失敗"

    # データが変更された場合、検証が失敗することを確認
    assert not CryptoUtils.verify_hmac("tampered_data", hmac_value), \
        "改ざんされたデータでHMAC検証が成功してしまう"


def test_secure_random_token_generation():
    """セキュアな乱数トークン生成のテスト"""
    from backend.app.utils.security import TokenManager

    # トークンを複数生成
    tokens = [TokenManager.generate_secure_token() for _ in range(10)]

    # すべてのトークンが異なることを確認（衝突がない）
    assert len(tokens) == len(set(tokens)), "トークンに重複がある"

    # トークンの長さが十分であることを確認
    for token in tokens:
        assert len(token) >= 32, "トークンが短すぎる"
