import sqlite3
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.app.utils import offline_queue
from backend.app.utils.offline_queue import OfflineQueueManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    mock_config = SimpleNamespace(
        SLACK_ENABLED=False,
        SLACK_TOKEN="",
        DATA_DIR=str(tmp_path),
    )
    monkeypatch.setattr(offline_queue, "config", mock_config)
    db_path = tmp_path / "offline_queue.db"
    return OfflineQueueManager(db_path=str(db_path))


def sample_punch(card_suffix="001"):
    return {
        "employee_id": "E001",
        "punch_type": "in",
        "card_idm": f"card{card_suffix}",
        "timestamp": datetime(2025, 1, 1, 9, 0).isoformat(),
        "device_type": "pasori",
        "ip_address": "127.0.0.1",
        "location": {"latitude": 35.0, "longitude": 139.0},
        "note": "offline",
    }


def test_add_and_get_pending_punches(manager):
    assert manager.add_punch(sample_punch())

    pending = manager.get_pending_punches()
    assert len(pending) == 1
    assert pending[0]["employee_id"] == "E001"


def test_mark_as_synced_and_duplicate_handling(manager):
    manager.add_punch(sample_punch())
    pending = manager.get_pending_punches()
    record_id = pending[0]["id"]

    assert manager.mark_as_synced(record_id) is True
    # After deletion we can add same punch again
    assert manager.add_punch(sample_punch()) is True
    # Duplicate insert without removal should be ignored (row count stays 1)
    manager.add_punch(sample_punch())
    pending = manager.get_pending_punches()
    assert len(pending) == 1


def test_update_retry_status(manager):
    manager.add_punch(sample_punch())
    record = manager.get_pending_punches()[0]

    assert manager.update_retry_status(record["id"], "network error")
    updated = manager.get_pending_punches()[0]
    assert updated["retry_count"] == 1
    assert "network error" in updated["error_message"]


def test_cleanup_old_records_removes_outdated_entries(manager):
    manager.add_punch(sample_punch())
    record = manager.get_pending_punches()[0]

    with sqlite3.connect(manager.db_path) as conn:
        conn.execute(
            "UPDATE offline_punches SET created_at = ? WHERE id = ?",
            ((datetime.now() - timedelta(days=10)).isoformat(), record["id"]),
        )
        conn.commit()

    manager._cleanup_old_records()
    assert manager.get_pending_punches() == []


def test_get_stats_reports_queue_usage(manager):
    manager.add_punch(sample_punch("100"))
    manager.add_punch(sample_punch("200"))
    pending = manager.get_pending_punches()
    manager.update_retry_status(pending[0]["id"], "net err")
    manager.update_retry_status(pending[0]["id"], "net err")
    stats = manager.get_stats()

    assert stats["total_pending"] == 2
    assert stats["failed_records"] == 0
    assert stats["queue_usage"].endswith("%")


@pytest.fixture
def slack_manager(tmp_path, monkeypatch):
    fake_client = MagicMock()
    mock_config = SimpleNamespace(
        SLACK_ENABLED=True,
        SLACK_TOKEN="xoxb-test",
        SLACK_CHANNEL="#alerts",
        DATA_DIR=str(tmp_path),
    )
    monkeypatch.setattr(offline_queue, "config", mock_config)
    monkeypatch.setattr(offline_queue, "WebClient", lambda token: fake_client)
    manager = OfflineQueueManager()
    manager.slack_client = fake_client
    try:
        yield manager, fake_client, mock_config
    finally:
        manager.cleanup()


def test_send_slack_notification_uses_client(slack_manager):
    manager, fake_client, mock_config = slack_manager

    manager._send_slack_notification("hello")

    fake_client.chat_postMessage.assert_called_once_with(
        channel=mock_config.SLACK_CHANNEL,
        text="hello",
    )


def test_send_slack_notification_handles_error(slack_manager):
    manager, fake_client, mock_config = slack_manager
    fake_client.chat_postMessage.side_effect = offline_queue.SlackApiError(
        message="boom",
        response={"error": "boom"},
    )

    manager._send_slack_notification("hello")

    fake_client.chat_postMessage.assert_called_once()


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self._target = target

    def start(self):
        self._target()

    def join(self, timeout=None):
        return None

    def is_alive(self):
        return False


