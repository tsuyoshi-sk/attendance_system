from datetime import datetime, date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.models import Employee, PunchRecord, WageType, PunchType
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services import analytics_service as analytics_service_module
from backend.app.schemas.report import AttendanceStats, OvertimeAnalysis


class FakeReportService:
    def __init__(
        self,
        daily_minutes=480,
        overtime_minutes=60,
        monthly_reports=None,
        employee_id="E001",
        employee_name="Test User",
    ):
        self.employee_id = employee_id
        self.employee_name = employee_name
        summary = SimpleNamespace(
            actual_work_minutes=daily_minutes,
            overtime_minutes=overtime_minutes,
            night_minutes=0,
        )
        self._daily_report = SimpleNamespace(
            employee_id=self.employee_id,
            employee_name=self.employee_name,
            summary=summary,
        )
        default_monthly = [
            SimpleNamespace(
                employee_id=self.employee_id,
                employee_name=self.employee_name,
                monthly_summary=SimpleNamespace(
                    total_work_hours=160.0,
                    overtime_hours=10.0,
                )
            )
        ]
        self.monthly_reports = monthly_reports or default_monthly

    async def generate_daily_reports(self, target_date, employee_ids=None):
        return [self._daily_report]

    async def generate_monthly_reports(self, year, month, employee_ids=None):
        return self.monthly_reports


@pytest.fixture
def db_session(test_db):
    session = test_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_employee(session, code="E001"):
    employee = Employee(
        employee_code=code,
        name=f"Employee {code}",
        wage_type=WageType.MONTHLY,
        monthly_salary=300000,
        is_active=True,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@pytest.mark.asyncio
async def test_get_overtime_distribution_groups_hours(db_session):
    service = AnalyticsService(db_session)
    fake_reports = [
        SimpleNamespace(
            employee_id=f"E00{i}",
            employee_name=f"User {i}",
            monthly_summary=SimpleNamespace(overtime_hours=hours),
        )
        for i, hours in enumerate([5, 15, 25, 35, 45], start=1)
    ]
    service.report_service = FakeReportService(monthly_reports=fake_reports)

    chart = await service.get_overtime_distribution(2025, 1)

    assert chart.chart_type == "bar"
    assert chart.data["datasets"][0]["data"][0] == 1  # 0-10時間
    assert chart.data["datasets"][0]["data"][-1] == 1  # 40時間以上


@pytest.mark.asyncio
async def test_get_work_hours_trend_returns_average(db_session):
    service = AnalyticsService(db_session)
    monthly_reports = [
        SimpleNamespace(
            employee_id="E001",
            employee_name="Trend User",
            monthly_summary=SimpleNamespace(
                total_work_hours=160.0,
                overtime_hours=20.0,
            )
        )
    ]
    service.report_service = FakeReportService(monthly_reports=monthly_reports)

    chart = await service.get_work_hours_trend(months=2)

    assert chart.chart_type == "line"
    assert len(chart.data["labels"]) == 2
    assert len(chart.data["datasets"][0]["data"]) == 2


@pytest.mark.asyncio
async def test_get_attendance_rate_trend_uses_punch_records(db_session):
    employee = _create_employee(db_session)
    # Punch once this month
    today = date.today()
    punch_time = datetime(today.year, today.month, 1, 9, 0)
    db_session.add(
        PunchRecord(
            employee_id=employee.id,
            punch_type=PunchType.IN.value,
            punch_time=punch_time,
        )
    )
    db_session.commit()

    service = AnalyticsService(db_session)
    chart = await service.get_attendance_rate_trend(months=1)

    assert chart.chart_type == "line"
    assert len(chart.data["datasets"][0]["data"]) == 1
    assert chart.data["datasets"][0]["data"][0] >= 0


@pytest.mark.asyncio
async def test_get_statistics_aggregates_sections(db_session):
    service = AnalyticsService(db_session)
    service.report_service = FakeReportService()

    stats = await service.get_statistics(period="day")

    assert stats.attendance_stats.average_work_hours >= 0
    assert stats.overtime_analysis.total_overtime_hours >= 0
    assert stats.trend_analysis.work_hours_trend in {"stable", "increasing", "decreasing"}


@pytest.mark.asyncio
async def test_get_statistics_handles_week_and_year(db_session):
    service = AnalyticsService(db_session)
    service.report_service = FakeReportService()

    week_stats = await service.get_statistics(period="week")
    year_stats = await service.get_statistics(period="year", year=2024)

    assert week_stats.attendance_stats.average_work_hours >= 0
    assert year_stats.attendance_stats.max_work_hours >= 0


@pytest.mark.asyncio
async def test_get_statistics_month_defaults(db_session):
    service = AnalyticsService(db_session)
    service.report_service = FakeReportService()

    month_stats = await service.get_statistics(period="month")

    assert month_stats.attendance_stats.average_work_hours >= 0


@pytest.mark.asyncio
async def test_get_statistics_month_handles_december(monkeypatch, db_session):
    class DecemberDate(date):
        @classmethod
        def today(cls):
            return cls(2025, 12, 10)

    monkeypatch.setattr(analytics_service_module, "date", DecemberDate)

    service = AnalyticsService(db_session)
    service.report_service = FakeReportService()

    stats = await service.get_statistics(period="month")

    assert stats.overtime_analysis.total_overtime_hours >= 0


@pytest.mark.asyncio
async def test_get_dashboard_data_returns_sections(monkeypatch, db_session):
    employee = _create_employee(db_session, "E100")
    db_session.add(
        PunchRecord(
            employee_id=employee.id,
            punch_type=PunchType.IN.value,
            punch_time=datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=9),
        )
    )
    db_session.commit()

    service = AnalyticsService(db_session)
    service.report_service = FakeReportService()
    monkeypatch.setattr(service, "get_current_alerts", AsyncMock(return_value=[]))

    dashboard = await service.get_dashboard_data()

    assert dashboard.today_summary.total_employees >= 1
    assert dashboard.this_month["total_work_hours"] >= 0


