"""
開発環境設定

開発環境特有の設定を定義します。
"""

from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """開発環境設定クラス"""
    
    # 基本設定
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # データベース設定
    DATABASE_URL: str = "sqlite:///./attendance.db"
    DATABASE_ECHO: bool = True
    
    # Redis設定
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # セキュリティ設定（開発用の緩い設定）
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24時間
    PASORI_MOCK_MODE: bool = True
    
    # CORS設定（開発用に全許可）
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # ログ設定
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "text"  # 開発時は読みやすいテキスト形式
    
    # パフォーマンス設定（開発用の小さい値）
    MAX_CONNECTIONS_COUNT: int = 10
    MIN_CONNECTIONS_COUNT: int = 1
    
    # 監視設定
    ENABLE_MONITORING: bool = False
    
    # Slack通知（開発環境では無効）
    SLACK_ENABLED: bool = False
    
    # メール設定（開発環境では無効）
    EMAIL_ENABLED: bool = False
    
    # 開発用の追加設定
    AUTO_RELOAD: bool = True
    PROFILING_ENABLED: bool = True
    SQL_QUERY_LOGGING: bool = True
    
    # テストデータ設定
    SEED_TEST_DATA: bool = True
    TEST_USER_PASSWORD: str = "testpass123"
    
    # デバッグ用設定
    SHOW_ERROR_DETAILS: bool = True
    ENABLE_DEBUG_TOOLBAR: bool = True
    
    # ホットリロード設定
    RELOAD_ON_CODE_CHANGE: bool = True
    RELOAD_DIRS: list = ["backend", "config"]
    
    # 開発用エンドポイント
    ENABLE_DOCS: bool = True
    ENABLE_REDOC: bool = True
    ENABLE_GRAPHQL: bool = False