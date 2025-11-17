import csv
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from backend.app.services.export_service import ExportService


class FakeReportService:
    def __init__(self):
        self.daily_report = SimpleNamespace(
            date=date(2025, 1, 1),
            employee_id="E001",
            employee_name="Alice",
            calculations=SimpleNamespace(
                regular_hours=8.0,
                overtime_hours=2.0,
                night_hours=1.0,
                basic_wage=20000,
                overtime_wage=5000,
                night_wage=1000,
                total_wage=26000,
            ),
            punch_records=[
                SimpleNamespace(punch_type="in", timestamp=datetime(2025, 1, 1, 9, 0)),
                SimpleNamespace(punch_type="out", timestamp=datetime(2025, 1, 1, 18, 0)),
            ],
            summary=SimpleNamespace(
                break_minutes=60,
                outside_minutes=0,
                actual_work_minutes=600,
                overtime_minutes=150,
                night_minutes=0,
            ),
        )
        self.monthly_report = SimpleNamespace(
            year=2025,
            month=1,
            employee_id="E001",
            employee_name="Alice",
            monthly_summary=SimpleNamespace(
                work_days=20,
                total_work_hours=160.0,
                regular_hours=150.0,
                overtime_hours=10.0,
                night_hours=5.0,
                holiday_hours=2.0,
            ),
            wage_calculation=SimpleNamespace(
                basic_wage=200000,
                overtime_wage=30000,
                night_wage=5000,
                holiday_wage=2000,
                total_wage=237000,
                deductions=10000,
                net_wage=227000,
            ),
        )

    async def generate_daily_reports(self, target_date, employee_ids=None):
        if target_date == self.daily_report.date:
            return [self.daily_report]
        return []

    async def generate_monthly_reports(self, year, month, employee_ids=None):
        return [self.monthly_report]


@pytest.mark.asyncio
async def test_export_daily_csv_outputs_rows(monkeypatch):
    service = ExportService(db=None)
    service.report_service = FakeReportService()

    csv_text = await service.export_daily_csv(
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 1),
        employee_ids=["E001"],
    )

    rows = list(csv.reader(csv_text.strip().splitlines()))
    assert rows[0][0] == "日付"
    assert rows[1][0] == "2025-01-01"
    assert rows[1][1] == "E001"
    assert rows[1][5] == "8.0"


@pytest.mark.asyncio
async def test_export_payroll_json_contains_employee(monkeypatch):
    service = ExportService(db=None)
    service.report_service = FakeReportService()

    data = await service.export_payroll_json(2025, 1)

    assert data["year"] == 2025
    assert data["month"] == 1
    assert len(data["employees"]) == 1
    assert data["employees"][0]["employee_code"] == "E001"
    assert data["employees"][0]["wages"]["net"] == 227000


@pytest.mark.asyncio
async def test_export_attendance_summary_csv_includes_notes(monkeypatch):
    service = ExportService(db=None)
    fake_reports = FakeReportService()
    service.report_service = fake_reports

    csv_text = await service.export_attendance_summary_csv(2025, 1)

    rows = list(csv.reader(csv_text.strip().splitlines()))
    # header + at least one data row (10 columns)
    assert rows[0][0] == "従業員コード"
    assert any("長時間残業" in row[-1] for row in rows[1:])


@pytest.mark.asyncio
async def test_export_monthly_csv_outputs_summary(monkeypatch):
    service = ExportService(db=None)
    service.report_service = FakeReportService()

    csv_text = await service.export_monthly_csv(2025, 1, ["E001"])
    rows = list(csv.reader(csv_text.strip().splitlines()))

    assert rows[0][0] == "年月"
    assert rows[1][0] == "2025-01"
    assert rows[1][3] == str(service.report_service.monthly_report.monthly_summary.work_days)


@pytest.mark.asyncio
async def test_export_payroll_csv_outputs_rows(monkeypatch):
    service = ExportService(db=None)
    service.report_service = FakeReportService()

    csv_text = await service.export_payroll_csv(2025, 1)
    rows = list(csv.reader(csv_text.strip().splitlines()))

    assert rows[0][0] == "従業員コード"
    assert rows[1][0] == "E001"
    assert rows[1][5] == f"{service.report_service.monthly_report.monthly_summary.total_work_hours:.2f}"