@pytest.mark.asyncio
async def test_get_current_alerts_detects_overtime(db_session):
    service = AnalyticsService(db_session)
    service.alert_conditions["overtime_monthly"] = 1
    service.alert_conditions["continuous_overtime"] = 2
    fake = FakeReportService(
        monthly_reports=[
            SimpleNamespace(
                employee_id="E001",
                employee_name="Alert User",
                monthly_summary=SimpleNamespace(overtime_hours=50),
            )
        ]
    )
    fake._daily_report.summary.overtime_minutes = 180
    service.report_service = fake

    alerts = await service.get_current_alerts()

    types = {alert.type for alert in alerts}
    assert "overtime_alert" in types
    assert "daily_overtime" in types


@pytest.mark.asyncio
async def test_get_realtime_summary_counts_status(db_session):
    worker = _create_employee(db_session, "WORK")
    breaker = _create_employee(db_session, "BREAK")
    returner = _create_employee(db_session, "RET")

    db_session.add_all(
        [
            PunchRecord(
                employee_id=worker.id,
                punch_type=PunchType.IN.value,
                punch_time=datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=9),
            ),
            PunchRecord(
                employee_id=breaker.id,
                punch_type=PunchType.OUTSIDE.value,
                punch_time=datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=10),
            ),
            PunchRecord(
                employee_id=returner.id,
                punch_type=PunchType.RETURN.value,
                punch_time=datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=11),
            ),
        ]
    )
    db_session.commit()

    service = AnalyticsService(db_session)
    summary = await service.get_realtime_summary()

    assert summary["working_count"] == 2
    assert summary["break_count"] == 1


@pytest.mark.asyncio
async def test_calculate_attendance_stats_with_multiple_employees(db_session):
    _create_employee(db_session, "AVG1")
    _create_employee(db_session, "AVG2")

    service = AnalyticsService(db_session)
    service.report_service = FakeReportService()

    stats = await service._calculate_attendance_stats(date(2025, 1, 1), date(2025, 1, 1))

    assert stats.standard_deviation >= 0


@pytest.mark.asyncio
async def test_calculate_overtime_analysis_distribution(db_session, monkeypatch):
    codes = ["E100", "E101", "E102", "E103"]
    for code in codes:
        _create_employee(db_session, code)

    service = AnalyticsService(db_session)

    minutes_map = {
        "E100": 60,   # 1h -> 0-10h bucket
        "E101": 720,  # 12h -> 10-20h
        "E102": 1500, # 25h -> 20-30h
        "E103": 2100, # 35h -> 30h+
    }

    async def fake_daily(target_date, employee_ids=None):
        code = employee_ids[0]
        summary = SimpleNamespace(overtime_minutes=minutes_map[code])
        return [SimpleNamespace(summary=summary)]

    monkeypatch.setattr(service.report_service, "generate_daily_reports", fake_daily)

    analysis = await service._calculate_overtime_analysis(date(2025, 1, 1), date(2025, 1, 1))

    assert analysis.overtime_distribution == {
        "0-10h": 1,
        "10-20h": 1,
        "20-30h": 1,
        "30h+": 1,
    }


