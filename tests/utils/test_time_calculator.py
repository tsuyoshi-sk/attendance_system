from datetime import datetime, date, time, timedelta
from types import SimpleNamespace

from backend.app.utils.time_calculator import TimeCalculator
from backend.app.models.punch_record import PunchType


def make_punch(punch_type: str, dt: datetime):
    return SimpleNamespace(punch_type=punch_type, punch_time=dt)


def test_calculate_daily_hours_with_breaks_and_overtime():
    calculator = TimeCalculator()
    start = datetime(2025, 1, 1, 9, 0)
    punches = [
        make_punch(PunchType.IN.value, start),
        make_punch(PunchType.OUTSIDE.value, start + timedelta(hours=3)),
        make_punch(PunchType.RETURN.value, start + timedelta(hours=4)),
        make_punch(PunchType.OUT.value, start + timedelta(hours=10)),
    ]

    result = calculator.calculate_daily_hours(punches)

    assert result["work_minutes"] == 600  # 10時間
    assert result["break_minutes"] == 60
    assert result["actual_work_minutes"] == 540  # 9時間
    assert result["overtime_minutes"] == 60  # 1時間分


def test_calculate_daily_hours_includes_night_minutes():
    calculator = TimeCalculator()
    start = datetime(2025, 1, 1, 21, 30)
    punches = [
        make_punch(PunchType.IN.value, start),
        make_punch(PunchType.OUT.value, start + timedelta(hours=6)),  # 03:30
    ]

    result = calculator.calculate_daily_hours(punches)

    # 22:00-03:30 = 5.5時間 = 330分 (rounded to 330)
    assert result["night_minutes"] >= 330


def test_round_monthly_overtime_behavior():
    calculator = TimeCalculator()
    assert calculator.round_monthly_overtime(89) == 60
    assert calculator.round_monthly_overtime(90) == 120


def test_holiday_and_scheduled_hours():
    calculator = TimeCalculator()
    saturday = date(2025, 1, 4)
    monday = date(2025, 1, 6)

    assert calculator.is_holiday(saturday) is True
    assert calculator.calculate_scheduled_hours(saturday) == 0
    assert calculator.calculate_scheduled_hours(monday) == 480


def test_late_and_early_minutes():
    calculator = TimeCalculator()

    scheduled_start = time(9, 0)
    actual_start = datetime(2025, 1, 1, 9, 12)
    assert calculator.calculate_late_minutes(scheduled_start, actual_start) == 12

    scheduled_end = time(18, 0)
    actual_end = datetime(2025, 1, 1, 17, 30)
    assert calculator.calculate_early_leave_minutes(scheduled_end, actual_end) == 30


def test_calculate_daily_hours_with_no_punches():
    calculator = TimeCalculator()
    result = calculator.calculate_daily_hours([])
    assert result["work_minutes"] == 0
    assert result["actual_work_minutes"] == 0


def test_calculate_early_leave_minutes_no_early_leave():
    calculator = TimeCalculator()
    scheduled_end = time(18, 0)
    actual_end = datetime(2025, 1, 1, 18, 5)
    assert calculator.calculate_early_leave_minutes(scheduled_end, actual_end) == 0


def test_calculate_daily_hours_without_clock_in():
    calculator = TimeCalculator()
    punches = [make_punch(PunchType.OUT.value, datetime(2025, 1, 1, 18, 0))]
    result = calculator.calculate_daily_hours(punches)
    assert result["work_minutes"] == 0
