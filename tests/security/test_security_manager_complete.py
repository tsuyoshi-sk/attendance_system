"""
完全版SecurityManager の包括的テスト
OWASP ASVS Level 2 要件検証
"""
import pytest
import os
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

# テスト用環境変数設定（86文字以上）
os.environ["SECRET_KEY"] = "test-secret-key-86-characters-very-long-for-comprehensive-security-testing-purposes-ok"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-86-characters-very-long-for-comprehensive-security-testing-purposes"
os.environ["IDM_HASH_SECRET"] = "test-idm-hash-secret-86-characters-very-long-for-comprehensive-testing-purposes"
os.environ["ENVIRONMENT"] = "testing"

from attendance_system.security.security_manager import SecurityManager


class TestSecurityManagerComplete:
    """完全版SecurityManager のテストクラス"""

    @pytest.fixture
    def security_manager(self):
        """SecurityManager インスタンス"""
        return SecurityManager()

    def test_initialization_success(self, security_manager):
        """正常な初期化テスト"""
        assert security_manager is not None
        assert hasattr(security_manager, 'fernet')
        assert hasattr(security_manager, '_session_store')
        assert hasattr(security_manager, '_rate_limits')

    def test_security_keys_validation_pass(self, security_manager):
        """セキュリティキー検証成功テスト"""
        # 86文字のキーで初期化成功することを確認
        assert len(security_manager.config.SECRET_KEY) >= 64
        assert len(security_manager.config.JWT_SECRET_KEY) >= 64
        assert len(security_manager.config.IDM_HASH_SECRET) >= 64

    def test_security_keys_validation_fail(self):
        """セキュリティキー検証失敗テスト"""
        with patch.dict(os.environ, {"SECRET_KEY": "short_key"}):
            with pytest.raises(ValueError, match="must be at least 64 characters"):
                SecurityManager()

    def test_nfc_idm_secure_and_verify(self, security_manager):
        """NFC IDM セキュア処理・検証テスト"""
        test_idm = "0123456789ABCDEF"
        
        # セキュア処理
        secured = security_manager.secure_nfc_idm(test_idm)
        assert secured is not None
        assert isinstance(secured, str)
        assert len(secured) > 0
        
        # 検証
        assert security_manager.verify_nfc_idm(test_idm, secured) is True
        assert security_manager.verify_nfc_idm("WRONG_IDM", secured) is False

    def test_nfc_idm_validation(self, security_manager):
        """NFC IDM 入力検証テスト"""
        # 無効な入力のテスト
        with pytest.raises(ValueError):
            security_manager.secure_nfc_idm("")
        
        with pytest.raises(ValueError):
            security_manager.secure_nfc_idm("short")  # 8文字未満
        
        with pytest.raises(ValueError):
            security_manager.secure_nfc_idm("x" * 33)  # 32文字超過

    def test_password_hashing(self, security_manager):
        """パスワードハッシュ化テスト"""
        password = "SecurePassword123!"
        
        # ハッシュ化
        hashed = security_manager.hash_password(password)
        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # 平文とは異なる
        
        # 検証
        assert security_manager.verify_password(password, hashed) is True
        assert security_manager.verify_password("wrong_password", hashed) is False

    def test_password_validation(self, security_manager):
        """パスワード検証テスト"""
        with pytest.raises(ValueError, match="at least 8 characters"):
            security_manager.hash_password("short")

    def test_session_management(self, security_manager):
        """セッション管理テスト"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        
        # セッション作成
        session_id = security_manager.create_session(user_id, ip_address)
        assert session_id is not None
        assert len(session_id) > 0
        
        # セッション検証
        session = security_manager.validate_session(session_id, ip_address)
        assert session is not None
        assert session['user_id'] == user_id
        assert session['ip_address'] == ip_address
        assert 'csrf_token' in session

    def test_session_ip_validation(self, security_manager):
        """セッション IP アドレス検証テスト"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        
        session_id = security_manager.create_session(user_id, ip_address)
        
        # 異なるIPアドレスで検証（失敗することを確認）
        invalid_session = security_manager.validate_session(session_id, "192.168.1.200")
        assert invalid_session is None

    def test_rate_limiting(self, security_manager):
        """レート制限テスト"""
        client_id = "test_client"
        limit = 10
        
        # 制限内でのリクエスト
        for _ in range(limit):
            assert security_manager.check_rate_limit(client_id, limit=limit) is True
        
        # 制限を超えるリクエスト
        assert security_manager.check_rate_limit(client_id, limit=limit) is False

    def test_security_headers(self, security_manager):
        """セキュリティヘッダーテスト"""
        headers = security_manager.get_security_headers()
        
        # 必須ヘッダーの確認
        required_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
        
        for header in required_headers:
            assert header in headers
            assert headers[header] is not None
            assert len(headers[header]) > 0

    def test_concurrent_nfc_processing(self, security_manager):
        """並行NFC処理テスト"""
        test_idms = [f"TEST{i:012X}" for i in range(50)]
        
        def process_idm(idm):
            secured = security_manager.secure_nfc_idm(idm)
            return security_manager.verify_nfc_idm(idm, secured)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_idm, test_idms))
        
        assert all(results), "All concurrent NFC processing should succeed"

    def test_timing_attack_resistance(self, security_manager):
        """タイミング攻撃耐性テスト"""
        test_idm = "0123456789ABCDEF"
        secured = security_manager.secure_nfc_idm(test_idm)
        
        # 正しい検証の時間測定
        times_correct = []
        for _ in range(20):
            start = time.perf_counter()
            security_manager.verify_nfc_idm(test_idm, secured)
            times_correct.append(time.perf_counter() - start)
        
        # 間違った検証の時間測定
        times_wrong = []
        for _ in range(20):
            start = time.perf_counter()
            security_manager.verify_nfc_idm("WRONG_IDM", secured)
            times_wrong.append(time.perf_counter() - start)
        
        avg_correct = sum(times_correct) / len(times_correct)
        avg_wrong = sum(times_wrong) / len(times_wrong)
        
        # タイミング差が20%以内であることを確認（テスト環境での緩い制限）
        timing_diff = abs(avg_correct - avg_wrong) / max(avg_correct, avg_wrong)
        assert timing_diff < 0.2, f"Potential timing attack vulnerability: {timing_diff}"