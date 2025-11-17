import json
import logging
from io import StringIO

import pytest

from backend.app.utils.logging_config import (
    JSONFormatter,
    SecurityAuditFilter,
    log_performance_metric,
    log_security_event,
    log_punch_event,
)


def test_json_formatter_includes_extra_fields():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Hello",
        args=(),
        exc_info=None,
    )
    record.employee_id = 42
    record.punch_type = "in"
    formatted = formatter.format(record)
    payload = json.loads(formatted)

    assert payload["message"] == "Hello"
    assert payload["employee_id"] == 42
    assert payload["punch_type"] == "in"


def test_security_audit_filter_passes_security_messages():
    audit_filter = SecurityAuditFilter()
    allowed = logging.LogRecord("audit", logging.INFO, __file__, 10, "user login success", (), None)
    blocked = logging.LogRecord("audit", logging.INFO, __file__, 10, "heartbeat ok", (), None)

    assert audit_filter.filter(allowed) is True
    assert audit_filter.filter(blocked) is False


def test_log_performance_metric_emits_json(monkeypatch):
    logger = logging.getLogger("performance")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_performance_metric("sync_task", 0.123, True, {"extra": "value"})

    handler.flush()
    log_line = stream.getvalue().strip()
    payload = json.loads(log_line)
    assert payload["operation"] == "sync_task"
    assert payload["duration_ms"] == pytest.approx(123.0, rel=0.01)
    assert payload["extra"] == "value"


def test_log_security_event_writes_warning_for_failure():
    logger = logging.getLogger("backend.app.utils.logging_config")
    captured = []

    class _Capture(logging.Handler):
        def emit(self, record):
            captured.append(record)

    handler = _Capture()
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_security_event("AUTH_FAIL", user_id="u1", success=False, details="bad password")

    assert captured, "Expected at least one log record"
    record = captured[0]
    assert record.levelno == logging.WARNING
    assert "AUTH_FAIL" in record.getMessage()


def test_log_punch_event_outputs_json(monkeypatch):
    from backend.app.utils.logging_config import log_punch_event

    logger = logging.getLogger("punch")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_punch_event(
        employee_id=10,
        punch_type="in",
        success=True,
        processing_time=0.5,
    )

    handler.flush()
    log_line = stream.getvalue()
    assert "打刻成功" in log_line
    assert '"employee_id": 10' in log_line
