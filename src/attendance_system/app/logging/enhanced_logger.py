"""
Enhanced Structured Logging System

Comprehensive logging with:
- Structured JSON logging
- Security event tracking
- Performance metrics logging
- Audit trail support
"""

import logging
import json
import time
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from pythonjsonlogger import jsonlogger
import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level
import hashlib
from contextvars import ContextVar
import asyncio
from pathlib import Path
import aiofiles
from collections import deque
import gzip

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
client_id_var: ContextVar[Optional[str]] = ContextVar("client_id", default=None)


class SecurityLogFilter:
    """Filter sensitive information from logs"""

    SENSITIVE_FIELDS = {
        "password",
        "token",
        "api_key",
        "secret",
        "card_id",
        "idm",
        "ssn",
        "credit_card",
        "cvv",
        "pin",
        "private_key",
    }

    @staticmethod
    def filter_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively filter sensitive data from dictionary"""
        filtered = {}

        for key, value in data.items():
            # Check if key contains sensitive field
            if any(
                sensitive in key.lower()
                for sensitive in SecurityLogFilter.SENSITIVE_FIELDS
            ):
                if isinstance(value, str) and len(value) > 4:
                    # Partially mask the value
                    filtered[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                else:
                    filtered[key] = "***"
            elif isinstance(value, dict):
                filtered[key] = SecurityLogFilter.filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [
                    SecurityLogFilter.filter_dict(item)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                filtered[key] = value

        return filtered


class PerformanceLogger:
    """Log performance metrics"""

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
        self.metrics_buffer = deque(maxlen=1000)

    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time_ms: float,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Log API request performance"""
        self.logger.info(
            "api_request",
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=round(response_time_ms, 2),
            request_size=request_size,
            response_size=response_size,
            performance_category="api",
        )

        # Buffer for batch analysis
        self.metrics_buffer.append(
            {
                "timestamp": time.time(),
                "response_time_ms": response_time_ms,
                "path": path,
            }
        )

    def log_database_query(
        self,
        query_type: str,
        table: str,
        execution_time_ms: float,
        rows_affected: int = 0,
    ):
        """Log database query performance"""
        self.logger.info(
            "database_query",
            query_type=query_type,
            table=table,
            execution_time_ms=round(execution_time_ms, 2),
            rows_affected=rows_affected,
            performance_category="database",
        )

    def log_websocket_message(
        self,
        message_type: str,
        client_id: str,
        processing_time_ms: float,
        message_size: int = 0,
    ):
        """Log WebSocket message performance"""
        self.logger.info(
            "websocket_message",
            message_type=message_type,
            client_id=client_id,
            processing_time_ms=round(processing_time_ms, 2),
            message_size=message_size,
            performance_category="websocket",
        )

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary from buffer"""
        if not self.metrics_buffer:
            return {}

        response_times = [m["response_time_ms"] for m in self.metrics_buffer]

        return {
            "avg_response_time_ms": sum(response_times) / len(response_times),
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times),
            "total_requests": len(response_times),
        }


class SecurityLogger:
    """Log security-related events"""

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger

    def log_nfc_scan_attempt(
        self,
        card_id: str,
        success: bool,
        client_id: str,
        error_message: Optional[str] = None,
    ):
        """Log NFC scan attempt"""
        # Hash card ID for privacy
        card_id_hash = hashlib.sha256(card_id.encode()).hexdigest()[:16]

        self.logger.info(
            "nfc_scan_attempt",
            card_id_hash=card_id_hash,
            success=success,
            client_id=client_id,
            error_message=error_message,
            event_type="nfc_scan",
            security_category="access",
        )

    def log_authentication_attempt(
        self,
        user_id: str,
        method: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log authentication attempt"""
        self.logger.info(
            "authentication_attempt",
            user_id=user_id,
            method=method,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            event_type="authentication",
            security_category="auth",
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
        threat_level: Optional[str] = None,
    ):
        """Log generic security event"""
        # Filter sensitive data
        filtered_details = SecurityLogFilter.filter_dict(details)

        log_method = (
            self.logger.warning
            if severity in ["HIGH", "CRITICAL"]
            else self.logger.info
        )

        log_method(
            "security_event",
            event_type=event_type,
            severity=severity,
            details=filtered_details,
            threat_level=threat_level,
            security_category="incident",
        )

    def log_access_control(
        self,
        resource: str,
        action: str,
        user_id: str,
        granted: bool,
        reason: Optional[str] = None,
    ):
        """Log access control decision"""
        self.logger.info(
            "access_control",
            resource=resource,
            action=action,
            user_id=user_id,
            granted=granted,
            reason=reason,
            event_type="access_control",
            security_category="authorization",
        )


