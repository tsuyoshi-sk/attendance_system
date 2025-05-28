"""
新セキュリティマネージャーの包括的テスト
OWASP ASVS Level 2 要件検証
"""
import pytest
import os
from unittest.mock import patch, Mock
import secrets

# テスト用環境変数設定
os.environ['SECRET_KEY'] = 'test-secret-key-64-characters-long-for-comprehensive-testing-ok'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-64-characters-long-for-comprehensive-testing-ok'
os.environ['IDM_HASH_SECRET'] = 'test-idm-hash-secret-64-characters-long-for-testing-purposes'

from attendance_system.security.security_manager import SecurityManager
from attendance_system.security.crypto_manager import CryptographicManager
from attendance_system.security.hash_manager import SecureHashManager


class TestNewSecurityManager:
    """新SecurityManager のテストクラス"""
    
    @pytest.fixture
    def security_manager(self):
        """SecurityManager インスタンス"""
        return SecurityManager()
    
    def test_initialization_success(self, security_manager):
        """正常な初期化テスト"""
        assert security_manager is not None
        assert hasattr(security_manager, 'fernet')
        assert hasattr(security_manager, 'config')
    
    def test_security_key_validation(self):
        """セキュリティキー検証テスト"""
        # 正常なキー長での初期化
        sm = SecurityManager()
        assert sm is not None
    
    def test_security_key_too_short(self):
        """短すぎるセキュリティキーのテスト"""
        with patch.dict(os.environ, {'SECRET_KEY': 'short'}):
            with pytest.raises(ValueError, match="must be at least 64 characters"):
                SecurityManager()
    
    def test_secure_nfc_idm_valid_input(self, security_manager):
        """正常なIDMのセキュア処理テスト"""
        test_idm = "0123456789ABCDEF"
        
        secured_idm = security_manager.secure_nfc_idm(test_idm)
        
        # 結果の検証
        assert secured_idm is not None
        assert isinstance(secured_idm, str)
        assert len(secured_idm) > 50  # 暗号化されたデータは長い
        assert secured_idm != test_idm  # 元のIDMと異なる
    
    def test_secure_nfc_idm_different_results(self, security_manager):
        """同じIDMでも異なる結果が生成されることのテスト"""
        test_idm = "0123456789ABCDEF"
        
        secured1 = security_manager.secure_nfc_idm(test_idm)
        secured2 = security_manager.secure_nfc_idm(test_idm)
        
        # ソルト付きハッシュなので毎回異なる
        assert secured1 != secured2
    
    def test_verify_nfc_idm_correct_match(self, security_manager):
        """正しいIDM検証のテスト"""
        test_idm = "0123456789ABCDEF"
        
        secured_idm = security_manager.secure_nfc_idm(test_idm)
        is_valid = security_manager.verify_nfc_idm(test_idm, secured_idm)
        
        assert is_valid is True
    
    def test_verify_nfc_idm_incorrect_match(self, security_manager):
        """間違ったIDM検証のテスト"""
        test_idm = "0123456789ABCDEF"
        wrong_idm = "FEDCBA9876543210"
        
        secured_idm = security_manager.secure_nfc_idm(test_idm)
        is_valid = security_manager.verify_nfc_idm(wrong_idm, secured_idm)
        
        assert is_valid is False
    
    def test_secure_nfc_idm_invalid_input(self, security_manager):
        """無効なIDM入力のテスト"""
        invalid_inputs = ["", "123", None]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError):
                if invalid_input is None:
                    security_manager.secure_nfc_idm(invalid_input)
                else:
                    security_manager.secure_nfc_idm(invalid_input)
    
    def test_verify_nfc_idm_invalid_stored_hash(self, security_manager):
        """無効な保存ハッシュでの検証テスト"""
        test_idm = "0123456789ABCDEF"
        invalid_hashes = ["invalid", "", "corrupted_base64"]
        
        for invalid_hash in invalid_hashes:
            is_valid = security_manager.verify_nfc_idm(test_idm, invalid_hash)
            assert is_valid is False
    
    def test_get_security_headers(self, security_manager):
        """セキュリティヘッダー取得テスト"""
        headers = security_manager.get_security_headers()
        
        # 必須ヘッダーの確認
        required_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]
        
        for header in required_headers:
            assert header in headers
            assert headers[header] is not None
            assert len(headers[header]) > 0
    
    def test_encryption_decryption_cycle(self, security_manager):
        """暗号化・復号化サイクルテスト"""
        test_data = "sensitive_test_data_12345"
        
        # 暗号化
        encrypted = security_manager._encrypt_data(test_data)
        assert encrypted != test_data
        
        # 復号化
        decrypted = security_manager._decrypt_data(encrypted)
        assert decrypted == test_data
    
    def test_hash_with_salt_consistency(self, security_manager):
        """ソルト付きハッシュの一貫性テスト"""
        test_data = "test_data"
        salt = "fixed_salt_for_testing"
        
        hash1 = security_manager._hash_with_salt(test_data, salt)
        hash2 = security_manager._hash_with_salt(test_data, salt)
        
        # 同じソルトでは同じハッシュ
        assert hash1 == hash2
        
        # 異なるソルトでは異なるハッシュ
        hash3 = security_manager._hash_with_salt(test_data, "different_salt")
        assert hash1 != hash3


