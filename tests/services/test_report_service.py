from datetime import datetime, date

import pytest

from backend.app.models import Employee, PunchRecord, PunchType, WageType
from backend.app.services.report_service import ReportService
from backend.app.schemas.report import (
    DailyReportResponse,
    DailySummaryData,
    DailyCalculations,
    PunchRecordResponse,
)


def _build_daily_report(employee_code="E001", employee_name="Report User", target_date=date(2025, 1, 1), minutes=480, overtime=60):
    summary = DailySummaryData(
        work_minutes=minutes,
        overtime_minutes=overtime,
        night_minutes=0,
        outside_minutes=0,
        break_minutes=0,
        actual_work_minutes=minutes,
    )
    calculations = DailyCalculations(
        regular_hours=minutes / 60.0,
        overtime_hours=overtime / 60.0,
        night_hours=0,
        basic_wage=10000 if minutes else 0,
        overtime_wage=2000 if overtime else 0,
        night_wage=0,
        total_wage=(10000 if minutes else 0) + (2000 if overtime else 0),
    )
    return DailyReportResponse(
        date=target_date,
        employee_id=employee_code,
        employee_name=employee_name,
        punch_records=[
            PunchRecordResponse(
                punch_type=PunchType.IN.value,
                timestamp=datetime.combine(target_date, datetime.min.time()),
                processed=True,
            )
        ],
        summary=summary,
        calculations=calculations,
    )


@pytest.fixture
def session(test_db):
    session = test_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_employee(session, code="E001"):
    employee = Employee(
        employee_code=code,
        name=f"Report User {code}",
        wage_type=WageType.MONTHLY,
        monthly_salary=300000,
        is_active=True,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def add_punches(session, employee_id):
    punches = [
        PunchRecord(
            employee_id=employee_id,
            punch_type=PunchType.IN.value,
            punch_time=datetime(2025, 1, 1, 9, 0),
        ),
        PunchRecord(
            employee_id=employee_id,
            punch_type=PunchType.OUT.value,
            punch_time=datetime(2025, 1, 1, 18, 0),
        ),
    ]
    session.add_all(punches)
    session.commit()


@pytest.mark.asyncio
async def test_calculate_daily_summary(session):
    employee = create_employee(session)
    add_punches(session, employee.id)
    service = ReportService(session)

    summary = await service._calculate_daily_summary(employee.id, date(2025, 1, 1))

    assert summary["employee_code"] == "E001"
    assert summary["clock_in_time"] == "09:00:00"
    assert summary["clock_out_time"] == "18:00:00"
    assert summary["overtime_minutes"] == 60
    assert summary["status"] == "退勤済"


@pytest.mark.asyncio
async def test_calculate_daily_summary_handles_breaks(session):
    employee = create_employee(session, code="E010")
    punches = [
        PunchRecord(
            employee_id=employee.id,
            punch_type=PunchType.IN.value,
            punch_time=datetime(2025, 1, 2, 9, 0),
        ),
        PunchRecord(
            employee_id=employee.id,
            punch_type=PunchType.OUTSIDE.value,
            punch_time=datetime(2025, 1, 2, 12, 0),
        ),
        PunchRecord(
            employee_id=employee.id,
            punch_type=PunchType.RETURN.value,
            punch_time=datetime(2025, 1, 2, 13, 0),
        ),
        PunchRecord(
            employee_id=employee.id,
            punch_type=PunchType.OUT.value,
            punch_time=datetime(2025, 1, 2, 18, 0),
        ),
    ]
    session.add_all(punches)
    session.commit()
    service = ReportService(session)

    summary = await service._calculate_daily_summary(employee.id, date(2025, 1, 2))

    assert summary["break_minutes"] == 60
    assert summary["actual_work_minutes"] == summary["work_minutes"] - 60


@pytest.mark.asyncio
async def test_export_monthly_report_csv_contains_data(session):
    employee = create_employee(session)
    add_punches(session, employee.id)
    service = ReportService(session)

    csv_text = await service.export_monthly_report_csv(2025, 1, employee.id)

    assert "E001" in csv_text
    assert "退勤済" in csv_text
    assert "実労働時間" in csv_text.splitlines()[0]


@pytest.mark.asyncio
async def test_generate_daily_reports_filters_by_employee_ids(session, monkeypatch):
    employee = create_employee(session)
    other = create_employee(session, "E002")
    service = ReportService(session)
    calls = []

    async def fake_daily(self, employee_obj, target_date):
        calls.append(employee_obj.employee_code)
        return _build_daily_report(employee_obj.employee_code, employee_obj.name, target_date, minutes=0, overtime=0)

    monkeypatch.setattr(ReportService, "_generate_employee_daily_report", fake_daily)

    reports = await service.generate_daily_reports(date(2025, 1, 2), employee_ids=[employee.employee_code])

    assert calls == [employee.employee_code]
    assert len(reports) == 1


@pytest.mark.asyncio
async def test_generate_employee_monthly_report_aggregates_minutes(session, monkeypatch):
    employee = create_employee(session)
    service = ReportService(session)

    async def fake_daily(self, employee_obj, current_date):
        worked = current_date.day <= 2
        return _build_daily_report(
            employee_obj.employee_code,
            employee_obj.name,
            current_date,
            minutes=480 if worked else 0,
            overtime=120 if worked else 0,
        )

    monkeypatch.setattr(ReportService, "_generate_employee_daily_report", fake_daily)

    report = await service._generate_employee_monthly_report(employee, 2025, 2)

    assert report.monthly_summary.work_days == 2
    assert report.wage_calculation.total_wage == 2 * (10000 + 2000)
    assert len(report.daily_breakdown) == 28


@pytest.mark.asyncio
async def test_generate_daily_summary_respects_employee_filter(session, monkeypatch):
    employee = create_employee(session)
    other = create_employee(session, "E002")
    service = ReportService(session)
    seen = []

    async def fake_summary(self, employee_id, target_date):
        seen.append(employee_id)
        return {"employee_id": employee_id, "date": target_date.isoformat()}

    monkeypatch.setattr(ReportService, "_calculate_daily_summary", fake_summary)

    summaries = await service.generate_daily_summary(date(2025, 1, 3), employee_id=other.id)

    assert summaries == [{"employee_id": other.id, "date": "2025-01-03"}]
    assert seen == [other.id]


@pytest.mark.asyncio
async def test_get_monthly_statistics_counts_work_days(session):
    employee = create_employee(session)
    for day in (1, 2):
        session.add(
            PunchRecord(
                employee_id=employee.id,
                punch_type=PunchType.IN.value,
                punch_time=datetime(2025, 2, day, 9, 0),
            )
        )
    session.commit()

    service = ReportService(session)
    stats = await service.get_monthly_statistics(2025, 2)

    assert stats["employees"][0]["work_days"] == 2