def test_sync_thread_processes_success_and_failures(manager, monkeypatch):
    monkeypatch.setattr(offline_queue, "Thread", ImmediateThread)
    manager.SYNC_INTERVAL = 0
    manager.add_punch(sample_punch("201"))
    manager.add_punch(sample_punch("202"))

    processed = []

    def sync_callback(punch):
        processed.append(punch["id"])
        if len(processed) == 2:
            manager.stop_event.set()
        return len(processed) == 1

    manager.start_sync_thread(sync_callback)
    manager.stop_sync_thread()

    pending = manager.get_pending_punches()
    assert len(pending) == 1
    assert pending[0]["retry_count"] == 1


def test_sync_thread_sends_slack_on_many_failures(manager, monkeypatch):
    monkeypatch.setattr(offline_queue, "Thread", ImmediateThread)
    manager.SYNC_INTERVAL = 0
    total = 6
    for idx in range(total):
        manager.add_punch(sample_punch(f"30{idx}"))

    processed = []
    manager._send_slack_notification = MagicMock()

    def failing_callback(punch):
        processed.append(punch["id"])
        if len(processed) == total:
            manager.stop_event.set()
        return False

    manager.start_sync_thread(failing_callback)
    manager.stop_sync_thread()

    manager._send_slack_notification.assert_called_once()


def test_default_db_path_and_memory_fallback(tmp_path, monkeypatch):
    mock_config = SimpleNamespace(
        SLACK_ENABLED=False,
        SLACK_TOKEN="",
        DATA_DIR="",
    )
    monkeypatch.setattr(offline_queue, "config", mock_config)
    monkeypatch.chdir(tmp_path)
    original_init = OfflineQueueManager._init_database
    calls = {"count": 0}

    def flaky_init(self):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("fail")
        return original_init(self)

    monkeypatch.setattr(OfflineQueueManager, "_init_database", flaky_init)

    manager = OfflineQueueManager()
    try:
        assert manager.db_path == ":memory:"
    finally:
        manager.cleanup()


def test_add_punch_evicts_oldest_when_queue_full(manager):
    manager.MAX_QUEUE_SIZE = 1
    manager.add_punch(sample_punch("801"))
    manager.add_punch(sample_punch("802"))

    pending = manager.get_pending_punches(limit=10)
    assert len(pending) == 1
    assert pending[0]["card_idm_hash"] == "card802"


def test_start_sync_thread_noop_when_already_running(manager):
    manager.is_running = True
    manager.start_sync_thread(lambda punch: True)
    assert manager.is_running is True
    manager.is_running = False


def test_sync_thread_updates_retry_on_exception(manager, monkeypatch):
    monkeypatch.setattr(offline_queue, "Thread", ImmediateThread)
    manager.SYNC_INTERVAL = 0
    manager.add_punch(sample_punch("901"))

    def raising_callback(punch):
        manager.stop_event.set()
        raise RuntimeError("boom")

    manager.start_sync_thread(raising_callback)
    manager.stop_sync_thread()

    pending = manager.get_pending_punches()
    assert pending[0]["retry_count"] == 1


class PersistentThread:
    def __init__(self, target, daemon=False):
        self._target = target

    def start(self):
        self._target()

    def join(self, timeout=None):
        return None

    def is_alive(self):
        return True


def test_stop_sync_thread_logs_when_thread_alive(manager, monkeypatch):
    monkeypatch.setattr(offline_queue, "Thread", PersistentThread)
    manager.SYNC_INTERVAL = 0
    manager.add_punch(sample_punch("910"))

    def callback(punch):
        manager.stop_event.set()
        return True

    manager.start_sync_thread(callback)
    manager.stop_sync_thread()
    assert manager.is_running is False


def test_sync_thread_triggers_cleanup_check(manager, monkeypatch):
    monkeypatch.setattr(offline_queue, "Thread", ImmediateThread)
    manager.SYNC_INTERVAL = 1
    manager.add_punch(sample_punch("920"))
    manager._cleanup_old_records = MagicMock()
    monkeypatch.setattr(offline_queue.time, "time", lambda: 0)
    monkeypatch.setattr(manager.stop_event, "wait", lambda timeout: None)

    def callback(punch):
        manager.stop_event.set()
        return True

    manager.start_sync_thread(callback)
    manager.stop_sync_thread()

    manager._cleanup_old_records.assert_called()


