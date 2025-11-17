import logging

import pytest

from backend.app.utils import logging_config
from backend.app.utils.logging_config import setup_logging, get_logger


def test_setup_logging_creates_files(tmp_path, monkeypatch):
    temp_dir = tmp_path / "logs"
    monkeypatch.setattr(logging_config.config, "LOG_DIR", str(temp_dir))
    monkeypatch.setattr(logging_config.config, "DEBUG", False)

    setup_logging()

    app_log = temp_dir / "app.log"
    error_log = temp_dir / "error.log"
    security_log = temp_dir / "security_audit.log"
    punch_log = temp_dir / "punch.log"
    assert app_log.exists()
    assert error_log.exists()
    assert security_log.exists()
    assert punch_log.exists()

    logger = get_logger("test_logger")
    logger.info("hello world")

    with app_log.open() as fh:
        contents = fh.read()
    assert "hello world" in contents


def test_log_punch_event_writes_json(tmp_path, monkeypatch):
    temp_dir = tmp_path / "logs"
    monkeypatch.setattr(logging_config.config, "LOG_DIR", str(temp_dir))
    monkeypatch.setattr(logging_config.config, "DEBUG", False)
    setup_logging()

    logging_config.log_punch_event(
        employee_id=99,
        punch_type="in",
        success=True,
        processing_time=0.42,
    )

    punch_log = temp_dir / "punch.log"
    with punch_log.open() as fh:
        lines = [line for line in fh.read().splitlines() if line]

    assert lines, "expected punch log to contain entries"
    assert "打刻成功" in lines[-1]
