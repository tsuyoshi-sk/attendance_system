from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.models.employee import Employee, WageType
from backend.app.utils.wage_calculator import WageCalculator


def make_hourly_employee(rate=1200):
    return Employee(
        employee_code="H001",
        name="Hourly",
        wage_type=WageType.HOURLY,
        hourly_rate=Decimal(rate),
    )


def make_monthly_employee(salary=300000):
    return Employee(
        employee_code="M001",
        name="Monthly",
        wage_type=WageType.MONTHLY,
        monthly_salary=salary,
    )


def test_calculate_daily_wage_for_hourly_employee():
    calculator = WageCalculator()
    employee = make_hourly_employee()

    result = calculator.calculate_daily_wage(
        employee,
        work_minutes=8 * 60,
        overtime_minutes=60,
        night_minutes=30,
    )

    assert result["regular_hours"] == 7.0
    assert result["overtime_hours"] == 1.0
    assert result["night_hours"] == 0.5
    assert result["basic_wage"] > 0
    assert result["total_wage"] > result["basic_wage"]


def test_calculate_monthly_wage_handles_threshold():
    calculator = WageCalculator()
    employee = make_monthly_employee()

    result = calculator.calculate_monthly_wage(
        employee,
        total_work_hours=180,
        total_overtime_hours=80,
        total_night_hours=10,
        total_holiday_hours=5,
        monthly_overtime_minutes=80 * 60,
    )

    assert result["overtime_wage"] > 0
    assert result["total_wage"] > result["basic_wage"]
    assert result["net_wage"] == pytest.approx(result["total_wage"] * 0.8, rel=0.01)


def test_calculate_payroll_entry_returns_summary():
    calculator = WageCalculator()
    employee = make_hourly_employee()
    summary = {
        "work_days": 20,
        "total_work_hours": 160,
        "overtime_hours": 10,
        "night_hours": 5,
        "total_wage": 250000,
        "deductions": 50000,
        "net_wage": 200000,
    }

    entry = calculator.calculate_payroll_entry(employee, 2025, 1, summary)

    assert entry["employee_code"] == "H001"
    assert entry["total_wage"] == 250000
    assert entry["year"] == 2025


def test_calculate_hourly_rate_raises_for_unknown_type():
    calculator = WageCalculator()
    unknown_employee = SimpleNamespace(wage_type="UNKNOWN")

    with pytest.raises(ValueError):
        calculator._calculate_hourly_rate(unknown_employee)


def test_calculate_hourly_rate_for_monthly_employee():
    calculator = WageCalculator()
    employee = make_monthly_employee()
    hourly = calculator._calculate_hourly_rate(employee)
    assert float(hourly) > 0


def test_calculate_overtime_with_threshold_normal_rate():
    calculator = WageCalculator()
    rate = Decimal("1000")
    wage = calculator._calculate_overtime_with_threshold(
        hourly_rate=rate,
        total_overtime_hours=10,
        monthly_overtime_minutes=10 * 60,
    )
    assert wage == rate * Decimal("10") * calculator.overtime_rate_normal


def test_to_decimal_handles_none():
    calculator = WageCalculator()
    assert calculator._to_decimal(None) == Decimal("0")
