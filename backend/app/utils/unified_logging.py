"""
統一ログ設定モジュール

アプリケーション全体で使用する統一されたロギング設定を提供します。
"""

import logging
import json
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from functools import wraps
import time
import traceback

from config.config import settings


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター（JSON/テキスト両対応）"""
    
    def __init__(self, format_type: str = "json"):
        super().__init__()
        self.format_type = format_type
    
    def format(self, record: logging.LogRecord) -> str:
        # 基本ログデータ
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process,
        }
        
        # 環境情報
        log_data["environment"] = settings.ENVIRONMENT
        log_data["app_name"] = settings.APP_NAME
        log_data["app_version"] = settings.APP_VERSION
        
        # エラー情報
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # カスタム属性
        custom_attrs = {
            "employee_id", "user_id", "punch_type", "device_type",
            "processing_time", "ip_address", "request_id", "correlation_id",
            "method", "path", "status_code", "response_time"
        }
        
        for attr in custom_attrs:
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)
        
        # フォーマット選択
        if self.format_type == "json":
            return json.dumps(log_data, ensure_ascii=False, default=str)
        else:
            # テキスト形式（開発用）
            base_msg = f"{log_data['timestamp']} | {log_data['level']:8} | {log_data['logger']:20} | {log_data['message']}"
            if "exception" in log_data:
                base_msg += f"\n{log_data['exception']['traceback']}"
            return base_msg


class LoggerFactory:
    """ロガーファクトリークラス"""
    
    _loggers = {}
    _initialized = False
    
    @classmethod
    def setup(cls):
        """ロギングシステムの初期設定"""
        if cls._initialized:
            return
        
        # ログディレクトリの作成
        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
        root_logger.handlers = []
        
        # フォーマッターの選択
        formatter_type = "text" if settings.DEBUG else settings.LOG_FORMAT
        formatter = StructuredFormatter(format_type=formatter_type)
        
        # 1. コンソールハンドラー
        cls._setup_console_handler(root_logger, formatter)
        
        # 2. アプリケーションログ
        cls._setup_application_logs(log_dir, formatter)
        
        # 3. 専門ログ
        cls._setup_specialized_logs(log_dir, formatter)
        
        # 4. 外部ライブラリのログレベル調整
        cls._configure_external_loggers()
        
        cls._initialized = True
        logger = cls.get_logger(__name__)
        logger.info("Unified logging system initialized", extra={
            "log_dir": str(log_dir),
            "log_level": settings.LOG_LEVEL,
            "environment": settings.ENVIRONMENT
        })
    
    @classmethod
    def _setup_console_handler(cls, root_logger: logging.Logger, formatter: StructuredFormatter):
        """コンソールハンドラーの設定"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)
        console_handler.setFormatter(formatter)
        
        # 本番環境では ERROR 以上のみコンソールに出力
        if settings.ENVIRONMENT == "production":
            console_handler.setLevel(logging.ERROR)
        
        root_logger.addHandler(console_handler)
    
    @classmethod
    def _setup_application_logs(cls, log_dir: Path, formatter: StructuredFormatter):
        """アプリケーションログの設定"""
        root_logger = logging.getLogger()
        
        # 一般アプリケーションログ
        app_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        app_handler.setFormatter(formatter)
        app_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(app_handler)
        
        # エラーログ
        error_handler = RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
    
    @classmethod
    def _setup_specialized_logs(cls, log_dir: Path, formatter: StructuredFormatter):
        """専門ログの設定"""
        
        # セキュリティログ
        security_logger = cls.get_logger("security")
        security_handler = TimedRotatingFileHandler(
            log_dir / "security.log",
            when='midnight',
            interval=1,
            backupCount=settings.AUDIT_LOG_RETENTION_DAYS,
            encoding='utf-8'
        )
        security_handler.setFormatter(formatter)
        security_logger.addHandler(security_handler)
        security_logger.propagate = False
        
        # パフォーマンスログ
        performance_logger = cls.get_logger("performance")
        performance_handler = RotatingFileHandler(
            log_dir / "performance.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=3,
            encoding='utf-8'
        )
        performance_handler.setFormatter(formatter)
        performance_logger.addHandler(performance_handler)
        performance_logger.propagate = False
        
        # 打刻ログ
        punch_logger = cls.get_logger("punch")
        punch_handler = TimedRotatingFileHandler(
            log_dir / "punch.log",
            when='midnight',
            interval=1,
            backupCount=settings.LOG_RETENTION_DAYS,
            encoding='utf-8'
        )
        punch_handler.setFormatter(formatter)
        punch_logger.addHandler(punch_handler)
        punch_logger.propagate = False
        
        # APIアクセスログ
        access_logger = cls.get_logger("api.access")
        access_handler = TimedRotatingFileHandler(
            log_dir / "api_access.log",
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        access_handler.setFormatter(formatter)
        access_logger.addHandler(access_handler)
        access_logger.propagate = False
    
    @classmethod
    def _configure_external_loggers(cls):
        """外部ライブラリのログレベル設定"""
        # 本番環境では外部ライブラリのログを抑制
        if settings.ENVIRONMENT == "production":
            logging.getLogger("uvicorn").setLevel(logging.WARNING)
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("aioredis").setLevel(logging.WARNING)
        else:
            # 開発環境でもSQL詳細ログは必要な時のみ
            logging.getLogger("sqlalchemy.engine").setLevel(
                logging.DEBUG if settings.DATABASE_ECHO else logging.WARNING
            )
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """名前付きロガーを取得"""
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]


