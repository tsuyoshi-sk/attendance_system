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
    PASORI_MOCK_MODE: bool = os.getenv("PASORI_MOCK_MODE", "False").lower() == "true"
    
    # 勤務時間設定
    BUSINESS_START_TIME: time = time(9, 0)  # 始業時間
    BUSINESS_END_TIME: time = time(18, 0)   # 終業時間
    BREAK_START_TIME: time = time(12, 0)    # 休憩開始
    BREAK_END_TIME: time = time(13, 0)      # 休憩終了
    NIGHT_START_TIME: time = time(22, 0)    # 深夜時間帯開始
    NIGHT_END_TIME: time = time(5, 0)       # 深夜時間帯終了
    
    # 丸め設定
    DAILY_ROUND_MINUTES: int = int(os.getenv("DAILY_ROUND_MINUTES", "15"))    # 日次の丸め単位（分）
    MONTHLY_ROUND_MINUTES: int = int(os.getenv("MONTHLY_ROUND_MINUTES", "30")) # 月次の丸め単位（分）
    
    # 割増率設定
    OVERTIME_RATE_NORMAL: float = float(os.getenv("OVERTIME_RATE_NORMAL", "1.25"))  # 通常残業
    OVERTIME_RATE_LATE: float = float(os.getenv("OVERTIME_RATE_LATE", "1.50"))      # 深夜残業
    NIGHT_RATE: float = float(os.getenv("NIGHT_RATE", "1.25"))                      # 深夜割増
    HOLIDAY_RATE: float = float(os.getenv("HOLIDAY_RATE", "1.35"))                  # 休日割増
    
    # Slack設定
    SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
    SLACK_CHANNEL: str = os.getenv("SLACK_CHANNEL", "#attendance")
    SLACK_USERNAME: str = os.getenv("SLACK_USERNAME", "勤怠管理Bot")
    SLACK_ICON_EMOJI: str = os.getenv("SLACK_ICON_EMOJI", ":clock9:")
    
    # バッチ処理設定
    DAILY_BATCH_TIME: str = os.getenv("DAILY_BATCH_TIME", "23:00")
    MONTHLY_BATCH_DAY: int = int(os.getenv("MONTHLY_BATCH_DAY", "25"))
    
    # ファイルパス設定
    DATA_DIR: Path = Path("./data")
    LOG_DIR: Path = Path("./logs")
    EXPORT_DIR: Path = Path("./exports")
    
    # ログ設定
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_MAX_BYTES: int = int(os.getenv("LOG_FILE_MAX_BYTES", "10485760"))  # 10MB
    LOG_FILE_BACKUP_COUNT: int = int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))
    
    # タイムゾーン設定
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tokyo")
    
    # オフライン設定
    OFFLINE_QUEUE_SIZE: int = int(os.getenv("OFFLINE_QUEUE_SIZE", "1000"))
    OFFLINE_RETRY_INTERVAL: int = int(os.getenv("OFFLINE_RETRY_INTERVAL", "300"))  # 秒
    
    @classmethod
    def validate(cls) -> None:
        """設定値の検証"""
        # 必須項目のチェック
        if cls.SECRET_KEY == "your-secret-key-change-in-production":
            print("警告: SECRET_KEYがデフォルト値のままです。本番環境では必ず変更してください。")
        
        if cls.IDM_HASH_SECRET == "your-idm-hash-secret":
            print("警告: IDM_HASH_SECRETがデフォルト値のままです。本番環境では必ず変更してください。")
        
        # ディレクトリの作成
        for dir_path in [cls.DATA_DIR, cls.LOG_DIR, cls.EXPORT_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 時間設定の妥当性チェック
        if cls.BUSINESS_START_TIME >= cls.BUSINESS_END_TIME:
            raise ValueError("始業時間は終業時間より前である必要があります")
        
        if cls.BREAK_START_TIME >= cls.BREAK_END_TIME:
            raise ValueError("休憩開始時間は休憩終了時間より前である必要があります")
    
    @classmethod
    def get_database_url(cls) -> str:
        """データベースURLを取得（SQLiteの場合は絶対パスに変換）"""
        if cls.DATABASE_URL.startswith("sqlite:///"):
            # SQLiteの場合は絶対パスに変換
            db_path = cls.DATABASE_URL.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                db_path = os.path.abspath(db_path)
            return f"sqlite:///{db_path}"
        return cls.DATABASE_URL
    
    @classmethod
    def is_slack_enabled(cls) -> bool:
        """Slack通知が有効かどうかを判定"""
        return bool(cls.SLACK_WEBHOOK_URL)
    
    @classmethod
    def is_mock_mode(cls) -> bool:
        """PaSoRiモックモードかどうかを判定"""
        return cls.PASORI_MOCK_MODE


# 設定のインスタンス化と検証
config = Config()