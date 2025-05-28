"""
本番環境設定

本番環境特有の設定を定義します。
"""

import os
from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """本番環境設定クラス"""
    
    # 基本設定
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # データベース設定（環境変数から取得）
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/attendance_db"
    )
    DATABASE_ECHO: bool = False
    
    # Redis設定（環境変数から取得）
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )
    
    # セキュリティ設定（本番用の厳格な設定）
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1時間
    PASORI_MOCK_MODE: bool = False
    
    # CORS設定（本番用に制限）
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "https://attendance.example.com"
    ).split(",")
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["GET", "POST", "PUT", "DELETE"]
    CORS_ALLOW_HEADERS: list = ["Content-Type", "Authorization"]
    
    # ログ設定
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # 本番環境ではJSON形式
    
    # パフォーマンス設定
    MAX_CONNECTIONS_COUNT: int = 100
    MIN_CONNECTIONS_COUNT: int = 10
    
    # 監視設定
    ENABLE_MONITORING: bool = True
    
    # Slack通知
    SLACK_ENABLED: bool = True
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    SLACK_CHANNEL: str = os.getenv("SLACK_CHANNEL", "#attendance-alerts")
    
    # メール設定
    EMAIL_ENABLED: bool = True
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@attendance.example.com")
    
    # セキュリティヘッダー
    SECURITY_HEADERS: dict = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'"
    }
    
    # SSL設定
    SSL_REDIRECT: bool = True
    SSL_CERT_PATH: str = os.getenv("SSL_CERT_PATH", "/etc/ssl/certs/cert.pem")
    SSL_KEY_PATH: str = os.getenv("SSL_KEY_PATH", "/etc/ssl/private/key.pem")
    
    # バックアップ設定
    BACKUP_ENABLED: bool = True
    BACKUP_SCHEDULE: str = "0 2 * * *"  # 毎日午前2時
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_S3_BUCKET: str = os.getenv("BACKUP_S3_BUCKET", "")
    
    # レート制限（本番用に厳格化）
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_PUNCH: str = "200/minute"
    RATE_LIMIT_REPORT: str = "5/minute"
    
    # キャッシュ設定
    CACHE_REDIS_CLUSTER: bool = True
    CACHE_REDIS_NODES: list = os.getenv(
        "CACHE_REDIS_NODES",
        "redis://node1:6379,redis://node2:6379"
    ).split(",")
    
    # CDN設定
    CDN_ENABLED: bool = True
    CDN_URL: str = os.getenv("CDN_URL", "https://cdn.attendance.example.com")
    
    # 監視・ロギング
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    DATADOG_API_KEY: str = os.getenv("DATADOG_API_KEY", "")
    
    # 本番用の追加設定
    AUTO_RELOAD: bool = False
    PROFILING_ENABLED: bool = False
    SQL_QUERY_LOGGING: bool = False
    SHOW_ERROR_DETAILS: bool = False
    ENABLE_DEBUG_TOOLBAR: bool = False
    
    # ドキュメント（本番では無効）
    ENABLE_DOCS: bool = False
    ENABLE_REDOC: bool = False