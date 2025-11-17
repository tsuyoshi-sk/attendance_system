from datetime import datetime, timedelta, date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import analytics
from backend.app.database import get_db
from backend.app.models import Employee, PunchRecord, PunchType, WageType


def _seed_employee(session):
    employee = Employee(
        employee_code="AN001",
        name="Analytics Tester",
        wage_type=WageType.MONTHLY,
        monthly_salary=300000,
        is_active=True,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)

    for offset in range(3):
        day = date.today() - timedelta(days=offset)
        session.add_all(
            [
                PunchRecord(
                    employee_id=employee.id,
                    punch_type=PunchType.IN.value,
                    punch_time=datetime(day.year, day.month, day.day, 9, 0),
                ),
                PunchRecord(
                    employee_id=employee.id,
                    punch_type=PunchType.OUT.value,
                    punch_time=datetime(day.year, day.month, day.day, 18, 0),
                ),
            ]
        )
    session.commit()


@pytest.fixture
def analytics_app(test_db):
    app = FastAPI()
    app.include_router(analytics.router, prefix="/api/v1/analytics")

    def override_get_db():
        db = test_db.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def analytics_client(analytics_app, test_db):
    session = test_db.SessionLocal()
    _seed_employee(session)
    session.close()
    return TestClient(analytics_app)


def test_analytics_health_endpoint(analytics_client):
    resp = analytics_client.get("/api/v1/analytics/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_get_dashboard_endpoint(analytics_client):
    resp = analytics_client.get("/api/v1/analytics/dashboard")
    assert resp.status_code == 200
    assert resp.json()["today_summary"]["total_employees"] >= 1


def test_get_statistics_invalid_period(analytics_client):
    resp = analytics_client.get("/api/v1/analytics/statistics?period=invalid")
    assert resp.status_code == 400


def test_get_statistics_valid(analytics_client):
    resp = analytics_client.get("/api/v1/analytics/statistics?period=day")
    assert resp.status_code == 200
    assert "attendance_stats" in resp.json()


def test_work_hours_trend_validation(analytics_client):
    resp = analytics_client.get("/api/v1/analytics/charts/work-hours-trend?months=0")
    assert resp.status_code == 400


def test_work_hours_trend_success(analytics_client):
    resp = analytics_client.get("/api/v1/analytics/charts/work-hours-trend?months=2")
    assert resp.status_code == 200
    assert "datasets" in resp.json()["data"]


def test_overtime_distribution_endpoint(analytics_client):
    today = date.today()
    resp = analytics_client.get(
        f"/api/v1/analytics/charts/overtime-distribution?year={today.year}&month={today.month}"
    )
    assert resp.status_code == 200


def test_attendance_rate_chart(analytics_client):
    resp = analytics_client.get("/api/v1/analytics/charts/attendance-rate?months=1")
    assert resp.status_code == 200


def test_current_alerts_endpoint(analytics_client):
    resp = analytics_client.get("/api/v1/analytics/alerts/current")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_realtime_summary_endpoint(analytics_client):
    resp = analytics_client.get("/api/v1/analytics/summary/realtime")
    assert resp.status_code == 200
    assert "working_count" in resp.json()