@pytest.mark.asyncio
async def test_trend_analysis_detects_changes(monkeypatch, db_session):
    service = AnalyticsService(db_session)

    async def fake_attendance(start, end):
        if start == date(2025, 1, 1):
            return AttendanceStats(average_work_hours=10, max_work_hours=10, min_work_hours=10, standard_deviation=0)
        return AttendanceStats(average_work_hours=5, max_work_hours=5, min_work_hours=5, standard_deviation=0)

    async def fake_overtime(start, end):
        if start == date(2025, 1, 1):
            return OvertimeAnalysis(total_overtime_hours=5, average_overtime_per_employee=5, overtime_distribution={})
        return OvertimeAnalysis(total_overtime_hours=20, average_overtime_per_employee=10, overtime_distribution={})

    monkeypatch.setattr(service, "_calculate_attendance_stats", fake_attendance)
    monkeypatch.setattr(service, "_calculate_overtime_analysis", fake_overtime)

    trend = await service._calculate_trend_analysis(date(2025, 1, 1), date(2025, 1, 1))

    assert trend.work_hours_trend == "increasing"
    assert trend.overtime_trend == "decreasing"


@pytest.mark.asyncio
async def test_check_consecutive_overtime_returns_value(monkeypatch, db_session):
    service = AnalyticsService(db_session)

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2025, 1, 5)

    monkeypatch.setattr(analytics_service_module, "date", FixedDate)

    async def fake_daily(target_date, employee_ids=None):
        if target_date >= FixedDate(2025, 1, 3):
            summary = SimpleNamespace(overtime_minutes=120)
            return [SimpleNamespace(summary=summary)]
        return []

    monkeypatch.setattr(service.report_service, "generate_daily_reports", fake_daily)

    result = await service._check_consecutive_overtime("E001", threshold_days=2)

    assert result == 3


@pytest.mark.asyncio
async def test_trend_analysis_detects_decreasing(monkeypatch, db_session):
    service = AnalyticsService(db_session)

    async def fake_attendance(start, end):
        if start == date(2025, 1, 1):
            return AttendanceStats(average_work_hours=5, max_work_hours=5, min_work_hours=5, standard_deviation=0)
        return AttendanceStats(average_work_hours=10, max_work_hours=10, min_work_hours=10, standard_deviation=0)

    async def fake_overtime(start, end):
        if start == date(2025, 1, 1):
            return OvertimeAnalysis(total_overtime_hours=20, average_overtime_per_employee=10, overtime_distribution={})
        return OvertimeAnalysis(total_overtime_hours=5, average_overtime_per_employee=5, overtime_distribution={})

    monkeypatch.setattr(service, "_calculate_attendance_stats", fake_attendance)
    monkeypatch.setattr(service, "_calculate_overtime_analysis", fake_overtime)

    trend = await service._calculate_trend_analysis(date(2025, 1, 1), date(2025, 1, 1))

    assert trend.work_hours_trend == "decreasing"
    assert trend.overtime_trend == "increasing"


@pytest.mark.asyncio
async def test_get_statistics_year_defaults(monkeypatch, db_session):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2025, 2, 1)

    monkeypatch.setattr(analytics_service_module, "date", FixedDate)

    service = AnalyticsService(db_session)
    service.report_service = FakeReportService()

    stats = await service.get_statistics(period="year")

    assert stats.attendance_stats.max_work_hours >= 0


@pytest.mark.asyncio
async def test_attendance_rate_trend_handles_december(monkeypatch, db_session):
    employee = _create_employee(db_session, "DEC")
    db_session.add(
        PunchRecord(
            employee_id=employee.id,
            punch_type=PunchType.IN.value,
            punch_time=datetime(2025, 12, 1, 9, 0),
        )
    )
    db_session.commit()

    class DecemberDate(date):
        @classmethod
        def today(cls):
            return cls(2025, 12, 15)

    monkeypatch.setattr(analytics_service_module, "date", DecemberDate)

    service = AnalyticsService(db_session)
    chart = await service.get_attendance_rate_trend(months=1)

    assert chart.data["labels"][0].startswith("2025-12")


@pytest.mark.asyncio
async def test_calculate_attendance_stats_with_multiple_employees(db_session):
    _create_employee(db_session, "AVG1")
    _create_employee(db_session, "AVG2")

    service = AnalyticsService(db_session)
    service.report_service = FakeReportService()

    stats = await service._calculate_attendance_stats(date(2025, 1, 1), date(2025, 1, 1))

    assert stats.standard_deviation >= 0