def test_init_database_creates_directory_and_file(tmp_path, monkeypatch):
    mock_config = SimpleNamespace(
        SLACK_ENABLED=False,
        SLACK_TOKEN="",
        DATA_DIR=str(tmp_path),
    )
    monkeypatch.setattr(offline_queue, "config", mock_config)
    db_path = tmp_path / "nested" / "offline.db"
    original_connect = offline_queue.sqlite3.connect
    calls = {"count": 0}

    def flaky_connect(path, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise offline_queue.sqlite3.OperationalError("fail")
        return original_connect(path, *args, **kwargs)

    monkeypatch.setattr(offline_queue.sqlite3, "connect", flaky_connect)

    manager = OfflineQueueManager(db_path=str(db_path))
    try:
        assert db_path.parent.exists()
        assert db_path.exists()
    finally:
        manager.cleanup()


def test_add_punch_handles_general_exception(manager, monkeypatch):
    def failing_connect(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(offline_queue.sqlite3, "connect", failing_connect)
    result = manager.add_punch(sample_punch("930"))
    assert result is False


def test_get_pending_punches_handles_exception(manager, monkeypatch):
    def failing_connect(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(offline_queue.sqlite3, "connect", failing_connect)
    assert manager.get_pending_punches() == []


def test_mark_as_synced_handles_exception(manager, monkeypatch):
    def failing_connect(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(offline_queue.sqlite3, "connect", failing_connect)
    assert manager.mark_as_synced(1) is False


def test_update_retry_status_handles_exception(manager, monkeypatch):
    def failing_connect(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(offline_queue.sqlite3, "connect", failing_connect)
    assert manager.update_retry_status(1, "err") is False


def test_sync_thread_handles_outer_exception(manager, monkeypatch):
    monkeypatch.setattr(offline_queue, "Thread", ImmediateThread)
    manager.SYNC_INTERVAL = 0

    def failing_pending():
        manager.stop_event.set()
        raise RuntimeError("boom")

    manager.get_pending_punches = failing_pending  # type: ignore

    manager.start_sync_thread(lambda punch: True)
    manager.stop_sync_thread()


def test_send_slack_notification_returns_when_not_configured(manager):
    assert manager.slack_client is None
    assert manager._send_slack_notification("hello") is None


def test_get_stats_handles_exception(manager, monkeypatch):
    def failing_connect(*args, **kwargs):
        raise RuntimeError("stats fail")

    monkeypatch.setattr(offline_queue.sqlite3, "connect", failing_connect)
    stats = manager.get_stats()
    assert "error" in stats


def test_add_punch_handles_integrity_error(manager, monkeypatch):
    class FakeResult:
        def fetchone(self):
            return (0,)

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, *params):
            if "INSERT" in sql:
                raise offline_queue.sqlite3.IntegrityError("dup")
            return FakeResult()

        def commit(self):
            return None

    monkeypatch.setattr(offline_queue.sqlite3, "connect", lambda *args, **kwargs: FakeConn())
    assert manager.add_punch(sample_punch("dup")) is False


def test_init_database_handles_operational_error(tmp_path, monkeypatch):
    mock_config = SimpleNamespace(
        SLACK_ENABLED=False,
        SLACK_TOKEN="",
        DATA_DIR=str(tmp_path),
    )
    monkeypatch.setattr(offline_queue, "config", mock_config)
    db_path = tmp_path / "ops" / "offline.db"
    manager = OfflineQueueManager(db_path=str(db_path))

    original_connect = offline_queue.sqlite3.connect
    calls = {"count": 0}

    def flaky_connect(path, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise offline_queue.sqlite3.OperationalError("fail")
        return original_connect(path, *args, **kwargs)

    monkeypatch.setattr(offline_queue.sqlite3, "connect", flaky_connect)

    manager._init_database()
    assert db_path.exists()


def test_offline_queue_init_handles_operational_error(tmp_path, monkeypatch):
    mock_config = SimpleNamespace(
        SLACK_ENABLED=False,
        SLACK_TOKEN="",
        DATA_DIR=str(tmp_path),
    )
    monkeypatch.setattr(offline_queue, "config", mock_config)
    db_path = tmp_path / "ops2" / "offline.db"
    original_connect = offline_queue.sqlite3.connect
    calls = {"count": 0}

    def flaky_connect(path, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise offline_queue.sqlite3.OperationalError("fail")
        return original_connect(path, *args, **kwargs)

    monkeypatch.setattr(offline_queue.sqlite3, "connect", flaky_connect)

    manager = OfflineQueueManager(db_path=str(db_path))
    try:
        assert db_path.exists()
    finally:
        manager.cleanup()
