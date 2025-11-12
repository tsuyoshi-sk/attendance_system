"""
勤怠管理システム設定管理モジュール

環境変数から設定を読み込み、アプリケーション全体で使用する設定を管理します。
"""

import os
import json
import logging
from typing import Optional, List, Type, Union
from datetime import time
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from dotenv import load_dotenv

# 環境設定インポートを削除（存在しないため）
# from .environments import ...

logger = logging.getLogger(__name__)

# .envファイルの読み込み
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # プロジェクトルートの.envも試す
    root_env = Path(__file__).parent.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)


class Settings(BaseSettings):
    """アプリケーション設定クラス"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # 基本設定
    APP_NAME: str = "勤怠管理システム"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # データベース設定
    DATABASE_URL: str = "sqlite:///./attendance.db"
    DATABASE_ECHO: bool = False
    
    # セキュリティ設定
    JWT_SECRET_KEY: str = Field(default="development-jwt-secret-key-change-me-please", min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 60→15分に短縮
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BYPASS_AUTH: bool = False
    
    # API設定
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS設定
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_CREDENTIALS: bool = True
    SECURITY_HEADERS_ENABLED: bool = True
    
    # Redis設定
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PREFIX: str = "attendance_system"
    
    # PaSoRi設定
    IDM_HASH_SECRET: str = "your-idm-hash-secret"
    PASORI_TIMEOUT: int = 3
    PASORI_MOCK_MODE: bool = True
    
    # NFC設定
    NFC_TIMEOUT_SECONDS: int = 30
    NFC_MAX_RETRIES: int = 3
    
    # 勤務時間設定
    BUSINESS_START_TIME: time = time(9, 0)  # 09:00
    BUSINESS_END_TIME: time = time(18, 0)   # 18:00
    BREAK_START_TIME: time = time(12, 0)    # 12:00
    BREAK_END_TIME: time = time(13, 0)      # 13:00
    
    # 時間丸め設定（分単位）
    DAILY_ROUND_MINUTES: int = int(os.getenv("DAILY_ROUND_MINUTES", "15"))
    MONTHLY_ROUND_MINUTES: int = int(os.getenv("MONTHLY_ROUND_MINUTES", "30"))
    
    # 時間外/深夜/休日手当率
    OVERTIME_RATE_NORMAL: float = float(os.getenv("OVERTIME_RATE_NORMAL", "1.25"))
    OVERTIME_RATE_LATE: float = float(os.getenv("OVERTIME_RATE_LATE", "1.50"))
    NIGHT_RATE: float = float(os.getenv("NIGHT_RATE", "1.25"))
    HOLIDAY_RATE: float = float(os.getenv("HOLIDAY_RATE", "1.35"))
    
    # Slack設定
    SLACK_ENABLED: bool = False
    SLACK_TOKEN: str = ""
    SLACK_CHANNEL: str = "#attendance-alerts"
    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_USERNAME: str = "勤怠管理Bot"
    SLACK_ICON_EMOJI: str = ":clock9:"
    
    # ログ設定
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    LOG_DIR: str = "./logs"
    LOG_FILE_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_FILE_BACKUP_COUNT: int = 5
    
    # データディレクトリ
    DATA_DIR: str = "./data"
    
    # パフォーマンス設定
    MAX_CONNECTIONS_COUNT: int = 100
    MIN_CONNECTIONS_COUNT: int = 10
    
    # 監視設定
    ENABLE_MONITORING: bool = True
    MONITORING_INTERVAL_SECONDS: int = 60
    DAILY_BATCH_TIME: str = "23:00"
    MONTHLY_BATCH_DAY: int = 25
    TIMEZONE: str = "Asia/Tokyo"
    
    # NFC セキュリティ設定
    NFC_CARD_ID_SALT: str = "default-nfc-salt-key"
    OFFLINE_QUEUE_SIZE: int = 1000
    OFFLINE_RETRY_INTERVAL: int = 300
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            value = v.strip()
            if not value:
                return []
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [origin.strip() for origin in value.split(',') if origin.strip()]
        return v
    
    @field_validator('JWT_SECRET_KEY')
    @classmethod
    def validate_jwt_secret(cls, v):
        if v == "your-secret-key-here-change-in-production":
            import secrets
            return secrets.token_urlsafe(32)
        return v
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        if v == "your-app-secret-key-here-change-in-production":
            import secrets
            return secrets.token_urlsafe(32)
        return v
    
    def __post_init__(self):
        """初期化後の処理"""
        # データディレクトリの作成
        Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.LOG_DIR).mkdir(parents=True, exist_ok=True)
    
    def validate(self):
        """設定値の検証"""
        errors = []
        
        if len(self.SECRET_KEY) < 16:
            errors.append("SECRET_KEY は16文字以上である必要があります")
        
        if len(self.IDM_HASH_SECRET) < 8:
            errors.append("IDM_HASH_SECRET は8文字以上である必要があります")
        
        if self.PASORI_TIMEOUT < 1 or self.PASORI_TIMEOUT > 10:
            errors.append("PASORI_TIMEOUT は1-10秒の範囲で設定してください")
        
        if errors:
            raise ValueError("設定エラー: " + ", ".join(errors))
    
    def is_slack_enabled(self) -> bool:
        """Slack通知が有効かどうか"""
        return self.SLACK_ENABLED and bool(self.SLACK_TOKEN)
    
    def is_mock_mode(self) -> bool:
        """PaSoRiモックモードかどうか"""
        return self.PASORI_MOCK_MODE
    
    def get_database_url(self) -> str:
        """データベースURLを取得"""
        return self.DATABASE_URL


# 環境別設定は単純化されたため削除


# 設定インスタンス（環境別設定を単純化）
settings = Settings()

# 後方互換性のため
config = settings

# 設定の検証とログ出力
logger.info(f"Configuration loaded for environment: {settings.ENVIRONMENT}")
logger.info(f"Debug mode: {settings.DEBUG}")
logger.info(f"Database: {settings.DATABASE_URL.split('@')[0] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
logger.info(f"Redis: {settings.REDIS_URL}")
logger.info(f"CORS origins: {settings.CORS_ORIGINS}")
