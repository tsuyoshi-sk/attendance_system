"""
テスト環境設定

テスト環境特有の設定を定義します。
"""

from .base import BaseConfig


class TestingConfig(BaseConfig):
    """テスト環境設定クラス"""
    
    # 基本設定
    DEBUG: bool = True
    TESTING: bool = True
    ENVIRONMENT: str = "testing"
    
    # データベース設定（テスト用のインメモリDB）
    DATABASE_URL: str = "sqlite:///:memory:"
    DATABASE_ECHO: bool = False
    
    # Redis設定（テスト用のモック）
    REDIS_URL: str = "redis://localhost:6379/15"  # テスト用DB番号
    
    # セキュリティ設定（テスト用）
    JWT_SECRET_KEY: str = "test-secret-key-for-testing-only"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 5
    PASORI_MOCK_MODE: bool = True
    
    # CORS設定（テスト用）
    CORS_ORIGINS: list = ["http://testserver"]
    
    # ログ設定
    LOG_LEVEL: str = "ERROR"  # テスト時は最小限のログ
    LOG_FORMAT: str = "text"
    
    # パフォーマンス設定（テスト用の最小値）
    MAX_CONNECTIONS_COUNT: int = 5
    MIN_CONNECTIONS_COUNT: int = 1
    
    # 監視設定（テストでは無効）
    ENABLE_MONITORING: bool = False
    
    # 通知設定（テストでは無効）
    SLACK_ENABLED: bool = False
    EMAIL_ENABLED: bool = False
    
    # キャッシュ設定（テスト用）
    CACHE_DEFAULT_TTL: int = 1  # 1秒
    CACHE_REDIS_CLUSTER: bool = False
    
    # テスト用設定
    DISABLE_AUTH: bool = False  # 認証を無効化するオプション
    MOCK_EXTERNAL_SERVICES: bool = True
    TEST_DATA_SEED: bool = True
    
    # レート制限（テストでは無効）
    RATE_LIMIT_ENABLED: bool = False
    
    # バックグラウンドタスク（テストでは同期実行）
    BACKGROUND_TASKS_SYNC: bool = True
    
    # ファイルアップロード（テスト用の小さいサイズ）
    MAX_UPLOAD_SIZE: int = 1 * 1024 * 1024  # 1MB
    
    # タイムアウト設定（テスト用に短縮）
    REQUEST_TIMEOUT: int = 5
    DATABASE_TIMEOUT: int = 1
    
    # フィクスチャ設定
    FIXTURE_PATH: str = "tests/fixtures"
    USE_FIXTURES: bool = True
    
    # テストカバレッジ設定
    COVERAGE_ENABLED: bool = True
    COVERAGE_MIN_PERCENTAGE: float = 80.0