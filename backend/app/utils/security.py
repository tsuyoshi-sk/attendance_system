"""
セキュリティユーティリティ

入力値のサニタイズ、検証、およびセキュリティ関連の機能を提供します。
"""

import re
import hashlib
import hmac
import secrets
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from config.config import config
from backend.app.utils.logging_config import log_security_event


logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """セキュリティ関連のエラー"""
    pass


class InputSanitizer:
    """入力値のサニタイズクラス"""
    
    # SQLインジェクション対策用のパターン
    SQL_INJECTION_PATTERNS = [
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
        r"(--|#|\/\*|\*\/)",
        r"(\bor\b\s*\d+\s*=\s*\d+)",
        r"(\band\b\s*\d+\s*=\s*\d+)",
        r"(\'|\"|;|\\)"
    ]
    
    # XSS対策用のパターン
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>"
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """
        文字列をサニタイズ
        
        Args:
            value: 入力文字列
            max_length: 最大長
        
        Returns:
            str: サニタイズされた文字列
        
        Raises:
            SecurityError: 危険な入力が検出された場合
        """
        if not isinstance(value, str):
            return str(value)
        
        # 長さチェック
        if len(value) > max_length:
            logger.warning(f"入力値が最大長を超えています: {len(value)} > {max_length}")
            value = value[:max_length]
        
        # SQLインジェクションパターンチェック
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                log_security_event(
                    "SQL_INJECTION_ATTEMPT",
                    details=f"Pattern detected: {pattern}"
                )
                raise SecurityError("危険な入力が検出されました")
        
        # XSSパターンチェック
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                log_security_event(
                    "XSS_ATTEMPT",
                    details=f"Pattern detected: {pattern}"
                )
                raise SecurityError("危険な入力が検出されました")
        
        # 基本的なエスケープ
        value = value.replace("'", "''")  # SQLエスケープ
        value = value.replace("<", "&lt;").replace(">", "&gt;")  # HTMLエスケープ
        
        return value.strip()
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        辞書データをサニタイズ
        
        Args:
            data: 入力辞書
        
        Returns:
            Dict[str, Any]: サニタイズされた辞書
        """
        sanitized = {}
        for key, value in data.items():
            # キーもサニタイズ
            safe_key = cls.sanitize_string(key, max_length=100)
            
            if isinstance(value, str):
                sanitized[safe_key] = cls.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[safe_key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[safe_key] = [
                    cls.sanitize_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[safe_key] = value
        
        return sanitized


class RateLimiter:
    """レート制限クラス"""
    
    def __init__(self):
        self._attempts = {}  # {key: [(timestamp, count)]}
        self._blocked_until = {}  # {key: timestamp}
    
    def check_rate_limit(
        self,
        key: str,
        max_attempts: int = 10,
        window_seconds: int = 60,
        block_duration_seconds: int = 300
    ) -> bool:
        """
        レート制限をチェック
        
        Args:
            key: 識別キー（IPアドレスなど）
            max_attempts: ウィンドウ内の最大試行回数
            window_seconds: ウィンドウサイズ（秒）
            block_duration_seconds: ブロック期間（秒）
        
        Returns:
            bool: アクセス可能な場合True
        """
        now = datetime.now()
        
        # ブロック中かチェック
        if key in self._blocked_until:
            if now < self._blocked_until[key]:
                remaining = (self._blocked_until[key] - now).total_seconds()
                log_security_event(
                    "RATE_LIMIT_BLOCKED",
                    details=f"Key: {key}, Remaining: {remaining:.0f}s"
                )
                return False
            else:
                # ブロック期間終了
                del self._blocked_until[key]
        
        # 試行履歴を取得
        if key not in self._attempts:
            self._attempts[key] = []
        
        # 古い試行を削除
        cutoff = now - timedelta(seconds=window_seconds)
        self._attempts[key] = [
            (ts, count) for ts, count in self._attempts[key]
            if ts > cutoff
        ]
        
        # 現在の試行数を計算
        current_attempts = sum(count for _, count in self._attempts[key])
        
        if current_attempts >= max_attempts:
            # レート制限に達した
            self._blocked_until[key] = now + timedelta(seconds=block_duration_seconds)
            log_security_event(
                "RATE_LIMIT_EXCEEDED",
                details=f"Key: {key}, Attempts: {current_attempts}"
            )
            return False
        
        # 試行を記録
        self._attempts[key].append((now, 1))
        return True
    
    def cleanup_old_entries(self, older_than_hours: int = 24):
        """古いエントリをクリーンアップ"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        
        # 古い試行履歴を削除
        for key in list(self._attempts.keys()):
            self._attempts[key] = [
                (ts, count) for ts, count in self._attempts[key]
                if ts > cutoff
            ]
            if not self._attempts[key]:
                del self._attempts[key]
        
        # 古いブロック情報を削除
        for key in list(self._blocked_until.keys()):
            if self._blocked_until[key] < cutoff:
                del self._blocked_until[key]