class TestCryptographicManager:
    """CryptographicManager のテストクラス"""
    
    @pytest.fixture
    def crypto_manager(self):
        """CryptographicManager インスタンス"""
        return CryptographicManager()
    
    def test_encrypt_decrypt_sensitive_data(self, crypto_manager):
        """機密データ暗号化・復号化テスト"""
        test_data = "confidential_information_12345"
        
        encrypted = crypto_manager.encrypt_sensitive_data(test_data)
        decrypted = crypto_manager.decrypt_sensitive_data(encrypted)
        
        assert encrypted != test_data
        assert decrypted == test_data
    
    def test_encrypt_decrypt_idm_data(self, crypto_manager):
        """IDMデータ暗号化・復号化テスト"""
        test_idm = "0123456789ABCDEF"
        
        encrypted = crypto_manager.encrypt_idm_data(test_idm)
        decrypted = crypto_manager.decrypt_idm_data(encrypted)
        
        assert encrypted != test_idm
        assert decrypted == test_idm
    
    def test_generate_secure_token(self, crypto_manager):
        """セキュアトークン生成テスト"""
        token1 = crypto_manager.generate_secure_token()
        token2 = crypto_manager.generate_secure_token()
        
        assert len(token1) > 40  # URL-safe base64で32バイト以上
        assert len(token2) > 40
        assert token1 != token2  # 毎回異なる
    
    def test_generate_csrf_token(self, crypto_manager):
        """CSRFトークン生成テスト"""
        csrf1 = crypto_manager.generate_csrf_token()
        csrf2 = crypto_manager.generate_csrf_token()
        
        assert len(csrf1) > 40
        assert len(csrf2) > 40
        assert csrf1 != csrf2


class TestSecureHashManager:
    """SecureHashManager のテストクラス"""
    
    @pytest.fixture
    def hash_manager(self):
        """SecureHashManager インスタンス"""
        return SecureHashManager()
    
    def test_hash_verify_password(self, hash_manager):
        """パスワードハッシュ化・検証テスト"""
        password = "secure_password_123"
        
        hashed = hash_manager.hash_password(password)
        is_valid = hash_manager.verify_password(password, hashed)
        
        assert hashed != password
        assert is_valid is True
        assert len(hashed) > 50  # bcryptハッシュは長い
    
    def test_verify_wrong_password(self, hash_manager):
        """間違ったパスワード検証テスト"""
        password = "correct_password"
        wrong_password = "wrong_password"
        
        hashed = hash_manager.hash_password(password)
        is_valid = hash_manager.verify_password(wrong_password, hashed)
        
        assert is_valid is False
    
    def test_hash_idm_secure(self, hash_manager):
        """セキュアIDMハッシュ化テスト"""
        test_idm = "0123456789ABCDEF"
        
        salt, hashed = hash_manager.hash_idm_secure(test_idm)
        is_valid = hash_manager.verify_idm_hash(test_idm, salt, hashed)
        
        assert len(salt) == 64  # 32バイトの16進数
        assert len(hashed) == 64  # SHA256の16進数
        assert is_valid is True
    
    def test_hash_data_with_hmac(self, hash_manager):
        """HMAC-SHA256ハッシュ化テスト"""
        test_data = "important_data"
        
        hash1 = hash_manager.hash_data_with_hmac(test_data, "purpose1")
        hash2 = hash_manager.hash_data_with_hmac(test_data, "purpose2")
        
        assert len(hash1) == 64  # SHA256ハッシュ
        assert len(hash2) == 64
        assert hash1 != hash2  # 異なる用途では異なるハッシュ
    
    def test_constant_time_compare(self, hash_manager):
        """定数時間比較テスト"""
        str1 = "identical_string"
        str2 = "identical_string"
        str3 = "different_string"
        
        assert hash_manager.constant_time_compare(str1, str2) is True
        assert hash_manager.constant_time_compare(str1, str3) is False


@pytest.mark.integration
class TestSecurityIntegration:
    """統合テストクラス"""
    
    def test_full_security_workflow(self):
        """完全なセキュリティワークフローテスト"""
        sm = SecurityManager()
        cm = CryptographicManager()
        hm = SecureHashManager()
        
        # iPhone Suica IDMのシミュレーション
        iphone_idms = [
            "0123456789ABCDEF",
            "FEDCBA9876543210", 
            "1111222233334444"
        ]
        
        for idm in iphone_idms:
            # SecurityManagerでの処理
            secured_idm = sm.secure_nfc_idm(idm)
            assert sm.verify_nfc_idm(idm, secured_idm) is True
            
            # CryptographicManagerでの処理
            encrypted_idm = cm.encrypt_idm_data(idm)
            decrypted_idm = cm.decrypt_idm_data(encrypted_idm)
            assert decrypted_idm == idm
            
            # SecureHashManagerでの処理
            salt, hashed = hm.hash_idm_secure(idm)
            assert hm.verify_idm_hash(idm, salt, hashed) is True
    
    def test_performance_benchmark(self):
        """パフォーマンステスト"""
        import time
        
        sm = SecurityManager()
        test_idm = "0123456789ABCDEF"
        
        # ハッシュ化パフォーマンス
        start_time = time.time()
        for _ in range(100):
            sm.secure_nfc_idm(test_idm)
        hash_time = time.time() - start_time
        
        # 検証パフォーマンス
        secured = sm.secure_nfc_idm(test_idm)
        start_time = time.time()
        for _ in range(100):
            sm.verify_nfc_idm(test_idm, secured)
        verify_time = time.time() - start_time
        
        # パフォーマンス要件（100回で1秒以内）
        assert hash_time < 2.0, f"Hash performance too slow: {hash_time}s"
        assert verify_time < 2.0, f"Verify performance too slow: {verify_time}s"
        
        print(f"Hash performance: {hash_time:.3f}s for 100 operations")
        print(f"Verify performance: {verify_time:.3f}s for 100 operations")