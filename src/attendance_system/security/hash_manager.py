"""
OWASP ASVS Level 2準拠 ハッシュ管理マネージャー
"""
import hashlib
import hmac
import secrets
import bcrypt
from typing import Optional, Tuple
import logging

from attendance_system.config.config import settings


class SecureHashManager:
    """
    OWASP ASVS Level 2準拠のハッシュ管理マネージャー
    V2.4: パスワード保存要件対応
    """

    def __init__(self):
        self.config = settings
        self._logger = logging.getLogger(__name__)

        # IDMハッシュ用の秘密キー
        self.idm_secret = getattr(self.config, "IDM_HASH_SECRET", "").encode()
        if len(self.idm_secret) < 64:
            raise ValueError("IDM_HASH_SECRET must be at least 64 characters")

    def hash_password(self, password: str) -> str:
        """
        V2.4.1: bcryptによるパスワードハッシュ化
        最小コスト12（OWASP推奨）
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # bcryptのコスト係数は12以上（OWASP ASVS Level 2）
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        V2.4.2: パスワード検証
        タイミング攻撃に強い比較
        """
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception as e:
            self._logger.warning(f"Password verification failed: {e}")
            return False

    def hash_idm_secure(
        self, idm: str, custom_salt: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        V2.1.1: iPhone Suica IDMの安全なハッシュ化

        Returns:
            Tuple[str, str]: (salt, hashed_idm)
        """
        if not idm or len(idm) < 8:
            raise ValueError("Invalid IDM format")

        # ソルト生成
        if custom_salt is None:
            salt = secrets.token_hex(32)
        else:
            salt = custom_salt

        # HMAC-SHA256でハッシュ化
        combined_data = f"{idm}:{salt}".encode("utf-8")
        hmac_hash = hmac.new(self.idm_secret, combined_data, hashlib.sha256).hexdigest()

        return salt, hmac_hash

    def verify_idm_hash(self, idm: str, salt: str, stored_hash: str) -> bool:
        """
        V2.1.2: IDMハッシュの検証
        タイミング攻撃に強い比較
        """
        try:
            _, computed_hash = self.hash_idm_secure(idm, salt)
            return hmac.compare_digest(computed_hash, stored_hash)
        except Exception as e:
            self._logger.warning(f"IDM hash verification failed: {e}")
            return False

    def hash_data_with_hmac(self, data: str, purpose: str = "general") -> str:
        """
        V6.2.6: 汎用HMAC-SHA256ハッシュ化
        """
        if not data:
            raise ValueError("Data cannot be empty")

        # 用途別のコンテキスト追加
        contextualized_data = f"{purpose}:{data}".encode("utf-8")

        hmac_hash = hmac.new(
            self.idm_secret, contextualized_data, hashlib.sha256
        ).hexdigest()

        return hmac_hash

    def generate_salt(self, length: int = 32) -> str:
        """V2.3.1: 暗号学的に安全なソルト生成"""
        return secrets.token_hex(length)

    def constant_time_compare(self, a: str, b: str) -> bool:
        """V2.3.2: タイミング攻撃に強い文字列比較"""
        return hmac.compare_digest(a, b)


# グローバルインスタンス
hash_manager = SecureHashManager()