class TokenManager:
    """トークン管理クラス"""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        セキュアなトークンを生成
        
        Args:
            length: トークンの長さ
        
        Returns:
            str: トークン文字列
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_token(token: str, salt: str = None) -> str:
        """
        トークンをハッシュ化
        
        Args:
            token: トークン
            salt: ソルト（省略時は設定から取得）
        
        Returns:
            str: ハッシュ化されたトークン
        """
        if salt is None:
            salt = config.IDM_HASH_SECRET
        
        return hashlib.sha256(f"{token}{salt}".encode()).hexdigest()
    
    @staticmethod
    def verify_token(token: str, hashed_token: str, salt: str = None) -> bool:
        """
        トークンを検証
        
        Args:
            token: 検証するトークン
            hashed_token: ハッシュ化されたトークン
            salt: ソルト
        
        Returns:
            bool: 一致する場合True
        """
        return TokenManager.hash_token(token, salt) == hashed_token


class CryptoUtils:
    """暗号化関連ユーティリティ"""
    
    @staticmethod
    def hash_idm(idm: str) -> str:
        """
        FeliCa IDmをハッシュ化
        
        Args:
            idm: IDm文字列
        
        Returns:
            str: ハッシュ化されたIDm
        """
        return hashlib.sha256(
            f"{idm}{config.IDM_HASH_SECRET}".encode()
        ).hexdigest()
    
    @staticmethod
    def generate_hmac(data: str, key: str = None) -> str:
        """
        HMACを生成
        
        Args:
            data: データ
            key: 秘密鍵（省略時は設定から取得）
        
        Returns:
            str: HMAC値
        """
        if key is None:
            key = config.SECRET_KEY
        
        return hmac.new(
            key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_hmac(data: str, hmac_value: str, key: str = None) -> bool:
        """
        HMACを検証
        
        Args:
            data: データ
            hmac_value: HMAC値
            key: 秘密鍵
        
        Returns:
            bool: 検証成功の場合True
        """
        expected = CryptoUtils.generate_hmac(data, key)
        return hmac.compare_digest(expected, hmac_value)


# グローバルインスタンス
rate_limiter = RateLimiter()


def validate_employee_id(employee_id: Any) -> int:
    """
    従業員IDを検証
    
    Args:
        employee_id: 従業員ID
    
    Returns:
        int: 検証済みの従業員ID
    
    Raises:
        ValueError: 無効な従業員IDの場合
    """
    try:
        emp_id = int(employee_id)
        if emp_id <= 0 or emp_id > 999999:
            raise ValueError("従業員IDの範囲が無効です")
        return emp_id
    except (TypeError, ValueError):
        raise ValueError("無効な従業員IDです")


def validate_punch_type(punch_type: str) -> str:
    """
    打刻タイプを検証
    
    Args:
        punch_type: 打刻タイプ
    
    Returns:
        str: 検証済みの打刻タイプ
    
    Raises:
        ValueError: 無効な打刻タイプの場合
    """
    valid_types = ['IN', 'OUT', 'OUTSIDE', 'RETURN']
    punch_type_upper = punch_type.upper()
    
    if punch_type_upper not in valid_types:
        raise ValueError(f"無効な打刻タイプです: {punch_type}")
    
    return punch_type_upper


def validate_datetime(dt_string: str) -> datetime:
    """
    日時文字列を検証
    
    Args:
        dt_string: 日時文字列
    
    Returns:
        datetime: 検証済みの日時オブジェクト
    
    Raises:
        ValueError: 無効な日時の場合
    """
    try:
        # ISO8601形式をサポート
        if 'T' in dt_string:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
        
        # 未来の日時は拒否
        if dt > datetime.now() + timedelta(minutes=5):
            raise ValueError("未来の日時は指定できません")
        
        # 古すぎる日時は拒否（1年以上前）
        if dt < datetime.now() - timedelta(days=365):
            raise ValueError("古すぎる日時は指定できません")
        
        return dt
    except Exception as e:
        raise ValueError(f"無効な日時形式です: {str(e)}")