"""
完全な勤怠フロー統合テスト

従業員作成からレポート出力まで、エンドツーエンドでシステムの動作を検証
"""

import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.employee import Employee
from backend.app.models.punch_record import PunchRecord


@pytest.mark.integration
class TestCompleteAttendanceWorkflow:
    """統合的な勤怠管理ワークフローのテスト"""

    def test_complete_attendance_workflow(self, client: TestClient, db: Session):
        """完全な勤怠フロー統合テスト"""
        # 1. 従業員作成
        employee_data = {
            "name": "統合テスト太郎",
            "employee_code": "INT_001",
            "email": "test@example.com",
        }
        response = client.post("/api/v1/admin/employees", json=employee_data)
        assert response.status_code == 201
        employee = response.json()
        employee_id = employee["id"]

        # 2. カード登録
        card_data = {"card_id": "test_card_123"}
        response = client.post(
            f"/api/v1/admin/employees/{employee_id}/card", json=card_data
        )
        assert response.status_code == 200

        # 3. 出勤打刻
        punch_data = {"card_idm": "test_card_123", "punch_type": "in"}
        response = client.post("/api/v1/punch", params=punch_data)
        assert response.status_code == 200
        punch_result = response.json()
        assert punch_result["success"] is True
        assert punch_result["punch_type"] == "in"

        # 4. 外出打刻
        punch_data = {"card_idm": "test_card_123", "punch_type": "out_break"}
        response = client.post("/api/v1/punch", params=punch_data)
        assert response.status_code == 200

        # 5. 戻り打刻
        punch_data = {"card_idm": "test_card_123", "punch_type": "in_break"}
        response = client.post("/api/v1/punch", params=punch_data)
        assert response.status_code == 200

        # 6. 退勤打刻
        punch_data = {"card_idm": "test_card_123", "punch_type": "out"}
        response = client.post("/api/v1/punch", params=punch_data)
        assert response.status_code == 200

        # 7. 打刻履歴確認
        response = client.get(f"/api/v1/punch/history/{employee_id}")
        assert response.status_code == 200
        history = response.json()
        assert len(history) == 4  # 4回の打刻

        # 8. 日次レポート確認
        today = date.today().isoformat()
        response = client.get(f"/api/v1/reports/daily/{today}")
        assert response.status_code == 200
        daily_report = response.json()
        assert len(daily_report) > 0

        # 該当従業員のレポートを確認
        employee_report = next(
            (r for r in daily_report if r["employee_name"] == "統合テスト太郎"), None
        )
        assert employee_report is not None
        assert employee_report["status"] == "完了"
        assert employee_report["work_time"] is not None

        # 9. 月次レポート確認
        current_month = date.today().strftime("%Y-%m")
        response = client.get(f"/api/v1/reports/monthly/{current_month}")
        assert response.status_code == 200
        monthly_report = response.json()
        assert len(monthly_report) > 0

    def test_punch_validation_workflow(self, client: TestClient, db: Session):
        """打刻検証ワークフローのテスト"""
        # 従業員作成とカード登録
        employee_data = {
            "name": "検証テスト花子",
            "employee_code": "VAL_001",
            "email": "validate@example.com",
        }
        response = client.post("/api/v1/admin/employees", json=employee_data)
        employee_id = response.json()["id"]

        card_data = {"card_id": "validate_card_456"}
        client.post(f"/api/v1/admin/employees/{employee_id}/card", json=card_data)

        # 出勤なしで退勤しようとする
        punch_data = {"card_idm": "validate_card_456", "punch_type": "out"}
        response = client.post("/api/v1/punch", params=punch_data)
        assert response.status_code == 400

        # 正常な出勤
        punch_data = {"card_idm": "validate_card_456", "punch_type": "in"}
        response = client.post("/api/v1/punch", params=punch_data)
        assert response.status_code == 200

        # 二重出勤を試みる
        response = client.post("/api/v1/punch", params=punch_data)
        assert response.status_code == 400

    def test_multi_employee_workflow(self, client: TestClient, db: Session):
        """複数従業員の同時処理ワークフロー"""
        employees = []

        # 10名の従業員を作成
        for i in range(10):
            employee_data = {
                "name": f"マルチテスト{i}",
                "employee_code": f"MULTI_{i:03d}",
                "email": f"multi{i}@example.com",
            }
            response = client.post("/api/v1/admin/employees", json=employee_data)
            assert response.status_code == 201
            employee = response.json()

            # カード登録
            card_data = {"card_id": f"multi_card_{i}"}
            response = client.post(
                f"/api/v1/admin/employees/{employee['id']}/card", json=card_data
            )
            assert response.status_code == 200

            employees.append({"id": employee["id"], "card_idm": f"multi_card_{i}"})

        # 全員が出勤
        for emp in employees:
            punch_data = {"card_idm": emp["card_idm"], "punch_type": "in"}
            response = client.post("/api/v1/punch", params=punch_data)
            assert response.status_code == 200

        # 日次レポートで全員の出勤を確認
        today = date.today().isoformat()
        response = client.get(f"/api/v1/reports/daily/{today}")
        assert response.status_code == 200
        daily_report = response.json()

        # 10名全員が含まれていることを確認
        multi_employees = [
            r for r in daily_report if r["employee_name"].startswith("マルチテスト")
        ]
        assert len(multi_employees) == 10

    def test_error_recovery_workflow(self, client: TestClient, db: Session):
        """エラーリカバリーワークフローのテスト"""
        # 存在しないカードでの打刻
        punch_data = {"card_idm": "non_existent_card", "punch_type": "in"}
        response = client.post("/api/v1/punch", params=punch_data)
        assert response.status_code == 404

        # 無効な打刻タイプ
        employee_data = {
            "name": "エラーテスト",
            "employee_code": "ERR_001",
            "email": "error@example.com",
        }
        response = client.post("/api/v1/admin/employees", json=employee_data)
        employee_id = response.json()["id"]

        card_data = {"card_id": "error_card"}
        client.post(f"/api/v1/admin/employees/{employee_id}/card", json=card_data)

        punch_data = {"card_idm": "error_card", "punch_type": "invalid_type"}
        response = client.post("/api/v1/punch", params=punch_data)
        assert response.status_code == 422  # バリデーションエラー
