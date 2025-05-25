"""
セキュリティ機能テスト

セキュリティユーティリティの包括的なテストケース
"""

import pytest
from datetime import datetime, timedelta
import time
import hashlib

from backend.app.utils.security import (
    InputSanitizer,
    RateLimiter,
    TokenManager,
    CryptoUtils,
    SecurityError,
    validate_employee_id,
    validate_punch_type,
    validate_datetime
)


class TestInputSanitizer:
    """入力サニタイズテストクラス"""
    
    def test_sanitize_normal_string(self):
        """通常の文字列サニタイズのテスト"""
        normal_input = "これは普通のテキストです"
        result = InputSanitizer.sanitize_string(normal_input)
        assert result == "これは普通のテキストです"
    
    def test_sanitize_sql_injection(self):
        """SQLインジェクション対策のテスト"""
        # UNION攻撃
        with pytest.raises(SecurityError):
            InputSanitizer.sanitize_string("' UNION SELECT * FROM users--")
        
        # OR攻撃
        with pytest.raises(SecurityError):
            InputSanitizer.sanitize_string("' OR 1=1--")
        
        # DROP文
        with pytest.raises(SecurityError):
            InputSanitizer.sanitize_string("'; DROP TABLE employees;--")
    
    def test_sanitize_xss(self):
        """XSS対策のテスト"""
        # スクリプトタグ
        with pytest.raises(SecurityError):
            InputSanitizer.sanitize_string("<script>alert('XSS')</script>")
        
        # イベントハンドラ
        with pytest.raises(SecurityError):
            InputSanitizer.sanitize_string('<img src="x" onerror="alert(1)">')
        
        # JavaScriptプロトコル
        with pytest.raises(SecurityError):
            InputSanitizer.sanitize_string('<a href="javascript:alert(1)">click</a>')
    
    def test_sanitize_length_limit(self):
        """文字列長制限のテスト"""
        long_string = "a" * 2000
        result = InputSanitizer.sanitize_string(long_string, max_length=100)
        assert len(result) == 100
    
    def test_sanitize_basic_escape(self):
        """基本的なエスケープのテスト"""
        input_str = "O'Brien said: <Hello>"
        result = InputSanitizer.sanitize_string(input_str)
        assert "O''Brien" in result  # SQLエスケープ
        assert "&lt;Hello&gt;" in result  # HTMLエスケープ
    
    def test_sanitize_dict(self):
        """辞書データのサニタイズテスト"""
        input_dict = {
            "name": "テスト太郎",
            "note": "<b>太字</b>のテキスト",
            "nested": {
                "value": "ネストした値"
            },
            "list": ["項目1", "項目2"]
        }
        
        result = InputSanitizer.sanitize_dict(input_dict)
        
        assert result["name"] == "テスト太郎"
        assert "&lt;b&gt;" in result["note"]
        assert result["nested"]["value"] == "ネストした値"
        assert len(result["list"]) == 2


class TestRateLimiter:
    """レート制限テストクラス"""
    
    def test_basic_rate_limiting(self):
        """基本的なレート制限のテスト"""
        limiter = RateLimiter()
        test_key = "test_ip_1"
        
        # 最初の10回は成功
        for i in range(10):
            assert limiter.check_rate_limit(test_key, max_attempts=10, window_seconds=60)
        
        # 11回目は失敗
        assert not limiter.check_rate_limit(test_key, max_attempts=10, window_seconds=60)
    
    def test_window_expiration(self):
        """時間ウィンドウ期限切れのテスト"""
        limiter = RateLimiter()
        test_key = "test_ip_2"
        
        # 制限に達する
        for i in range(5):
            limiter.check_rate_limit(test_key, max_attempts=5, window_seconds=1)
        
        # 制限超過
        assert not limiter.check_rate_limit(test_key, max_attempts=5, window_seconds=1)
        
        # 1秒後は再度許可される
        time.sleep(1.1)
        assert limiter.check_rate_limit(test_key, max_attempts=5, window_seconds=1)
    
    def test_block_duration(self):
        """ブロック期間のテスト"""
        limiter = RateLimiter()
        test_key = "test_ip_3"
        
        # 制限に達してブロック
        for i in range(3):
            limiter.check_rate_limit(test_key, max_attempts=3, block_duration_seconds=1)
        
        # ブロック中
        assert not limiter.check_rate_limit(test_key, max_attempts=3)
        
        # 1秒後はブロック解除
        time.sleep(1.1)
        assert limiter.check_rate_limit(test_key, max_attempts=3)
    
    def test_cleanup_old_entries(self):
        """古いエントリのクリーンアップテスト"""
        limiter = RateLimiter()
        
        # エントリを作成
        limiter.check_rate_limit("old_key", max_attempts=1)
        
        # 古いエントリをクリーンアップ
        limiter.cleanup_old_entries(older_than_hours=0)  # 即座にクリーンアップ
        
        # 新しいキーとして扱われる
        assert limiter.check_rate_limit("old_key", max_attempts=1)


