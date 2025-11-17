import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock

from backend.app.services.notification_service import NotificationService
from backend.app.services import notification_service as notification_service_module


@pytest.mark.asyncio
async def test_send_slack_notification_returns_false_without_webhook():
    service = NotificationService()
    service.slack_webhook_url = None  # 明示的に未設定にする

    result = await service.send_slack_notification(
        channel="#test",
        title="Test",
        message="No webhook configured",
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_admin_notification_maps_severity_to_color():
    service = NotificationService()
    service.send_slack_notification = AsyncMock(return_value=True)

    await service.send_admin_notification(
        title="Alert",
        message="Needs attention",
        severity="error",
    )

    service.send_slack_notification.assert_awaited_once()
    kwargs = service.send_slack_notification.await_args.kwargs
    assert kwargs["channel"] == service.admin_channel
    assert kwargs["color"] == "danger"


@pytest.mark.asyncio
async def test_send_daily_alerts_groups_alerts_into_fields():
    service = NotificationService()
    service.send_slack_notification = AsyncMock(return_value=True)

    alerts = [
        {"type": "overtime", "employee": "Alice", "message": "4h overtime"},
        {"type": "overtime", "employee": "Bob", "message": "3h overtime"},
        {"type": "missing_punch", "employee": "Carol", "message": "Missing OUT"},
    ]

    await service.send_daily_alerts(date(2025, 1, 1), alerts)

    service.send_slack_notification.assert_awaited_once()
    kwargs = service.send_slack_notification.await_args.kwargs
    assert kwargs["color"] == "warning"
    fields = kwargs["fields"]
    titles = {field["title"] for field in fields}
    assert any("長時間労働" in title for title in titles)
    assert any("打刻漏れ" in title for title in titles)


@pytest.mark.asyncio
async def test_send_monthly_alerts_sets_color_by_severity():
    service = NotificationService()
    service.send_slack_notification = AsyncMock(return_value=True)

    alerts = [
        {"type": "overtime", "employee": "Alice", "message": "Exceeded", "severity": "error"},
        {"type": "missing_punch", "employee": "Bob", "message": "Warning", "severity": "warning"},
        {"type": "info", "employee": "Carol", "message": "FYI", "severity": "info"},
    ]

    await service.send_monthly_alerts(2025, 1, alerts)

    kwargs = service.send_slack_notification.await_args.kwargs
    assert kwargs["color"] == "danger"
    field_titles = {field["title"] for field in kwargs["fields"]}
    assert any("重要アラート" in title for title in field_titles)
    assert any("警告" in title for title in field_titles)


@pytest.mark.asyncio
async def test_send_overtime_alert_monthly_sets_danger_color():
    service = NotificationService()
    service.send_slack_notification = AsyncMock(return_value=True)

    await service.send_overtime_alert("Alice", 65.0, period="monthly")

    kwargs = service.send_slack_notification.await_args.kwargs
    assert kwargs["color"] == "danger"
    assert any(field["title"] == "残業時間" for field in kwargs["fields"])


@pytest.mark.asyncio
async def test_send_batch_error_notification_includes_additional_info():
    service = NotificationService()
    service.send_slack_notification = AsyncMock(return_value=True)

    await service.send_batch_error_notification(
        batch_type="daily",
        error_message="Boom!",
        additional_info={"job_id": 42},
    )

    kwargs = service.send_slack_notification.await_args.kwargs
    fields = kwargs["fields"]
    assert any(field["title"] == "job_id" and field["value"] == "42" for field in fields)


class _DummyResponse:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummySession:
    def __init__(self, status=200, raise_error=False):
        self._status = status
        self._raise_error = raise_error
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url, **kwargs):
        self.post_calls.append({"url": url, **kwargs})
        if self._raise_error:
            raise RuntimeError("network error")
        return _DummyResponse(self._status)


@pytest.mark.asyncio
async def test_send_slack_notification_success(monkeypatch):
    service = NotificationService()
    service.slack_webhook_url = "https://example.com/webhook"

    dummy_session = _DummySession(status=200)
    monkeypatch.setattr(
        notification_service_module.aiohttp,
        "ClientSession",
        lambda: dummy_session,
    )

    result = await service.send_slack_notification(
        channel="#alerts",
        title="OK",
        message="all good",
        fields=[{"title": "field", "value": "value"}],
    )

    assert result is True
    assert dummy_session.post_calls[0]["url"] == "https://example.com/webhook"


@pytest.mark.asyncio
async def test_send_slack_notification_handles_failure(monkeypatch):
    service = NotificationService()
    service.slack_webhook_url = "https://example.com/webhook"

    dummy_session = _DummySession(status=500)
    monkeypatch.setattr(
        notification_service_module.aiohttp,
        "ClientSession",
        lambda: dummy_session,
    )

    result = await service.send_slack_notification(
        channel="#alerts",
        title="NG",
        message="failed request",
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_slack_notification_handles_exception(monkeypatch):
    service = NotificationService()
    service.slack_webhook_url = "https://example.com/webhook"

    dummy_session = _DummySession(status=200, raise_error=True)
    monkeypatch.setattr(
        notification_service_module.aiohttp,
        "ClientSession",
        lambda: dummy_session,
    )

    result = await service.send_slack_notification(
        channel="#alerts",
        title="Boom",
        message="raises",
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_daily_alerts_returns_when_empty():
    service = NotificationService()
    service.send_slack_notification = AsyncMock(return_value=True)

    await service.send_daily_alerts(date(2025, 1, 1), [])

    service.send_slack_notification.assert_not_called()


@pytest.mark.asyncio
async def test_send_monthly_alerts_truncates_warnings():
    service = NotificationService()
    service.send_slack_notification = AsyncMock(return_value=True)

    warning_alerts = [
        {"type": "warn", "employee": f"E{i}", "message": "warn", "severity": "warning"}
        for i in range(12)
    ]

    await service.send_monthly_alerts(2025, 2, warning_alerts)

    kwargs = service.send_slack_notification.await_args.kwargs
    assert kwargs["color"] == "warning"
    warning_field = next(field for field in kwargs["fields"] if "警告" in field["title"])
    assert "... 他2件" in warning_field["value"]


@pytest.mark.asyncio
async def test_send_overtime_alert_daily_branch():
    service = NotificationService()
    service.send_slack_notification = AsyncMock(return_value=True)

    await service.send_overtime_alert("Alice", 2.5, period="daily")

    kwargs = service.send_slack_notification.await_args.kwargs
    assert kwargs["color"] == "warning"
    assert "日次残業" in kwargs["title"]


@pytest.mark.asyncio
async def test_send_punch_notification_uses_realtime_channel():
    service = NotificationService()
    service.send_slack_notification = AsyncMock(return_value=True)

    await service.send_punch_notification(
        employee_name="Alice",
        punch_type="in",
        punch_time=datetime(2025, 1, 1, 9, 0, 0),
    )

    service.send_slack_notification.assert_awaited_once()
    kwargs = service.send_slack_notification.await_args.kwargs
    assert kwargs["channel"] == service.realtime_channel
    assert kwargs["title"] == "打刻通知"