class AuditLogger:
    """Comprehensive audit logging"""

    def __init__(self, logger: structlog.BoundLogger, audit_dir: str = "logs/audit"):
        self.logger = logger
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = None
        self.current_date = None

    async def log_audit_event(
        self,
        category: str,
        action: str,
        actor: str,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        result: str = "success",
    ):
        """Log audit event asynchronously"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": category,
            "action": action,
            "actor": actor,
            "target": target,
            "details": details or {},
            "result": result,
            "request_id": request_id_var.get(),
            "session_id": client_id_var.get(),
        }

        # Log to structured logger
        self.logger.info("audit_event", **event)

        # Write to audit file
        await self._write_to_audit_file(event)

    async def _write_to_audit_file(self, event: Dict[str, Any]):
        """Write event to daily audit file"""
        current_date = datetime.utcnow().date()

        # Rotate file if date changed
        if current_date != self.current_date:
            if self.current_file:
                await self.current_file.close()

            filename = self.audit_dir / f"audit_{current_date.isoformat()}.jsonl"
            self.current_file = await aiofiles.open(filename, "a")
            self.current_date = current_date

        # Write event
        if self.current_file:
            await self.current_file.write(json.dumps(event) + "\n")
            await self.current_file.flush()

    async def compress_old_audit_files(self, days_to_keep: int = 7):
        """Compress audit files older than specified days"""
        cutoff_date = datetime.utcnow().date() - timedelta(days=days_to_keep)

        for file_path in self.audit_dir.glob("audit_*.jsonl"):
            # Extract date from filename
            try:
                file_date = datetime.strptime(
                    file_path.stem.replace("audit_", ""), "%Y-%m-%d"
                ).date()

                if file_date < cutoff_date:
                    # Compress file
                    compressed_path = file_path.with_suffix(".jsonl.gz")

                    async with aiofiles.open(file_path, "rb") as f_in:
                        content = await f_in.read()

                    with gzip.open(compressed_path, "wb") as f_out:
                        f_out.write(content)

                    # Remove original file
                    file_path.unlink()

                    self.logger.info(
                        "audit_file_compressed",
                        file=str(file_path),
                        compressed_file=str(compressed_path),
                    )
            except Exception as e:
                self.logger.error(
                    "audit_file_compression_error", file=str(file_path), error=str(e)
                )


class EnhancedLogger:
    """Main enhanced logging system"""

    def __init__(
        self,
        app_name: str = "attendance_system",
        log_level: str = "INFO",
        enable_console: bool = True,
        enable_file: bool = True,
        log_dir: str = "logs",
    ):
        self.app_name = app_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configure structlog
        self._configure_structlog()

        # Get logger
        self.logger = structlog.get_logger(app_name)

        # Initialize specialized loggers
        self.performance = PerformanceLogger(self.logger)
        self.security = SecurityLogger(self.logger)
        self.audit = AuditLogger(self.logger)

        # Configure Python logging
        if enable_console or enable_file:
            self._configure_python_logging(log_level, enable_console, enable_file)

    def _configure_structlog(self):
        """Configure structlog processors"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                TimeStamper(fmt="iso"),
                self._add_context_vars,
                self._add_app_info,
                SecurityLogFilter.filter_dict,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def _add_context_vars(self, logger, method_name, event_dict):
        """Add context variables to log entries"""
        if request_id := request_id_var.get():
            event_dict["request_id"] = request_id
        if user_id := user_id_var.get():
            event_dict["user_id"] = user_id
        if client_id := client_id_var.get():
            event_dict["client_id"] = client_id
        return event_dict

    def _add_app_info(self, logger, method_name, event_dict):
        """Add application information to log entries"""
        event_dict["app_name"] = self.app_name
        event_dict["environment"] = "production"  # Could be from config
        return event_dict

    def _configure_python_logging(
        self, log_level: str, enable_console: bool, enable_file: bool
    ):
        """Configure Python logging handlers"""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # Remove existing handlers
        root_logger.handlers = []

        # JSON formatter
        json_formatter = jsonlogger.JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s", timestamp=True
        )

        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(json_formatter)
            root_logger.addHandler(console_handler)

        # File handler with rotation
        if enable_file:
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                self.log_dir / f"{self.app_name}.log",
                maxBytes=100 * 1024 * 1024,  # 100MB
                backupCount=10,
            )
            file_handler.setFormatter(json_formatter)
            root_logger.addHandler(file_handler)

            # Error file handler
            error_handler = RotatingFileHandler(
                self.log_dir / f"{self.app_name}_errors.log",
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=5,
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(json_formatter)
            root_logger.addHandler(error_handler)

    def set_context(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ):
        """Set logging context variables"""
        if request_id:
            request_id_var.set(request_id)
        if user_id:
            user_id_var.set(user_id)
        if client_id:
            client_id_var.set(client_id)

    def clear_context(self):
        """Clear logging context variables"""
        request_id_var.set(None)
        user_id_var.set(None)
        client_id_var.set(None)

    def log_exception(self, exc: Exception, context: Optional[Dict[str, Any]] = None):
        """Log exception with full traceback"""
        exc_info = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
            "context": context or {},
        }

        self.logger.error("unhandled_exception", **exc_info)

    def create_child_logger(self, name: str) -> structlog.BoundLogger:
        """Create a child logger with inherited context"""
        return self.logger.bind(logger_name=name)


