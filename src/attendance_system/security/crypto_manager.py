"""
OWASP ASVS Level 2準拠 暗号化マネージャー
"""
import os
import secrets
import hashlib
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging

from attendance_system.config.config import settings


class CryptographicManager:
    """
    OWASP ASVS Level 2準拠の暗号化マネージャー
    V6.2: 暗号化要件に完全対応
    """
    
    def __init__(self):
        self.config = settings
        self._logger = logging.getLogger(__name__)
        self._init_crypto_keys()
    
    def _init_crypto_keys(self) -> None:
        """V6.2.1: 暗号化キーの初期化"""
        # メインの暗号化キー
        secret_key = getattr(self.config, 'SECRET_KEY', '').encode()
        salt = b'attendance_system_salt_2024'  # 固定ソルト（プロダクションでは環境変数）
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # NIST推奨
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key))
        self.fernet = Fernet(key)
        
        # IDM専用暗号化キー
        idm_secret = getattr(self.config, 'IDM_HASH_SECRET', '').encode()
        idm_kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'idm_encryption_salt_2024',
            iterations=100000,
        )
        idm_key = base64.urlsafe_b64encode(idm_kdf.derive(idm_secret))
        self.idm_fernet = Fernet(idm_key)
        
        self._logger.info("Cryptographic keys initialized securely")
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """V6.2.2: 機密データの暗号化"""
        if not isinstance(data, str):
            raise ValueError("Data must be string")
        
        encrypted = self.fernet.encrypt(data.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted).decode('ascii')
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """V6.2.3: 機密データの復号化"""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode('ascii'))
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            self._logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
    
    def encrypt_idm_data(self, idm: str) -> str:
        """V6.2.4: IDM専用暗号化"""
        if not idm or len(idm) < 8:
            raise ValueError("Invalid IDM format")
        
        encrypted = self.idm_fernet.encrypt(idm.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted).decode('ascii')
    
    def decrypt_idm_data(self, encrypted_idm: str) -> str:
        """V6.2.5: IDM専用復号化"""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_idm.encode('ascii'))
            decrypted = self.idm_fernet.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            self._logger.error(f"IDM decryption failed: {e}")
            raise ValueError("Failed to decrypt IDM data")
    
    def generate_secure_token(self, length: int = 32) -> str:
        """V6.3.1: セキュアなトークン生成"""
        return secrets.token_urlsafe(length)
    
    def generate_csrf_token(self) -> str:
        """V4.2.2: CSRF トークン生成"""
        return secrets.token_urlsafe(32)


# グローバルインスタンス
crypto_manager = CryptographicManager()