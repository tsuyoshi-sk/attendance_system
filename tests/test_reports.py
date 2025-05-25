"""
レポート機能のテスト
"""

import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import Employee, PunchRecord, PunchType, WageType
from backend.app.services.report_service import ReportService
from tests.conftest import TestDatabase


@pytest.fixture
def client():
    """テストクライアント"""
    return TestClient(app)


@pytest.fixture
def test_db():
    """テスト用データベース"""
    return TestDatabase()


@pytest.fixture
def sample_employee(test_db):
    """サンプル従業員"""
    with test_db.get_session() as db:
        employee = Employee(
            employee_code="TEST001",
            name="テスト太郎",
            email="test@example.com",
            wage_type=WageType.HOURLY,
            hourly_rate=2500,
            is_active=True
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee


@pytest.fixture
def sample_punch_records(test_db, sample_employee):
    """サンプル打刻記録"""
    with test_db.get_session() as db:
        target_date = date.today()
        
        # 出勤
        punch_in = PunchRecord(
            employee_id=sample_employee.id,
            punch_type=PunchType.CLOCK_IN.value,
            punch_time=datetime.combine(target_date, datetime.min.time().replace(hour=9))
        )
        
        # 外出
        break_start = PunchRecord(
            employee_id=sample_employee.id,
            punch_type=PunchType.BREAK_START.value,
            punch_time=datetime.combine(target_date, datetime.min.time().replace(hour=12))
        )
        
        # 戻り
        break_end = PunchRecord(
            employee_id=sample_employee.id,
            punch_type=PunchType.BREAK_END.value,
            punch_time=datetime.combine(target_date, datetime.min.time().replace(hour=13))
        )
        
        # 退勤
        punch_out = PunchRecord(
            employee_id=sample_employee.id,
            punch_type=PunchType.CLOCK_OUT.value,
            punch_time=datetime.combine(target_date, datetime.min.time().replace(hour=18))
        )
        
        db.add_all([punch_in, break_start, break_end, punch_out])
        db.commit()
        
        return [punch_in, break_start, break_end, punch_out]


class TestReportService:
    """レポートサービスのテスト"""
    
    def test_generate_daily_reports(self, test_db, sample_employee, sample_punch_records):
        """日次レポート生成のテスト"""
        with test_db.get_session() as db:
            service = ReportService(db)
            
            # 日次レポートを生成
            reports = asyncio.run(service.generate_daily_reports(date.today()))
            
            assert len(reports) == 1
            report = reports[0]
            
            assert report.employee_id == sample_employee.employee_code
            assert report.employee_name == sample_employee.name
            assert report.date == date.today()
            
            # 労働時間の確認（9時間 - 1時間休憩 = 8時間）
            assert report.summary.work_minutes == 540  # 9時間
            assert report.summary.break_minutes == 60   # 1時間
            assert report.summary.actual_work_minutes == 480  # 8時間
    
    def test_generate_monthly_reports(self, test_db, sample_employee, sample_punch_records):
        """月次レポート生成のテスト"""
        with test_db.get_session() as db:
            service = ReportService(db)
            
            # 月次レポートを生成
            today = date.today()
            reports = asyncio.run(service.generate_monthly_reports(today.year, today.month))
            
            assert len(reports) == 1
            report = reports[0]
            
            assert report.employee_id == sample_employee.employee_code
            assert report.year == today.year
            assert report.month == today.month
            
            # 賃金計算の確認
            assert report.wage_calculation.basic_wage > 0
            assert report.wage_calculation.total_wage > 0


class TestReportAPI:
    """レポートAPIのテスト"""
    
    def test_daily_report_endpoint(self, client, test_db, sample_employee, sample_punch_records):
        """日次レポートAPIのテスト"""
        # データベースセッションをモック
        app.dependency_overrides[get_db] = test_db.get_session
        
        # API呼び出し
        response = client.post("/api/v1/reports/daily", json={
            "target_date": date.today().isoformat(),
            "employee_ids": [sample_employee.employee_code]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        report = data[0]
        
        assert report["employee_id"] == sample_employee.employee_code
        assert report["date"] == date.today().isoformat()
        
        # クリーンアップ
        app.dependency_overrides.clear()
    
    def test_monthly_report_endpoint(self, client, test_db, sample_employee, sample_punch_records):
        """月次レポートAPIのテスト"""
        app.dependency_overrides[get_db] = test_db.get_session
        
        today = date.today()
        response = client.post("/api/v1/reports/monthly", json={
            "year": today.year,
            "month": today.month,
            "employee_ids": [sample_employee.employee_code]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        report = data[0]
        
        assert report["employee_id"] == sample_employee.employee_code
        assert report["year"] == today.year
        assert report["month"] == today.month
        
        app.dependency_overrides.clear()
    
    def test_csv_export_endpoint(self, client, test_db, sample_employee, sample_punch_records):
        """CSV出力APIのテスト"""
        app.dependency_overrides[get_db] = test_db.get_session
        
        today = date.today()
        response = client.get(f"/api/v1/reports/export/daily/csv", params={
            "from_date": today.isoformat(),
            "to_date": today.isoformat()
        })
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # CSVの内容確認
        csv_content = response.content.decode("utf-8")
        assert "従業員コード" in csv_content
        assert sample_employee.employee_code in csv_content
        
        app.dependency_overrides.clear()


class TestTimeCalculator:
    """時間計算のテスト"""
    
    def test_daily_hours_calculation(self, sample_punch_records):
        """日次時間計算のテスト"""
        from backend.app.utils.time_calculator import TimeCalculator
        
        calculator = TimeCalculator()
        result = calculator.calculate_daily_hours(sample_punch_records)
        
        # 9時間労働、1時間休憩 = 8時間実労働
        assert result["work_minutes"] == 540
        assert result["break_minutes"] == 60
        assert result["actual_work_minutes"] == 480
        assert result["overtime_minutes"] == 0  # 8時間なので残業なし
    
    def test_overtime_calculation(self, test_db, sample_employee):
        """残業時間計算のテスト"""
        from backend.app.utils.time_calculator import TimeCalculator
        
        calculator = TimeCalculator()
        
        # 10時間労働のサンプル
        with test_db.get_session() as db:
            target_date = date.today()
            
            punch_in = PunchRecord(
                employee_id=sample_employee.id,
                punch_type=PunchType.CLOCK_IN.value,
                punch_time=datetime.combine(target_date, datetime.min.time().replace(hour=9))
            )
            
            punch_out = PunchRecord(
                employee_id=sample_employee.id,
                punch_type=PunchType.CLOCK_OUT.value,
                punch_time=datetime.combine(target_date, datetime.min.time().replace(hour=19))  # 19時
            )
            
            result = calculator.calculate_daily_hours([punch_in, punch_out])
            
            # 10時間労働 - 8時間標準 = 2時間残業
            assert result["work_minutes"] == 600
            assert result["actual_work_minutes"] == 600
            assert result["overtime_minutes"] == 120


class TestWageCalculator:
    """賃金計算のテスト"""
    
    def test_hourly_wage_calculation(self, sample_employee):
        """時給制賃金計算のテスト"""
        from backend.app.utils.wage_calculator import WageCalculator
        
        calculator = WageCalculator()
        result = calculator.calculate_daily_wage(
            employee=sample_employee,
            work_minutes=480,  # 8時間
            overtime_minutes=0,
            night_minutes=0
        )
        
        # 時給2500円 × 8時間 = 20000円
        assert result["basic_wage"] == 20000
        assert result["overtime_wage"] == 0
        assert result["total_wage"] == 20000
    
    def test_overtime_wage_calculation(self, sample_employee):
        """残業代計算のテスト"""
        from backend.app.utils.wage_calculator import WageCalculator
        
        calculator = WageCalculator()
        result = calculator.calculate_daily_wage(
            employee=sample_employee,
            work_minutes=600,  # 10時間
            overtime_minutes=120,  # 2時間残業
            night_minutes=0
        )
        
        # 基本給: 時給2500円 × 8時間 = 20000円
        # 残業代: 時給2500円 × 2時間 × 1.25 = 6250円
        assert result["basic_wage"] == 20000
        assert result["overtime_wage"] == 6250
        assert result["total_wage"] == 26250