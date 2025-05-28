"""
Mac mini 向けパフォーマンス最適化設定
"""
import os
import multiprocessing

# CPUコア数の取得
CPU_COUNT = multiprocessing.cpu_count()

# Mac mini 向けパフォーマンス設定
MAC_MINI_CONFIG = {
    "WORKER_COUNT": min(2, CPU_COUNT),  # Mac mini のCPUコア数に応じて調整
    "MAX_CONNECTIONS": 50,
    "MEMORY_LIMIT": "512MB",
    "LOG_ROTATION": "daily",
    "CACHE_SIZE": 128,  # MB
    "DB_POOL_SIZE": 5,
    "DB_MAX_OVERFLOW": 10,
}

# uvicorn 起動設定の最適化
UVICORN_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": MAC_MINI_CONFIG["WORKER_COUNT"],
    "reload": True,  # 開発時
    "log_level": "info",
    "access_log": True,
    "use_colors": True,
    "limit_concurrency": MAC_MINI_CONFIG["MAX_CONNECTIONS"],
}

# 開発環境用追加設定
DEV_CONFIG = {
    "AUTO_RELOAD_DIRS": ["backend", "config", "scripts"],
    "HOT_RELOAD_EXTENSIONS": [".py", ".env", ".json"],
    "DEBUG_TOOLBAR": True,
    "PROFILING": False,  # パフォーマンス分析時のみ有効化
}

# Mac mini ネットワーク設定
NETWORK_CONFIG = {
    "HOST": os.getenv("HOST", "0.0.0.0"),
    "PORT": int(os.getenv("PORT", "8000")),
    "ALLOWED_HOSTS": ["localhost", "127.0.0.1", "0.0.0.0"],
    "CORS_ALLOW_CREDENTIALS": True,
    "CORS_MAX_AGE": 3600,
}

# システムリソース最適化
RESOURCE_LIMITS = {
    "MAX_REQUEST_SIZE": 10 * 1024 * 1024,  # 10MB
    "REQUEST_TIMEOUT": 30,  # seconds
    "KEEPALIVE_TIMEOUT": 5,  # seconds
    "GRACEFUL_TIMEOUT": 30,  # seconds
}

def get_optimal_workers():
    """最適なワーカー数を計算"""
    # Mac mini M1/M2: 8コア推奨
    # Mac mini Intel: 4-6コア推奨
    if CPU_COUNT >= 8:
        return 4
    elif CPU_COUNT >= 4:
        return 2
    else:
        return 1

def get_db_pool_config():
    """データベース接続プール設定を取得"""
    return {
        "pool_size": MAC_MINI_CONFIG["DB_POOL_SIZE"],
        "max_overflow": MAC_MINI_CONFIG["DB_MAX_OVERFLOW"],
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }