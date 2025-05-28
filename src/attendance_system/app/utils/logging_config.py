"""
ロギング設定

アプリケーション全体のロギング設定を管理します。
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from config.config import config


class JSONFormatter(logging.Formatter):
    """JSON形式でログを出力するフォーマッター"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # エラーの場合は例外情報を追加
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 追加の属性がある場合
        if hasattr(record, "employee_id"):
            log_data["employee_id"] = record.employee_id
        if hasattr(record, "punch_type"):
            log_data["punch_type"] = record.punch_type
        if hasattr(record, "device_type"):
            log_data["device_type"] = record.device_type
        if hasattr(record, "processing_time"):
            log_data["processing_time"] = record.processing_time

        return json.dumps(log_data, ensure_ascii=False)


class SecurityAuditFilter(logging.Filter):
    """セキュリティ監査用のログフィルター"""

    def filter(self, record: logging.LogRecord) -> bool:
        # セキュリティ関連のログのみを通す
        security_keywords = [
            "security",
            "auth",
            "login",
            "access",
            "permission",
            "hash",
            "idm",
            "card",
            "unauthorized",
        ]

        message = record.getMessage().lower()
        return any(keyword in message for keyword in security_keywords)


def setup_logging():
    """ロギングの設定"""

    # ログディレクトリの作成
    log_dir = Path(config.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

    # 既存のハンドラーをクリア
    root_logger.handlers = []

    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # アプリケーションログファイルハンドラー（JSON形式）
    app_log_file = log_dir / "app.log"
    app_file_handler = logging.handlers.RotatingFileHandler(
        app_log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
    )
    app_file_handler.setLevel(logging.DEBUG)
    app_file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(app_file_handler)

    # エラーログファイルハンドラー
    error_log_file = log_dir / "error.log"
    error_file_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_file_handler)

    # セキュリティ監査ログハンドラー
    security_log_file = log_dir / "security_audit.log"
    security_handler = logging.handlers.RotatingFileHandler(
        security_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,  # セキュリティログは長期保存
        encoding="utf-8",
    )
    security_handler.setLevel(logging.INFO)
    security_handler.setFormatter(JSONFormatter())
    security_handler.addFilter(SecurityAuditFilter())
    root_logger.addHandler(security_handler)

    # パフォーマンスログハンドラー
    performance_log_file = log_dir / "performance.log"
    performance_handler = logging.handlers.RotatingFileHandler(
        performance_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
        encoding="utf-8",
    )
    performance_handler.setLevel(logging.INFO)
    performance_handler.setFormatter(JSONFormatter())
    performance_logger = logging.getLogger("performance")
    performance_logger.addHandler(performance_handler)
    performance_logger.propagate = False

    # 打刻専用ログハンドラー
    punch_log_file = log_dir / "punch.log"
    punch_handler = logging.handlers.TimedRotatingFileHandler(
        punch_log_file,
        when="midnight",
        interval=1,
        backupCount=30,  # 30日分保存
        encoding="utf-8",
    )
    punch_handler.setLevel(logging.INFO)
    punch_handler.setFormatter(JSONFormatter())
    punch_logger = logging.getLogger("punch")
    punch_logger.addHandler(punch_handler)
    punch_logger.propagate = False

    # 特定のロガーのレベル設定
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("ロギング設定が完了しました")
    logger.info(f"ログディレクトリ: {log_dir}")


def get_logger(name: str) -> logging.Logger:
    """名前付きロガーを取得"""
    return logging.getLogger(name)


def log_punch_event(
    employee_id: int,
    punch_type: str,
    success: bool,
    processing_time: float,
    error_message: str = None,
):
    """打刻イベントをログに記録"""
    punch_logger = logging.getLogger("punch")

    log_data = {
        "employee_id": employee_id,
        "punch_type": punch_type,
        "success": success,
        "processing_time": processing_time,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if error_message:
        log_data["error"] = error_message

    if success:
        punch_logger.info(f"打刻成功: {json.dumps(log_data, ensure_ascii=False)}")
    else:
        punch_logger.error(f"打刻失敗: {json.dumps(log_data, ensure_ascii=False)}")


def log_performance_metric(
    operation: str, duration: float, success: bool, metadata: Dict[str, Any] = None
):
    """パフォーマンスメトリクスをログに記録"""
    performance_logger = logging.getLogger("performance")

    log_data = {
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        "success": success,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if metadata:
        log_data.update(metadata)

    performance_logger.info(json.dumps(log_data, ensure_ascii=False))


def log_security_event(
    event_type: str,
    user_id: str = None,
    ip_address: str = None,
    success: bool = True,
    details: str = None,
):
    """セキュリティイベントをログに記録"""
    logger = logging.getLogger(__name__)

    message = f"SECURITY: {event_type}"
    if user_id:
        message += f", user_id={user_id}"
    if ip_address:
        message += f", ip={ip_address}"
    if details:
        message += f", details={details}"

    if success:
        logger.info(message)
    else:
        logger.warning(message)
