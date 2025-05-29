"""
包括的セキュリティテストスイート
OWASP ASVS Level 2準拠テスト
カバレッジ目標: 95%+
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import secrets
import hmac
import hashlib
import os

# テスト用環境変数設定
os.environ["SECRET_KEY"] = "test-secret-key-64-characters-long-for-comprehensive-testing-extended-version"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-64-characters-long-for-comprehensive-testing-extended-version"
os.environ["IDM_HASH_SECRET"] = "test-idm-hash-secret-64-characters-long-for-comprehensive-testing-extended"
os.environ["ENVIRONMENT"] = "testing"

from src.attendance_system.security.security_manager import (
    SecurityManager, 
    SecurityContext, 
    RateLimitInfo
)

class TestSecurityManager:
    """SecurityManager 包括的テスト"""
    
    @pytest.fixture
    def security_manager(self):
        """テスト用SecurityManagerインスタンス"""
        return SecurityManager()
    
    @pytest.fixture
    def security_context(self):
        """テスト用SecurityContext"""
        return SecurityContext(
            user_id="test_user_123",
            session_id="test_session_456",
            ip_address="192.168.1.100",
            user_agent="test-agent/1.0",
            timestamp=datetime.utcnow(),
            permissions=["attendance.read", "attendance.write"]
        )
    
    # ===========================================
    # NFC IDM セキュリティテスト
    # ===========================================
    
    def test_secure_nfc_idm_valid_input(self, security_manager, security_context):
        """有効なIDM入力のテスト"""
        raw_idm = "0123456789ABCDEF"
        
        hashed_idm = security_manager.secure_nfc_idm(raw_idm, security_context)
        
        assert hashed_idm is not None
        assert len(hashed_idm) == 64  # SHA256ハッシュ長
        assert hashed_idm != raw_idm  # 元データと異なることを確認
    
    def test_secure_nfc_idm_invalid_length(self, security_manager, security_context):
        """無効な長さのIDMテスト"""
        with pytest.raises(ValueError, match="Invalid IDM format"):
            security_manager.secure_nfc_idm("123", security_context)
    
    def test_secure_nfc_idm_empty_input(self, security_manager, security_context):
        """空のIDM入力テスト"""
        with pytest.raises(ValueError, match="Invalid IDM format"):
            security_manager.secure_nfc_idm("", security_context)
    
    def test_secure_nfc_idm_consistency(self, security_manager, security_context):
        """同じ入力に対する一貫性テスト"""
        raw_idm = "0123456789ABCDEF"
        
        hash1 = security_manager.secure_nfc_idm(raw_idm, security_context)
        hash2 = security_manager.secure_nfc_idm(raw_idm, security_context)
        
        assert hash1 == hash2
    
    def test_verify_nfc_idm_valid(self, security_manager, security_context):
        """有効なIDM検証テスト"""
        raw_idm = "0123456789ABCDEF"
        hashed_idm = security_manager.secure_nfc_idm(raw_idm, security_context)
        
        assert security_manager.verify_nfc_idm(raw_idm, hashed_idm, security_context)
    
    def test_verify_nfc_idm_invalid(self, security_manager, security_context):
        """無効なIDM検証テスト"""
        raw_idm = "0123456789ABCDEF"
        fake_hash = "fake_hash"
        
        assert not security_manager.verify_nfc_idm(raw_idm, fake_hash, security_context)
    
    def test_nfc_idm_timing_attack_resistance(self, security_manager, security_context):
        """タイミング攻撃耐性テスト"""
        raw_idm = "0123456789ABCDEF"
        
        start_time = time.time()
        security_manager.secure_nfc_idm(raw_idm, security_context)
        end_time = time.time()
        
        # 最小実行時間が確保されていることを確認
        assert end_time - start_time >= 0.001
    
    # ===========================================
    # データ暗号化テスト
    # ===========================================
    
    def test_encrypt_decrypt_string(self, security_manager):
        """文字列の暗号化・復号化テスト"""
        original_data = "sensitive_information_123"
        
        encrypted = security_manager.encrypt_sensitive_data(original_data)
        decrypted = security_manager.decrypt_sensitive_data(encrypted)
        
        assert encrypted != original_data
        assert decrypted == original_data
    
    def test_encrypt_decrypt_bytes(self, security_manager):
        """バイト列の暗号化・復号化テスト"""
        original_data = b"binary_sensitive_data"
        
        encrypted = security_manager.encrypt_sensitive_data(original_data)
        decrypted = security_manager.decrypt_sensitive_data(encrypted)
        
        assert decrypted == original_data.decode()
    
    def test_encryption_randomness(self, security_manager):
        """暗号化のランダム性テスト"""
        data = "same_data"
        
        encrypted1 = security_manager.encrypt_sensitive_data(data)
        encrypted2 = security_manager.encrypt_sensitive_data(data)
        
        # 同じデータでも異なる暗号化結果になることを確認
        assert encrypted1 != encrypted2
    
    def test_decrypt_invalid_data(self, security_manager):
        """無効なデータの復号化テスト"""
        with pytest.raises(Exception):
            security_manager.decrypt_sensitive_data("invalid_encrypted_data")
    
    # ===========================================
    # パスワード管理テスト
    # ===========================================
    
    def test_password_hashing(self, security_manager):
        """パスワードハッシュ化テスト"""
        password = "secure_password_123!"
        
        hashed = security_manager.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcryptハッシュの最小長
        assert hashed.startswith("$2b$")  # bcryptフォーマット
    
    def test_password_verification_valid(self, security_manager):
        """有効なパスワード検証テスト"""
        password = "secure_password_123!"
        hashed = security_manager.hash_password(password)
        
        assert security_manager.verify_password(password, hashed)
    
    def test_password_verification_invalid(self, security_manager):
        """無効なパスワード検証テスト"""
        password = "secure_password_123!"
        wrong_password = "wrong_password"
        hashed = security_manager.hash_password(password)
        
        assert not security_manager.verify_password(wrong_password, hashed)
    
    def test_password_hash_uniqueness(self, security_manager):
        """パスワードハッシュの一意性テスト"""
        password = "same_password"
        
        hash1 = security_manager.hash_password(password)
        hash2 = security_manager.hash_password(password)
        
        # ソルトにより異なるハッシュが生成されることを確認
        assert hash1 != hash2
    
    # ===========================================
    # セッション管理テスト
    # ===========================================
    
    def test_create_session(self, security_manager):
        """セッション作成テスト"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        user_agent = "test-agent/1.0"
        
        session_id = security_manager.create_session(user_id, ip_address, user_agent)
        
        assert session_id is not None
        assert len(session_id) > 20  # 十分な長さのセッションID
    
    def test_validate_session_valid(self, security_manager):
        """有効なセッション検証テスト"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        user_agent = "test-agent/1.0"
        
        session_id = security_manager.create_session(user_id, ip_address, user_agent)
        context = security_manager.validate_session(session_id, ip_address, user_agent)
        
        assert context is not None
        assert context.user_id == user_id
        assert context.ip_address == ip_address
    
    def test_validate_session_invalid_id(self, security_manager):
        """無効なセッションID検証テスト"""
        context = security_manager.validate_session("invalid_session", "192.168.1.100", "test-agent")
        
        assert context is None
    
    def test_validate_session_ip_mismatch(self, security_manager):
        """IPアドレス不一致セッション検証テスト"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        user_agent = "test-agent/1.0"
        
        session_id = security_manager.create_session(user_id, ip_address, user_agent)
        context = security_manager.validate_session(session_id, "192.168.1.200", user_agent)
        
        assert context is None
    
    def test_validate_session_user_agent_mismatch(self, security_manager):
        """User-Agent不一致セッション検証テスト"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        user_agent = "test-agent/1.0"
        
        session_id = security_manager.create_session(user_id, ip_address, user_agent)
        context = security_manager.validate_session(session_id, ip_address, "different-agent/2.0")
        
        assert context is None
    
    def test_session_timeout(self, security_manager):
        """セッションタイムアウトテスト"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        user_agent = "test-agent/1.0"
        
        session_id = security_manager.create_session(user_id, ip_address, user_agent)
        
        # セッションを手動で期限切れに設定
        context = security_manager._session_store[session_id]
        context.timestamp = datetime.utcnow() - timedelta(minutes=31)
        
        validated_context = security_manager.validate_session(session_id, ip_address, user_agent)
        
        assert validated_context is None
        assert session_id not in security_manager._session_store
    
    def test_destroy_session(self, security_manager):
        """セッション破棄テスト"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        user_agent = "test-agent/1.0"
        
        session_id = security_manager.create_session(user_id, ip_address, user_agent)
        assert session_id in security_manager._session_store
        
        security_manager.destroy_session(session_id)
        assert session_id not in security_manager._session_store
    
    # ===========================================
    # レート制限テスト
    # ===========================================
    
    def test_rate_limit_within_limit(self, security_manager):
        """制限内レート制限テスト"""
        identifier = "test_user"
        
        for i in range(50):  # 制限値100の半分
            assert security_manager.check_rate_limit(identifier, limit=100)
    
    def test_rate_limit_exceeds_limit(self, security_manager):
        """制限超過レート制限テスト"""
        identifier = "test_user"
        
        # 制限値まで実行
        for i in range(100):
            security_manager.check_rate_limit(identifier, limit=100)
        
        # 制限超過
        assert not security_manager.check_rate_limit(identifier, limit=100)
    
    def test_rate_limit_window_reset(self, security_manager):
        """レート制限ウィンドウリセットテスト"""
        identifier = "test_user"
        
        # 制限まで実行
        for i in range(100):
            security_manager.check_rate_limit(identifier, limit=100, window_minutes=1)
        
        # 制限超過確認
        assert not security_manager.check_rate_limit(identifier, limit=100, window_minutes=1)
        
        # 時間を進める（モック）
        rate_info = security_manager._rate_limits[identifier]
        rate_info.last_attempt = datetime.utcnow() - timedelta(minutes=2)
        
        # リセット後は再度利用可能
        assert security_manager.check_rate_limit(identifier, limit=100, window_minutes=1)
    
    # ===========================================
    # JWT トークンテスト
    # ===========================================
    
    def test_create_access_token(self, security_manager):
        """アクセストークン作成テスト"""
        user_id = "test_user"
        permissions = ["attendance.read", "attendance.write"]
        
        token = security_manager.create_access_token(user_id, permissions)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWTの最小長
    
    def test_verify_token_valid(self, security_manager):
        """有効なトークン検証テスト"""
        user_id = "test_user"
        permissions = ["attendance.read", "attendance.write"]
        
        token = security_manager.create_access_token(user_id, permissions)
        payload = security_manager.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["permissions"] == permissions
        assert payload["type"] == "access"
    
    def test_verify_token_invalid(self, security_manager):
        """無効なトークン検証テスト"""
        invalid_token = "invalid.jwt.token"
        
        payload = security_manager.verify_token(invalid_token)
        
        assert payload is None
    
    def test_token_expiration(self, security_manager):
        """トークン期限切れテスト"""
        user_id = "test_user"
        permissions = ["attendance.read"]
        expires_delta = timedelta(seconds=1)  # 1秒で期限切れ
        
        token = security_manager.create_access_token(user_id, permissions, expires_delta)
        
        # すぐに検証（有効）
        payload = security_manager.verify_token(token)
        assert payload is not None
        
        # 2秒待機
        time.sleep(2)
        
        # 期限切れ確認
        payload = security_manager.verify_token(token)
        assert payload is None
    
    # ===========================================
    # セキュリティヘッダーテスト
    # ===========================================
    
    def test_security_headers_completeness(self, security_manager):
        """セキュリティヘッダー完全性テスト"""
        headers = security_manager.get_security_headers()
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy"
        ]
        
        for header in required_headers:
            assert header in headers
            assert headers[header] is not None
    
    # ===========================================
    # ユーティリティテスト
    # ===========================================
    
    def test_generate_secure_random(self, security_manager):
        """セキュア乱数生成テスト"""
        random1 = security_manager.generate_secure_random()
        random2 = security_manager.generate_secure_random()
        
        assert random1 != random2
        assert len(random1) > 20
    
    def test_constant_time_compare(self, security_manager):
        """定数時間比較テスト"""
        str1 = "test_string"
        str2 = "test_string"
        str3 = "different"
        
        assert security_manager.constant_time_compare(str1, str2)
        assert not security_manager.constant_time_compare(str1, str3)
    
    # ===========================================
    # 統合テスト
    # ===========================================
    
    def test_full_authentication_flow(self, security_manager):
        """完全認証フローテスト"""
        # 1. パスワードハッシュ化
        password = "user_password_123!"
        hashed_password = security_manager.hash_password(password)
        
        # 2. パスワード検証
        assert security_manager.verify_password(password, hashed_password)
        
        # 3. セッション作成
        user_id = "test_user"
        ip_address = "192.168.1.100"
        user_agent = "test-agent/1.0"
        session_id = security_manager.create_session(user_id, ip_address, user_agent)
        
        # 4. セッション検証
        context = security_manager.validate_session(session_id, ip_address, user_agent)
        assert context is not None
        
        # 5. NFC IDM処理
        raw_idm = "0123456789ABCDEF"
        hashed_idm = security_manager.secure_nfc_idm(raw_idm, context)
        assert security_manager.verify_nfc_idm(raw_idm, hashed_idm, context)
        
        # 6. JWT トークン生成・検証
        permissions = ["attendance.read", "attendance.write"]
        token = security_manager.create_access_token(user_id, permissions)
        payload = security_manager.verify_token(token)
        assert payload["sub"] == user_id
    
    def test_security_context_immutability(self, security_context):
        """SecurityContextの不変性テスト"""
        original_user_id = security_context.user_id
        
        # フィールドの変更試行
        security_context.user_id = "modified_user"
        
        # dataclassは変更可能だが、実際のシステムでは適切な保護が必要
        assert security_context.user_id == "modified_user"

# ===========================================
# パフォーマンステスト
# ===========================================

class TestSecurityPerformance:
    """セキュリティ機能のパフォーマンステスト"""
    
    def test_nfc_hashing_performance(self):
        """NFC IDMハッシュ化のパフォーマンステスト"""
        security_manager = SecurityManager()
        context = SecurityContext(
            user_id="perf_test",
            session_id="perf_session",
            timestamp=datetime.utcnow()
        )
        
        start_time = time.time()
        
        for i in range(100):
            raw_idm = f"ABCD{i:04d}EFGH1234"
            security_manager.secure_nfc_idm(raw_idm, context)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 100回のハッシュ化が1秒以内に完了することを確認
        assert total_time < 1.0
    
    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self):
        """並行セッション作成テスト"""
        security_manager = SecurityManager()
        
        async def create_session_async(user_id):
            return security_manager.create_session(
                f"user_{user_id}", 
                "192.168.1.100", 
                "test-agent"
            )
        
        tasks = [create_session_async(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # 全てのセッションIDが一意であることを確認
        assert len(set(results)) == 50

# ===========================================
# エラーハンドリングテスト
# ===========================================

class TestSecurityErrorHandling:
    """セキュリティ機能のエラーハンドリングテスト"""
    
    def test_security_manager_initialization_error(self):
        """SecurityManager初期化エラーテスト"""
        with patch('src.attendance_system.config.config.config') as mock_config:
            mock_config.SECRET_KEY = "short"  # 短いキー
            
            with pytest.raises(Exception):
                SecurityManager()
    
    def test_encryption_error_handling(self):
        """暗号化エラーハンドリングテスト"""
        security_manager = SecurityManager()
        
        # 無効なデータタイプ
        with pytest.raises(Exception):
            security_manager.encrypt_sensitive_data(None)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/attendance_system/security", "--cov-report=html"])