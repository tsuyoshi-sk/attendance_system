"""
勤怠管理システム設定管理モジュール

環境変数から設定を読み込み、アプリケーション全体で使用する設定を管理します。
"""

import os
import json
from typing import Optional, List
from datetime import time
from pathlib import Path
from pydantic import BaseSettings, validator
from dotenv import load_dotenv


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
    
    # 基本設定
    APP_NAME: str = "勤怠管理システム"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # データベース設定
    DATABASE_URL: str = "sqlite:///./attendance.db"
    DATABASE_ECHO: bool = False
    
    # セキュリティ設定
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # API設定
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS設定
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
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
    BUSINESS_START_TIME = time(9, 0)  # 09:00
    BUSINESS_END_TIME = time(18, 0)   # 18:00
    BREAK_START_TIME = time(12, 0)    # 12:00
    BREAK_END_TIME = time(13, 0)      # 13:00
    
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
    
    # ログ設定
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_DIR: str = "./logs"
    
    # データディレクトリ
    DATA_DIR: str = "./data"
    
    # パフォーマンス設定
    MAX_CONNECTIONS_COUNT: int = 100
    MIN_CONNECTIONS_COUNT: int = 10
    
    # 監視設定
    ENABLE_MONITORING: bool = True
    MONITORING_INTERVAL_SECONDS: int = 60
    
    @validator('CORS_ORIGINS', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return v.split(',')
        return v
    
    @validator('JWT_SECRET_KEY')
    def validate_jwt_secret(cls, v):
        if v == "your-secret-key-here-change-in-production":
            import secrets
            return secrets.token_urlsafe(32)
        return v
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if v == "your-app-secret-key-here-change-in-production":
            import secrets
            return secrets.token_urlsafe(32)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
    
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
    
    @property
    def JWT_ALGORITHM(self) -> str:
        """JWT署名アルゴリズム"""
        return "HS256"


# 設定インスタンス
settings = Settings()

# 後方互換性のため
config = settings