# Global logger instance
enhanced_logger = EnhancedLogger()


# Convenience functions
def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance"""
    return enhanced_logger.create_child_logger(name)


def log_api_request(method: str, path: str, status_code: int, response_time_ms: float):
    """Log API request"""
    enhanced_logger.performance.log_api_request(
        method, path, status_code, response_time_ms
    )


def log_security_event(event_type: str, severity: str, details: Dict[str, Any]):
    """Log security event"""
    enhanced_logger.security.log_security_event(event_type, severity, details)


async def log_audit_event(category: str, action: str, actor: str, **kwargs):
    """Log audit event"""
    await enhanced_logger.audit.log_audit_event(category, action, actor, **kwargs)


# Decorators for automatic logging
def log_performance(category: str = "function"):
    """Decorator to log function performance"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                enhanced_logger.logger.info(
                    "function_performance",
                    function=func.__name__,
                    category=category,
                    execution_time_ms=round(execution_time, 2),
                    success=True,
                )
                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                enhanced_logger.logger.error(
                    "function_performance",
                    function=func.__name__,
                    category=category,
                    execution_time_ms=round(execution_time, 2),
                    success=False,
                    error=str(e),
                )
                raise

        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                enhanced_logger.logger.info(
                    "function_performance",
                    function=func.__name__,
                    category=category,
                    execution_time_ms=round(execution_time, 2),
                    success=True,
                )
                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                enhanced_logger.logger.error(
                    "function_performance",
                    function=func.__name__,
                    category=category,
                    execution_time_ms=round(execution_time, 2),
                    success=False,
                    error=str(e),
                )
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def log_security_action(action: str):
    """Decorator to log security-sensitive actions"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            actor = user_id_var.get() or "system"
            try:
                result = await func(*args, **kwargs)
                await enhanced_logger.audit.log_audit_event(
                    category="security",
                    action=action,
                    actor=actor,
                    result="success",
                    details={"function": func.__name__},
                )
                return result
            except Exception as e:
                await enhanced_logger.audit.log_audit_event(
                    category="security",
                    action=action,
                    actor=actor,
                    result="failure",
                    details={"function": func.__name__, "error": str(e)},
                )
                raise

        def sync_wrapper(*args, **kwargs):
            actor = user_id_var.get() or "system"
            try:
                result = func(*args, **kwargs)
                asyncio.create_task(
                    enhanced_logger.audit.log_audit_event(
                        category="security",
                        action=action,
                        actor=actor,
                        result="success",
                        details={"function": func.__name__},
                    )
                )
                return result
            except Exception as e:
                asyncio.create_task(
                    enhanced_logger.audit.log_audit_event(
                        category="security",
                        action=action,
                        actor=actor,
                        result="failure",
                        details={"function": func.__name__, "error": str(e)},
                    )
                )
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
