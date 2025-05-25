"""
勤怠管理システム設定管理モジュール

環境変数から設定を読み込み、アプリケーション全体で使用する設定を管理します。
"""

import os
from typing import Optional
from datetime import time
from pathlib import Path
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


class Config:
    """アプリケーション設定クラス"""
    
    # 基本設定
    APP_NAME: str = "勤怠管理システム"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # データベース設定
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/attendance.db")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"
    
    # API設定
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS設定
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    
    # PaSoRi設定
    IDM_HASH_SECRET: str = os.getenv("IDM_HASH_SECRET", "your-idm-hash-secret")
    PASORI_TIMEOUT: int = int(os.getenv("PASORI_TIMEOUT", "3"))
    PASORI_MOCK_MODE: bool = os.getenv("PASORI_MOCK_MODE", "True").lower() == "true"
    
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
    SLACK_ENABLED: bool = os.getenv("SLACK_ENABLED", "False").lower() == "true"
    SLACK_TOKEN: str = os.getenv("SLACK_TOKEN", "")
    SLACK_CHANNEL: str = os.getenv("SLACK_CHANNEL", "#attendance-alerts")
    
    # ログ設定
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")
    
    # データディレクトリ
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    
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
config = Config()