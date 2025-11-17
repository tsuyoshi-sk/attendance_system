import pytest

from datetime import datetime, timedelta, date
from pathlib import Path

import pytest

from backend.app import health_check
from backend.app.health_check import SubsystemHealth, HealthStatus, HealthChecker
from backend.app.models import (
    Employee,
    PunchRecord,
    WageType,
    User,
    UserRole,
    DailySummary,
    MonthlySummary,
)


def test_subsystem_health_to_dict_contains_fields():
    health = SubsystemHealth(
        name="database",
        status=HealthStatus.HEALTHY,
        message="ok",
        details={"tables": 5},
    )

    payload = health.to_dict()
    assert payload["name"] == "database"
    assert payload["status"] == "healthy"
    assert payload["details"]["tables"] == 5


def _make_checker(test_db):
    session = test_db.SessionLocal()
    checker = HealthChecker(session)
    return checker, session


def _patch_checks(checker, monkeypatch, statuses):
    methods = [
        "_check_database",
        "_check_punch_system",
        "_check_employee_system",
        "_check_report_system",
        "_check_analytics_system",
        "_check_pasori",
        "_check_file_system",
    ]
    for method, status in zip(methods, statuses):
        monkeypatch.setattr(
            checker,
            method,
            lambda s=status, name=method: SubsystemHealth(name, s),
        )


def test_health_checker_aggregates_status(monkeypatch, test_db):
    checker, session = _make_checker(test_db)
    statuses = [
        HealthStatus.HEALTHY,
        HealthStatus.DEGRADED,
        HealthStatus.HEALTHY,
        HealthStatus.UNHEALTHY,
        HealthStatus.HEALTHY,
        HealthStatus.HEALTHY,
        HealthStatus.HEALTHY,
    ]
    _patch_checks(checker, monkeypatch, statuses)

    result = checker.check_all()

    session.close()
    assert result["status"] == "unhealthy"
    assert result["summary"]["unhealthy"] == 1
    assert result["summary"]["degraded"] == 1


def _setup_checker_with_data(test_db, tmp_path, monkeypatch):
    session = test_db.SessionLocal()
    monkeypatch.setattr(health_check.config, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(health_check.config, "LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(health_check.config, "PASORI_MOCK_MODE", True)
    checker = HealthChecker(session)
    return checker, session


def _create_employee(session, code="HC001", with_card=False):
    employee = Employee(
        employee_code=code,
        name=f"HC {code}",
        wage_type=WageType.MONTHLY,
        monthly_salary=300000,
        is_active=True,
        card_idm_hash="hash123" if with_card else None,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def test_check_database_reports_counts(tmp_path, monkeypatch, test_db):
    checker, session = _setup_checker_with_data(test_db, tmp_path, monkeypatch)
    employee = _create_employee(session)
    session.add(
        PunchRecord(
            employee_id=employee.id,
            punch_type="in",
            punch_time=datetime.now(),
        )
    )
    session.commit()

    result = checker._check_database()
    session.close()
    assert result.status == HealthStatus.HEALTHY
    assert result.details["employees"] >= 1


def test_check_punch_system_degraded_when_old_punch(tmp_path, monkeypatch, test_db):
    checker, session = _setup_checker_with_data(test_db, tmp_path, monkeypatch)
    employee = _create_employee(session)
    session.add(
        PunchRecord(
            employee_id=employee.id,
            punch_type="in",
            punch_time=datetime.now() - timedelta(hours=13),
        )
    )
    session.commit()

    result = checker._check_punch_system()
    session.close()
    assert result.status == HealthStatus.DEGRADED
    assert "12時間以上" in result.message


def test_check_employee_system_requires_admin(tmp_path, monkeypatch, test_db):
    checker, session = _setup_checker_with_data(test_db, tmp_path, monkeypatch)
    employee = _create_employee(session, with_card=True)
    monkeypatch.setattr(
        health_check.User,
        "is_admin",
        health_check.User.role == UserRole.ADMIN,
        raising=False,
    )
    admin_user = User(
        username="admin",
        password_hash="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(admin_user)
    session.commit()

    result = checker._check_employee_system()
    session.close()
    assert result.status == HealthStatus.HEALTHY
    assert result.details["admin_accounts"] >= 1


def test_check_report_system_detects_lag(tmp_path, monkeypatch, test_db):
    checker, session = _setup_checker_with_data(test_db, tmp_path, monkeypatch)
    employee = _create_employee(session)
    session.add(
        DailySummary(
            employee_id=employee.id,
            work_date=date.today() - timedelta(days=3),
        )
    )
    session.add(
        MonthlySummary(
            employee_id=employee.id,
            year=date.today().year,
            month=date.today().month,
        )
    )
    session.commit()

    result = checker._check_report_system()
    session.close()
    assert result.status == HealthStatus.DEGRADED
    assert "日次集計" in result.message


def test_check_analytics_system_creates_cache(tmp_path, monkeypatch, test_db):
    checker, session = _setup_checker_with_data(test_db, tmp_path, monkeypatch)
    employee = _create_employee(session)
    session.add(
        PunchRecord(
            employee_id=employee.id,
            punch_type="in",
            punch_time=datetime.now(),
        )
    )
    session.commit()

    result = checker._check_analytics_system()
    session.close()
    assert result.status == HealthStatus.HEALTHY
    assert result.details["has_data"] is True


def test_check_pasori_mock(tmp_path, monkeypatch, test_db):
    checker, session = _setup_checker_with_data(test_db, tmp_path, monkeypatch)
    result = checker._check_pasori()
    session.close()
    assert result.status == HealthStatus.HEALTHY
    assert result.details["mock_mode"] is True


def test_check_file_system_creates_dirs(tmp_path, monkeypatch, test_db):
    checker, session = _setup_checker_with_data(test_db, tmp_path, monkeypatch)
    result = checker._check_file_system()
    session.close()
    assert result.status == HealthStatus.DEGRADED
    assert result.details["issues"]
