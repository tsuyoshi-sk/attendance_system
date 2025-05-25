"""
エンドツーエンド統合テスト

システム全体の統合動作を検証するテストスイートです。
従業員登録 → カード登録 → 打刻 → レポート生成の完全なフローをテストします。
"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
import hashlib
from typing import Dict, Any, List

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import Employee, User, PunchRecord, DailySummary, MonthlySummary
from backend.app.services.auth_service import AuthService
from config.config import config


class TestIntegratedWorkflow:
    """統合ワークフローテスト"""
    
    @pytest.fixture(autouse=True)
    def setup(self, db: Session, client: TestClient):
        """テスト環境のセットアップ"""
        self.db = db
        self.client = client
        self.auth_service = AuthService(db)
        
        # テスト用管理者を作成
        self.admin_token = self._create_test_admin()
        
        # クリーンアップ
        yield
        
        # テストデータを削除
        db.query(MonthlySummary).delete()
        db.query(DailySummary).delete()
        db.query(PunchRecord).delete()
        db.query(Employee).filter(Employee.employee_code.like("TEST%")).delete()
        db.query(User).filter(User.username.like("test%")).delete()
        db.commit()
    
    def _create_test_admin(self) -> str:
        """テスト用管理者アカウントを作成"""
        admin_user = self.auth_service.create_user(
            username="test_admin",
            password="admin123456",
            is_admin=True,
            employee_id=None
        )
        
        # ログインしてトークンを取得
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "test_admin", "password": "admin123456"}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def _get_auth_headers(self, token: str = None) -> Dict[str, str]:
        """認証ヘッダーを取得"""
        token = token or self.admin_token
        return {"Authorization": f"Bearer {token}"}
    
    def test_complete_workflow(self):
        """
        完全な統合ワークフローテスト
        
        1. 従業員登録
        2. カード登録
        3. ユーザーアカウント作成
        4. 打刻（出勤・退勤）
        5. 日次レポート生成
        6. 月次レポート生成
        7. CSV出力
        """
        
        # Step 1: 従業員登録 (Terminal B機能)
        employee_data = {
            "employee_code": "TEST001",
            "name": "テスト太郎",
            "name_kana": "テストタロウ",
            "email": "test.taro@example.com",
            "department": "開発部",
            "position": "エンジニア",
            "employment_type": "正社員",
            "hire_date": "2024-01-01",
            "wage_type": "hourly",
            "hourly_rate": "2500.00",
            "is_active": True
        }
        
        response = self.client.post(
            "/api/v1/admin/employees",
            json=employee_data,
            headers=self._get_auth_headers()
        )
        assert response.status_code == 201
        employee = response.json()
        employee_id = employee["id"]
        
        # Step 2: カード登録 (Terminal B機能)
        test_idm = "1234567890ABCDEF"
        idm_hash = hashlib.sha256(
            f"{test_idm}{config.IDM_HASH_SECRET}".encode()
        ).hexdigest()
        
        card_data = {
            "card_idm_hash": idm_hash,
            "card_name": "テストカード"
        }
        
        response = self.client.post(
            f"/api/v1/admin/employees/{employee_id}/cards",
            json=card_data,
            headers=self._get_auth_headers()
        )
        assert response.status_code == 201
        card = response.json()
        
        # Step 3: 従業員用ユーザーアカウント作成
        user_data = {
            "username": "test_employee",
            "password": "employee123456",
            "employee_id": employee_id,
            "is_admin": False
        }
        
        response = self.client.post(
            "/api/v1/auth/users",
            json=user_data,
            headers=self._get_auth_headers()
        )
        assert response.status_code == 201
        
        # Step 4: 打刻実行 (Terminal A機能)
        # 出勤打刻
        punch_in_data = {
            "card_idm": test_idm,  # ハッシュ化前のIDm
            "punch_type": "IN"
        }
        
        response = self.client.post(
            "/api/v1/punch",
            json=punch_in_data
        )
        assert response.status_code == 200
        punch_in_result = response.json()
        assert punch_in_result["success"] is True
        assert punch_in_result["punch_record"]["punch_type"] == "IN"
        
        # 打刻状態確認
        response = self.client.get(
            f"/api/v1/punch/status/{employee_id}"
        )
        assert response.status_code == 200
        status = response.json()
        assert status["is_working"] is True
        assert status["last_punch_type"] == "IN"
        
        # 退勤打刻（6時間後）
        # 実際のテストでは時間を操作する代わりに、
        # punch_timeを直接指定できるようにAPI を拡張することを推奨
        punch_out_data = {
            "card_idm": test_idm,
            "punch_type": "OUT"
        }
        
        response = self.client.post(
            "/api/v1/punch",
            json=punch_out_data
        )
        assert response.status_code == 200
        punch_out_result = response.json()
        assert punch_out_result["success"] is True
        assert punch_out_result["punch_record"]["punch_type"] == "OUT"
        
        # Step 5: 日次レポート生成 (Terminal C機能)
        today = date.today()
        
        response = self.client.post(
            "/api/v1/reports/daily",
            json={"target_date": today.isoformat()},
            headers=self._get_auth_headers()
        )
        assert response.status_code == 200
        daily_generation = response.json()
        assert daily_generation["success"] is True
        assert daily_generation["processed"] > 0
        
        # 日次レポート取得
        response = self.client.get(
            f"/api/v1/reports/daily/{today.isoformat()}",
            headers=self._get_auth_headers()
        )
        assert response.status_code == 200
        daily_reports = response.json()
        assert len(daily_reports["summaries"]) > 0
        
        # 特定従業員の日次レポート確認
        employee_daily = next(
            (s for s in daily_reports["summaries"] if s["employee_id"] == employee_id),
            None
        )
        assert employee_daily is not None
        assert employee_daily["punch_in_time"] is not None
        assert employee_daily["punch_out_time"] is not None
        assert employee_daily["work_hours"] > 0
        
        # Step 6: 月次レポート生成 (Terminal C機能)
        current_year = today.year
        current_month = today.month
        
        response = self.client.post(
            "/api/v1/reports/monthly",
            json={
                "year": current_year,
                "month": current_month
            },
            headers=self._get_auth_headers()
        )
        assert response.status_code == 200
        monthly_generation = response.json()
        assert monthly_generation["success"] is True
        
        # 月次レポート取得
        response = self.client.get(
            f"/api/v1/reports/monthly/{current_year}/{current_month}",
            headers=self._get_auth_headers()
        )
        assert response.status_code == 200
        monthly_reports = response.json()
        assert len(monthly_reports["summaries"]) > 0
        
        # Step 7: CSV出力 (Terminal C機能)
        # 日次CSV出力
        response = self.client.get(
            f"/api/v1/reports/export/daily/csv",
            params={
                "start_date": today.isoformat(),
                "end_date": today.isoformat()
            },
            headers=self._get_auth_headers()
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert len(response.text) > 0
        
        # 月次CSV出力
        response = self.client.get(
            f"/api/v1/reports/export/monthly/csv",
            params={
                "year": current_year,
                "month": current_month
            },
            headers=self._get_auth_headers()
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Step 8: 分析ダッシュボード確認 (Terminal C機能)
        response = self.client.get(
            "/api/v1/analytics/dashboard",
            headers=self._get_auth_headers()
        )
        assert response.status_code == 200
        dashboard = response.json()
        assert dashboard["total_employees"] > 0
        assert dashboard["active_today"] > 0
        
        # Step 9: 統合ヘルスチェック
        response = self.client.get("/health/integrated")
        assert response.status_code == 200
        health = response.json()
        assert health["status"] in ["healthy", "degraded"]
        assert len(health["subsystems"]) > 0
    
    def test_concurrent_punches(self):
        """並行打刻テスト"""
        # 複数の従業員を作成
        employees = []
        for i in range(5):
            employee_data = {
                "employee_code": f"TEST{i:03d}",
                "name": f"テスト{i}",
                "email": f"test{i}@example.com",
                "wage_type": "hourly",
                "hourly_rate": "2000.00",
                "is_active": True
            }
            
            response = self.client.post(
                "/api/v1/admin/employees",
                json=employee_data,
                headers=self._get_auth_headers()
            )
            assert response.status_code == 201
            employees.append(response.json())
        
        # 同時に打刻を実行
        # 実際の並行性テストには threading や asyncio を使用
        for employee in employees:
            test_idm = f"IDM{employee['id']:016X}"
            idm_hash = hashlib.sha256(
                f"{test_idm}{config.IDM_HASH_SECRET}".encode()
            ).hexdigest()
            
            # カード登録
            card_data = {
                "card_idm_hash": idm_hash,
                "card_name": f"カード{employee['id']}"
            }
            
            response = self.client.post(
                f"/api/v1/admin/employees/{employee['id']}/cards",
                json=card_data,
                headers=self._get_auth_headers()
            )
            assert response.status_code == 201
            
            # 打刻実行
            punch_data = {
                "card_idm": test_idm,
                "punch_type": "IN"
            }
            
            response = self.client.post(
                "/api/v1/punch",
                json=punch_data
            )
            assert response.status_code == 200
        
        # 全員の打刻が記録されていることを確認
        for employee in employees:
            response = self.client.get(
                f"/api/v1/punch/status/{employee['id']}"
            )
            assert response.status_code == 200
            status = response.json()
            assert status["is_working"] is True
    
    def test_error_recovery(self):
        """エラーリカバリーテスト"""
        # 存在しないカードで打刻
        response = self.client.post(
            "/api/v1/punch",
            json={
                "card_idm": "INVALID_CARD_IDM",
                "punch_type": "IN"
            }
        )
        assert response.status_code == 404
        assert "登録されていません" in response.json()["detail"]
        
        # 無効な打刻タイプ
        response = self.client.post(
            "/api/v1/punch",
            json={
                "card_idm": "1234567890ABCDEF",
                "punch_type": "INVALID"
            }
        )
        assert response.status_code == 422
        
        # 権限なしでの管理API アクセス
        response = self.client.get("/api/v1/admin/employees")
        assert response.status_code == 401
    
    def test_performance_requirements(self):
        """パフォーマンス要件テスト"""
        import time
        
        # 従業員作成
        employee_data = {
            "employee_code": "PERF001",
            "name": "パフォーマンステスト",
            "wage_type": "monthly",
            "monthly_salary": 300000,
            "is_active": True
        }
        
        response = self.client.post(
            "/api/v1/admin/employees",
            json=employee_data,
            headers=self._get_auth_headers()
        )
        assert response.status_code == 201
        employee_id = response.json()["id"]
        
        # カード登録
        test_idm = "PERF1234567890AB"
        idm_hash = hashlib.sha256(
            f"{test_idm}{config.IDM_HASH_SECRET}".encode()
        ).hexdigest()
        
        response = self.client.post(
            f"/api/v1/admin/employees/{employee_id}/cards",
            json={
                "card_idm_hash": idm_hash,
                "card_name": "パフォーマンステストカード"
            },
            headers=self._get_auth_headers()
        )
        assert response.status_code == 201
        
        # 打刻APIの応答時間測定
        start_time = time.time()
        response = self.client.post(
            "/api/v1/punch",
            json={
                "card_idm": test_idm,
                "punch_type": "IN"
            }
        )
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 3.0, f"打刻API応答時間が3秒を超えています: {response_time:.2f}秒"
        
        # ヘルスチェックAPIの応答時間測定
        start_time = time.time()
        response = self.client.get("/health/integrated")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 5.0, f"ヘルスチェックAPI応答時間が5秒を超えています: {response_time:.2f}秒"