# ロギングデコレーター
def log_execution_time(logger_name: str = __name__):
    """関数の実行時間をログに記録するデコレーター"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = LoggerFactory.get_logger(logger_name)
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(
                    f"Function executed successfully",
                    extra={
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function execution failed",
                    extra={
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = LoggerFactory.get_logger(logger_name)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(
                    f"Function executed successfully",
                    extra={
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function execution failed",
                    extra={
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# ログヘルパー関数
def log_api_request(
    method: str,
    path: str,
    status_code: int,
    response_time: float,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    error: Optional[str] = None
):
    """APIリクエストをログに記録"""
    logger = LoggerFactory.get_logger("api.access")
    
    log_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "response_time": response_time,
        "user_id": user_id,
        "ip_address": ip_address
    }
    
    if error:
        log_data["error"] = error
        logger.error("API request failed", extra=log_data)
    else:
        logger.info("API request completed", extra=log_data)


def log_security_event(
    event_type: str,
    success: bool,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """セキュリティイベントをログに記録"""
    logger = LoggerFactory.get_logger("security")
    
    log_data = {
        "event_type": event_type,
        "success": success,
        "user_id": user_id,
        "ip_address": ip_address
    }
    
    if details:
        log_data.update(details)
    
    if success:
        logger.info(f"Security event: {event_type}", extra=log_data)
    else:
        logger.warning(f"Security event failed: {event_type}", extra=log_data)


def log_performance_metric(
    operation: str,
    duration: float,
    success: bool,
    metadata: Optional[Dict[str, Any]] = None
):
    """パフォーマンスメトリクスをログに記録"""
    logger = LoggerFactory.get_logger("performance")
    
    log_data = {
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        "success": success
    }
    
    if metadata:
        log_data.update(metadata)
    
    logger.info(f"Performance metric: {operation}", extra=log_data)


def log_punch_event(
    employee_id: int,
    punch_type: str,
    success: bool,
    device_type: str = "unknown",
    processing_time: Optional[float] = None,
    error_message: Optional[str] = None
):
    """打刻イベントをログに記録"""
    logger = LoggerFactory.get_logger("punch")
    
    log_data = {
        "employee_id": employee_id,
        "punch_type": punch_type,
        "device_type": device_type,
        "success": success
    }
    
    if processing_time is not None:
        log_data["processing_time"] = processing_time
    
    if error_message:
        log_data["error_message"] = error_message
        logger.error("Punch event failed", extra=log_data)
    else:
        logger.info("Punch event recorded", extra=log_data)


# 初期化
LoggerFactory.setup()

# エクスポート
__all__ = [
    "LoggerFactory",
    "log_execution_time",
    "log_api_request",
    "log_security_event",
    "log_performance_metric",
    "log_punch_event",
]