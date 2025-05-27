"""
基本設定

すべての環境で共通の設定を定義します。
"""

from datetime import time
from typing import List


class BaseConfig:
    """基本設定クラス"""
    
    # 基本設定
    APP_NAME: str = "勤怠管理システム"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # 勤務時間設定
    BUSINESS_START_TIME = time(9, 0)  # 09:00
    BUSINESS_END_TIME = time(18, 0)   # 18:00
    BREAK_START_TIME = time(12, 0)    # 12:00
    BREAK_END_TIME = time(13, 0)      # 13:00
    
    # 時間丸め設定（分単位）
    DAILY_ROUND_MINUTES: int = 15
    MONTHLY_ROUND_MINUTES: int = 30
    
    # 時間外/深夜/休日手当率
    OVERTIME_RATE_NORMAL: float = 1.25
    OVERTIME_RATE_LATE: float = 1.50
    NIGHT_RATE: float = 1.25
    HOLIDAY_RATE: float = 1.35
    
    # PaSoRi設定
    PASORI_TIMEOUT: int = 3
    
    # NFC設定
    NFC_TIMEOUT_SECONDS: int = 30
    NFC_MAX_RETRIES: int = 3
    
    # WebSocket設定
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_PONG_TIMEOUT: int = 10
    WS_MAX_CONNECTIONS: int = 1000
    WS_MAX_QUEUE_SIZE: int = 100
    WS_MAX_RECONNECT_ATTEMPTS: int = 5
    WS_BUFFER_SIZE: int = 1000
    
    # キャッシュ設定
    CACHE_DEFAULT_TTL: int = 300  # 5分
    CACHE_MAX_ENTRIES: int = 10000
    
    # バッチ処理設定
    BATCH_MAX_SIZE: int = 100
    BATCH_TIMEOUT: int = 30
    
    # レート制限
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_PUNCH: str = "300/minute"
    RATE_LIMIT_REPORT: str = "10/minute"
    
    # セキュリティポリシー
    MIN_PASSWORD_LENGTH: int = 12
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_DURATION: int = 30  # 分
    
    # ファイルアップロード
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".csv", ".xlsx", ".xls"]
    
    # エクスポート設定
    EXPORT_CHUNK_SIZE: int = 1000
    EXPORT_TIMEOUT: int = 300  # 5分
    
    # 監視設定
    MONITORING_INTERVAL: int = 60  # 秒
    ALERT_THRESHOLD_CPU: float = 80.0  # %
    ALERT_THRESHOLD_MEMORY: float = 80.0  # %
    ALERT_THRESHOLD_DISK: float = 90.0  # %
    
    # ログ保持期間
    LOG_RETENTION_DAYS: int = 30
    AUDIT_LOG_RETENTION_DAYS: int = 365