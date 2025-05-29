"""
構造化ログ設定

structlogを使用した構造化ログとセキュリティ監査ログ
"""

import logging
import logging.config
import structlog
from datetime import datetime
from typing import Any, Dict
from pathlib import Path

from ...config.config import settings


def setup_logging():
    """
    構造化ログの設定

    本番環境ではJSON形式、開発環境では人間が読みやすい形式でログを出力
    """

    # ログディレクトリの作成
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 基本的なロギング設定
    logging.basicConfig(
        format="%(message)s",
        stream=None,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # structlogプロセッサーの設定
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
    ]

    # 環境に応じたレンダラーの選択
    if settings.ENVIRONMENT == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    # structlogの設定
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 専用ロガーの設定
    setup_specialized_loggers()


def setup_specialized_loggers():
    """専用ロガーの設定"""

    log_dir = Path(settings.LOG_DIR)

    # ファイルハンドラーの設定
    handlers = {}

    # アプリケーションログ
    handlers["app_file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(log_dir / "app.log"),
        "maxBytes": 10485760,  # 10MB
        "backupCount": 5,
        "formatter": "json" if settings.ENVIRONMENT == "production" else "detailed",
    }

    # セキュリティ監査ログ
    handlers["security_file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(log_dir / "security.log"),
        "maxBytes": 10485760,
        "backupCount": 10,  # セキュリティログは長期保存
        "formatter": "json",
    }

    # パフォーマンスログ
    handlers["performance_file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(log_dir / "performance.log"),
        "maxBytes": 10485760,
        "backupCount": 3,
        "formatter": "json",
    }

    # エラーログ
    handlers["error_file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(log_dir / "error.log"),
        "maxBytes": 10485760,
        "backupCount": 5,
        "formatter": "json",
    }

    # コンソールハンドラー
    handlers["console"] = {
        "class": "logging.StreamHandler",
        "formatter": "simple",
    }

    # フォーマッターの設定
    formatters = {
        "simple": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(module)s %(funcName)s %(message)s",
        },
    }

    # ロガーの設定
    loggers = {
        "attendance.app": {
            "handlers": ["app_file", "console"],
            "level": settings.LOG_LEVEL,
            "propagate": False,
        },
        "attendance.security": {
            "handlers": ["security_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "attendance.performance": {
            "handlers": ["performance_file"],
            "level": "INFO",
            "propagate": False,
        },
        "attendance.error": {
            "handlers": ["error_file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
    }

    # ロギング設定を適用
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": loggers,
    }

    logging.config.dictConfig(config)


def get_logger(name: str = "attendance.app") -> structlog.BoundLogger:
    """
    構造化ロガーを取得

    Args:
        name: ロガー名

    Returns:
        構造化ロガー
    """
    return structlog.get_logger(name)


def get_security_logger() -> structlog.BoundLogger:
    """セキュリティ監査ロガーを取得"""
    return structlog.get_logger("attendance.security")


def get_performance_logger() -> structlog.BoundLogger:
    """パフォーマンスロガーを取得"""
    return structlog.get_logger("attendance.performance")


def get_error_logger() -> structlog.BoundLogger:
    """エラーロガーを取得"""
    return structlog.get_logger("attendance.error")


class SecurityAuditLogger:
    """セキュリティ監査ログ専用クラス"""

    def __init__(self):
        self.logger = get_security_logger()

    def log_login_attempt(
        self, username: str, success: bool, ip_address: str, user_agent: str = None
    ):
        """ログイン試行をログ"""
        self.logger.info(
            "login_attempt",
            username=username,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            event_type="authentication",
        )

    def log_punch_access(
        self, employee_id: int, card_id: str, success: bool, ip_address: str
    ):
        """打刻アクセスをログ"""
        self.logger.info(
            "punch_access",
            employee_id=employee_id,
            card_id_hash=hash(card_id),  # 実際のカードIDはハッシュ化
            success=success,
            ip_address=ip_address,
            event_type="punch",
        )

    def log_admin_action(
        self, admin_user: str, action: str, target: str, success: bool
    ):
        """管理者操作をログ"""
        self.logger.info(
            "admin_action",
            admin_user=admin_user,
            action=action,
            target=target,
            success=success,
            event_type="admin",
        )

    def log_data_access(self, user: str, resource: str, action: str, success: bool):
        """データアクセスをログ"""
        self.logger.info(
            "data_access",
            user=user,
            resource=resource,
            action=action,
            success=success,
            event_type="data",
        )


class PerformanceLogger:
    """パフォーマンス監視ログ専用クラス"""

    def __init__(self):
        self.logger = get_performance_logger()

    def log_request_timing(
        self, endpoint: str, method: str, duration_ms: float, status_code: int
    ):
        """リクエスト処理時間をログ"""
        self.logger.info(
            "request_timing",
            endpoint=endpoint,
            method=method,
            duration_ms=duration_ms,
            status_code=status_code,
            metric_type="timing",
        )

    def log_database_query(
        self, query_type: str, duration_ms: float, record_count: int = None
    ):
        """データベースクエリ性能をログ"""
        self.logger.info(
            "database_query",
            query_type=query_type,
            duration_ms=duration_ms,
            record_count=record_count,
            metric_type="database",
        )

    def log_cache_operation(self, operation: str, hit: bool, duration_ms: float = None):
        """キャッシュ操作をログ"""
        self.logger.info(
            "cache_operation",
            operation=operation,
            hit=hit,
            duration_ms=duration_ms,
            metric_type="cache",
        )


# シングルトンインスタンス
security_audit = SecurityAuditLogger()
performance_monitor = PerformanceLogger()
