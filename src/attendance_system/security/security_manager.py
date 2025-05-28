"""
OWASP ASVS v4.0.3 Level 2 準拠
統合セキュリティマネージャー
"""
import os
import hmac
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import base64

from attendance_system.config.config import settings


class SecurityManager:
    """
    統合セキュリティマネージャー
    OWASP ASVS Level 2 完全準拠
    """

    def __init__(self):
        self.config = settings
        self._logger = logging.getLogger(__name__)

        # セキュリティキーの検証
        self._validate_security_keys()

        # 暗号化キーの初期化
        self._init_encryption()

    def _validate_security_keys(self) -> None:
        """V2.1.1: セキュリティキーの強度検証"""
        secret_key = getattr(self.config, "SECRET_KEY", "")
        jwt_key = getattr(self.config, "JWT_SECRET_KEY", "")
        idm_secret = getattr(self.config, "IDM_HASH_SECRET", "")

        if len(secret_key) < 64:
            raise ValueError(
                "SECRET_KEY must be at least 64 characters for ASVS Level 2"
            )
        if len(jwt_key) < 64:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 64 characters for ASVS Level 2"
            )
        if len(idm_secret) < 64:
            raise ValueError(
                "IDM_HASH_SECRET must be at least 64 characters for ASVS Level 2"
            )

        self._logger.info("Security keys validation passed")

    def _init_encryption(self) -> None:
        """V6.2.1: 暗号化システムの初期化"""
        # 暗号化キーの生成（デフォルト）
        encryption_seed = getattr(self.config, "SECRET_KEY", "")[:32]
        key = base64.urlsafe_b64encode(encryption_seed.encode()[:32].ljust(32, b"\0"))
        self.fernet = Fernet(key)

        self._logger.info("Encryption system initialized")

    def secure_nfc_idm(self, idm: str) -> str:
        """
        V2.1.1: NFC IDMの安全な処理
        iPhone Suica IDMのハッシュ化と暗号化
        """
        if not idm or len(idm) < 8:
            raise ValueError("Invalid IDM format")

        # 1. HMAC-SHA256でハッシュ化
        hashed_idm = self._hash_with_salt(idm)

        # 2. 暗号化（データベース保存時の追加保護）
        encrypted_idm = self._encrypt_data(hashed_idm)

        self._logger.debug(f"IDM processed securely")
        return encrypted_idm

    def verify_nfc_idm(self, idm: str, stored_encrypted_hash: str) -> bool:
        """
        V2.1.2: NFC IDMの検証
        タイミング攻撃に強い比較
        """
        try:
            # 1. 復号化
            decrypted_hash = self._decrypt_data(stored_encrypted_hash)

            # 2. 入力IDMをハッシュ化
            input_hash = self._hash_with_salt(idm, decrypted_hash.split(":")[0])

            # 3. タイミング攻撃に強い比較
            return hmac.compare_digest(input_hash, decrypted_hash)

        except Exception as e:
            self._logger.warning(f"IDM verification failed: {e}")
            return False

    def _hash_with_salt(self, data: str, salt: Optional[str] = None) -> str:
        """HMAC-SHA256 + ソルトによるハッシュ化"""
        if salt is None:
            salt = secrets.token_hex(32)

        idm_secret = getattr(self.config, "IDM_HASH_SECRET", "").encode()
        combined_data = f"{data}:{salt}".encode()

        hmac_hash = hmac.new(idm_secret, combined_data, hashlib.sha256).hexdigest()
        return f"{salt}:{hmac_hash}"

    def _encrypt_data(self, data: str) -> str:
        """V6.2.2: データの暗号化"""
        encrypted = self.fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def _decrypt_data(self, encrypted_data: str) -> str:
        """V6.2.3: データの復号化"""
        decoded = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.fernet.decrypt(decoded)
        return decrypted.decode()

    def get_security_headers(self) -> Dict[str, str]:
        """V14.4.1: セキュリティヘッダーの設定"""
        return {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "object-src 'none';"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }


# グローバルインスタンス
security_manager = SecurityManager()