class TestTokenManager:
    """トークン管理テストクラス"""
    
    def test_generate_secure_token(self):
        """セキュアトークン生成のテスト"""
        token1 = TokenManager.generate_secure_token()
        token2 = TokenManager.generate_secure_token()
        
        # 異なるトークンが生成される
        assert token1 != token2
        
        # 適切な長さ
        assert len(token1) > 40  # base64エンコードされた32バイト
    
    def test_hash_and_verify_token(self):
        """トークンハッシュ化と検証のテスト"""
        token = "test_token_12345"
        hashed = TokenManager.hash_token(token)
        
        # ハッシュ化確認
        assert len(hashed) == 64  # SHA-256
        assert hashed != token
        
        # 検証成功
        assert TokenManager.verify_token(token, hashed)
        
        # 検証失敗
        assert not TokenManager.verify_token("wrong_token", hashed)
    
    def test_token_with_custom_salt(self):
        """カスタムソルト付きトークンのテスト"""
        token = "test_token"
        salt1 = "salt1"
        salt2 = "salt2"
        
        hash1 = TokenManager.hash_token(token, salt1)
        hash2 = TokenManager.hash_token(token, salt2)
        
        # 異なるソルトは異なるハッシュ
        assert hash1 != hash2
        
        # 正しいソルトでのみ検証成功
        assert TokenManager.verify_token(token, hash1, salt1)
        assert not TokenManager.verify_token(token, hash1, salt2)


class TestCryptoUtils:
    """暗号化ユーティリティテストクラス"""
    
    def test_hash_idm(self):
        """IDmハッシュ化のテスト"""
        idm = "0123456789ABCDEF"
        hash1 = CryptoUtils.hash_idm(idm)
        hash2 = CryptoUtils.hash_idm(idm)
        
        # 同じIDmは同じハッシュ
        assert hash1 == hash2
        assert len(hash1) == 64
        
        # 異なるIDmは異なるハッシュ
        hash3 = CryptoUtils.hash_idm("FEDCBA9876543210")
        assert hash1 != hash3
    
    def test_hmac_generation_and_verification(self):
        """HMAC生成と検証のテスト"""
        data = "重要なデータ"
        hmac_value = CryptoUtils.generate_hmac(data)
        
        # HMAC検証成功
        assert CryptoUtils.verify_hmac(data, hmac_value)
        
        # 改ざんされたデータでは検証失敗
        assert not CryptoUtils.verify_hmac("改ざんされたデータ", hmac_value)
    
    def test_hmac_with_custom_key(self):
        """カスタムキー付きHMACのテスト"""
        data = "test data"
        key = "custom_secret_key"
        
        hmac_value = CryptoUtils.generate_hmac(data, key)
        
        # 正しいキーでのみ検証成功
        assert CryptoUtils.verify_hmac(data, hmac_value, key)
        assert not CryptoUtils.verify_hmac(data, hmac_value, "wrong_key")


class TestValidationFunctions:
    """検証関数テストクラス"""
    
    def test_validate_employee_id(self):
        """従業員ID検証のテスト"""
        # 正常な値
        assert validate_employee_id(123) == 123
        assert validate_employee_id("456") == 456
        
        # 異常な値
        with pytest.raises(ValueError):
            validate_employee_id(0)  # 0以下
        
        with pytest.raises(ValueError):
            validate_employee_id(1000000)  # 大きすぎる
        
        with pytest.raises(ValueError):
            validate_employee_id("abc")  # 数値でない
        
        with pytest.raises(ValueError):
            validate_employee_id(None)  # None
    
    def test_validate_punch_type(self):
        """打刻タイプ検証のテスト"""
        # 正常な値
        assert validate_punch_type("IN") == "IN"
        assert validate_punch_type("out") == "OUT"  # 小文字も可
        assert validate_punch_type("OUTSIDE") == "OUTSIDE"
        assert validate_punch_type("return") == "RETURN"
        
        # 異常な値
        with pytest.raises(ValueError):
            validate_punch_type("INVALID")
        
        with pytest.raises(ValueError):
            validate_punch_type("")
    
    def test_validate_datetime(self):
        """日時検証のテスト"""
        # 正常な値
        now = datetime.now()
        
        # ISO形式
        iso_string = now.isoformat()
        result = validate_datetime(iso_string)
        assert isinstance(result, datetime)
        
        # 標準形式
        standard_string = now.strftime("%Y-%m-%d %H:%M:%S")
        result = validate_datetime(standard_string)
        assert isinstance(result, datetime)
        
        # 未来の日時（5分以内はOK）
        future_ok = (now + timedelta(minutes=4)).isoformat()
        validate_datetime(future_ok)  # エラーなし
        
        # 異常な値
        # 遠い未来
        with pytest.raises(ValueError, match="未来の日時"):
            future_ng = (now + timedelta(minutes=10)).isoformat()
            validate_datetime(future_ng)
        
        # 古すぎる日時
        with pytest.raises(ValueError, match="古すぎる日時"):
            old_date = (now - timedelta(days=400)).isoformat()
            validate_datetime(old_date)
        
        # 不正な形式
        with pytest.raises(ValueError):
            validate_datetime("invalid date")