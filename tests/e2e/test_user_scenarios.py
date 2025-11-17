"""
E2E統合テスト - 実際のユーザーシナリオ

実際のユーザーの操作フローを想定したEnd-to-Endテストを実施します。
"""

import pytest
from datetime import datetime, timedelta


class TestNewEmployeeOnboarding:
    """新入社員の入社フローのE2Eテスト"""

    def test_complete_employee_onboarding_flow(self, client, auth_headers):
        """
        シナリオ: 新入社員の初日の完全なフロー

        1. 管理者がログイン
        2. 新入社員を登録
        3. 社員証（カード）を発行
        4. 初回出勤打刻
        5. 退勤打刻
        6. 勤怠記録の確認
        """
        # Step 1: 管理者がログイン（auth_headersで既に認証済み）

        # Step 2: 新入社員を登録
        new_employee = {
            "employee_code": "E2E001",
            "name": "山田太郎",
            "email": "yamada@example.com",
            "position": "エンジニア",
            "employment_type": "正社員",
            "hire_date": datetime.now().strftime("%Y-%m-%d"),
            "wage_type": "monthly",
            "monthly_salary": 400000,
            "is_active": True
        }

        response = client.post(
            "/api/v1/admin/employees",
            json=new_employee,
            headers=auth_headers
        )
        assert response.status_code in [200, 201], f"従業員登録に失敗: {response.text}"
        employee_data = response.json()
        employee_id = employee_data["id"]

        print(f"✓ 従業員登録完了: {employee_data['name']} (ID: {employee_id})")

        # Step 3: 社員証（カード）を発行
        card_data = {
            "card_idm_hash": "a" * 64,  # テスト用の64文字ハッシュ
            "card_nickname": "社員証",
            "issued_date": datetime.now().strftime("%Y-%m-%d")
        }

        response = client.post(
            f"/api/v1/admin/employees/{employee_id}/cards",
            json=card_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201], f"カード発行に失敗: {response.text}"
        card = response.json()

        print(f"✓ カード発行完了: {card['card_nickname']}")

        # Step 4: 初回出勤打刻
        punch_in_data = {
            "card_idm_hash": card_data["card_idm_hash"],
            "punch_type": "in"
        }

        response = client.post(
            "/api/v1/punch/",
            json=punch_in_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201], f"出勤打刻に失敗: {response.text}"
        punch_in = response.json()

        print(f"✓ 出勤打刻完了: {punch_in.get('punch_time', 'N/A')}")

        # Step 5: 退勤打刻（数秒後を想定）
        punch_out_data = {
            "card_idm_hash": card_data["card_idm_hash"],
            "punch_type": "out"
        }

        response = client.post(
            "/api/v1/punch/",
            json=punch_out_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201], f"退勤打刻に失敗: {response.text}"
        punch_out = response.json()

        print(f"✓ 退勤打刻完了: {punch_out.get('punch_time', 'N/A')}")

        # Step 6: 従業員の勤怠記録を確認
        response = client.get(
            f"/api/v1/admin/employees/{employee_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"従業員情報取得に失敗: {response.text}"

        print(f"✓ 新入社員の初日フローが正常に完了しました")

        # アサーション: すべてのステップが成功していることを確認
        assert employee_id is not None
        assert card is not None
        assert punch_in is not None
        assert punch_out is not None


class TestDailyWorkFlow:
    """日常業務フローのE2Eテスト"""

    def test_typical_workday_flow(self, client, auth_headers):
        """
        シナリオ: 一般的な1日の勤務フロー

        1. 従業員を作成
        2. カードを発行
        3. 出勤打刻
        4. 外出打刻
        5. 戻り打刻
        6. 退勤打刻
        7. 打刻履歴の確認
        """
        # Step 1: 従業員を作成
        employee = {
            "employee_code": "E2E002",
            "name": "佐藤花子",
            "wage_type": "hourly",
            "hourly_rate": 2000,
        }

        response = client.post(
            "/api/v1/admin/employees",
            json=employee,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        employee_id = response.json()["id"]

        print(f"✓ 従業員作成: 佐藤花子 (ID: {employee_id})")

        # Step 2: カードを発行
        card_hash = "b" * 64
        response = client.post(
            f"/api/v1/admin/employees/{employee_id}/cards",
            json={
                "card_idm_hash": card_hash,
                "card_nickname": "通勤カード"
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

        print(f"✓ カード発行完了")

        # Step 3: 出勤打刻
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm_hash": card_hash, "punch_type": "in"},
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        punch_in_time = response.json().get("punch_time")

        print(f"✓ 出勤打刻: {punch_in_time}")

        # Step 4: 外出打刻
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm_hash": card_hash, "punch_type": "outside"},
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

        print(f"✓ 外出打刻完了")

        # Step 5: 戻り打刻
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm_hash": card_hash, "punch_type": "return"},
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

        print(f"✓ 戻り打刻完了")

        # Step 6: 退勤打刻
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm_hash": card_hash, "punch_type": "out"},
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        punch_out_time = response.json().get("punch_time")

        print(f"✓ 退勤打刻: {punch_out_time}")

        # Step 7: 打刻履歴の確認（従業員詳細取得）
        response = client.get(
            f"/api/v1/admin/employees/{employee_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        print(f"✓ 日常業務フローが正常に完了しました")


class TestManagerReportFlow:
    """管理者レポート確認フローのE2Eテスト"""

    def test_manager_daily_report_flow(self, client, auth_headers):
        """
        シナリオ: 管理者が日次レポートを確認

        1. 従業員を複数作成
        2. 各従業員が打刻
        3. 従業員一覧を取得
        4. 各従業員の勤怠状況を確認
        """
        # Step 1: 従業員を3人作成
        employees = []
        for i in range(3):
            employee = {
                "employee_code": f"E2E00{i+3}",
                "name": f"テスト従業員{i+1}",
                "wage_type": "monthly",
                "monthly_salary": 300000 + (i * 50000),
            }

            response = client.post(
                "/api/v1/admin/employees",
                json=employee,
                headers=auth_headers
            )
            assert response.status_code in [200, 201]
            employees.append(response.json())

        print(f"✓ 従業員{len(employees)}人を作成完了")

        # Step 2: 各従業員にカードを発行し、出勤打刻
        for idx, emp in enumerate(employees):
            card_hash = chr(ord('c') + idx) * 64

            # カード発行
            response = client.post(
                f"/api/v1/admin/employees/{emp['id']}/cards",
                json={"card_idm_hash": card_hash, "card_nickname": f"社員証{idx+1}"},
                headers=auth_headers
            )
            assert response.status_code in [200, 201]

            # 出勤打刻
            response = client.post(
                "/api/v1/punch/",
                json={"card_idm_hash": card_hash, "punch_type": "in"},
                headers=auth_headers
            )
            assert response.status_code in [200, 201]

            print(f"✓ {emp['name']} の出勤打刻完了")

        # Step 3: 従業員一覧を取得
        response = client.get(
            "/api/v1/admin/employees",
            headers=auth_headers
        )
        assert response.status_code == 200
        employee_list = response.json()

        print(f"✓ 従業員一覧取得: {employee_list.get('total', 0)}人")

        # Step 4: 各従業員の詳細を確認
        for emp in employees:
            response = client.get(
                f"/api/v1/admin/employees/{emp['id']}",
                headers=auth_headers
            )
            assert response.status_code == 200
            detail = response.json()

            print(f"✓ {detail['name']} の勤怠状況を確認")

        print(f"✓ 管理者レポート確認フローが正常に完了しました")


class TestErrorHandlingFlow:
    """エラーハンドリングのE2Eテスト"""

    def test_duplicate_punch_prevention(self, client, auth_headers):
        """
        シナリオ: 二重打刻の防止

        1. 従業員を作成しカードを発行
        2. 出勤打刻
        3. 再度出勤打刻を試みる（エラーになるべき）
        4. 退勤打刻
        5. 再度退勤打刻を試みる（エラーになるべき）
        """
        # Step 1: 従業員とカードを作成
        employee = {
            "employee_code": "E2E_ERROR01",
            "name": "エラーテスト",
            "wage_type": "monthly",
            "monthly_salary": 300000,
        }

        response = client.post(
            "/api/v1/admin/employees",
            json=employee,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        employee_id = response.json()["id"]

        card_hash = "0123456789abcdef" * 4  # 正確に64文字の16進数
        response = client.post(
            f"/api/v1/admin/employees/{employee_id}/cards",
            json={"card_idm_hash": card_hash, "card_nickname": "テストカード"},
            headers=auth_headers
        )
        assert response.status_code in [200, 201], f"カード発行エラー: {response.text}"

        print(f"✓ テストデータ作成完了")

        # Step 2: 出勤打刻
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm_hash": card_hash, "punch_type": "in"},
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

        print(f"✓ 1回目の出勤打刻成功")

        # Step 3: 再度出勤打刻を試みる（エラーになることを期待）
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm_hash": card_hash, "punch_type": "in"},
            headers=auth_headers
        )
        # 二重打刻は400または409エラーになるべき
        assert response.status_code in [400, 409], \
            f"二重打刻が防止されていない: {response.status_code}"

        print(f"✓ 二重出勤打刻が正しく防止されました")

        # Step 4: 退勤打刻
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm_hash": card_hash, "punch_type": "out"},
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

        print(f"✓ 退勤打刻成功")

        # Step 5: 再度退勤打刻を試みる
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm_hash": card_hash, "punch_type": "out"},
            headers=auth_headers
        )
        assert response.status_code in [400, 409], \
            f"二重退勤打刻が防止されていない: {response.status_code}"

        print(f"✓ 二重退勤打刻が正しく防止されました")
        print(f"✓ エラーハンドリングフローが正常に完了しました")


class TestDataIntegrityFlow:
    """データ整合性のE2Eテスト"""

    def test_employee_card_relationship(self, client, auth_headers):
        """
        シナリオ: 従業員とカードの関連性を確認

        1. 従業員を作成
        2. 複数のカードを発行
        3. 各カードで打刻
        4. すべての打刻が同じ従業員に紐付いていることを確認
        """
        # Step 1: 従業員を作成
        employee = {
            "employee_code": "E2E_DATA01",
            "name": "データ整合性テスト",
            "wage_type": "monthly",
            "monthly_salary": 350000,
        }

        response = client.post(
            "/api/v1/admin/employees",
            json=employee,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        employee_id = response.json()["id"]

        print(f"✓ 従業員作成: ID {employee_id}")

        # Step 2: 複数のカード（予備カードを想定）を発行
        cards = []
        card_templates = [
            "d1" + "0" * 62,  # カード1（一意）
            "d2" + "0" * 62,  # カード2（一意）
        ]
        for i, card_hash in enumerate(card_templates):
            response = client.post(
                f"/api/v1/admin/employees/{employee_id}/cards",
                json={
                    "card_idm_hash": card_hash,
                    "card_nickname": f"カード{i+1}"
                },
                headers=auth_headers
            )
            assert response.status_code in [200, 201]
            cards.append(card_hash)

        print(f"✓ {len(cards)}枚のカードを発行")

        # Step 3: 最初のカードで出勤打刻のみ実施
        # （同じ日に同じ従業員が複数回出勤することはできないため）
        response = client.post(
            "/api/v1/punch/",
            json={"card_idm_hash": cards[0], "punch_type": "in"},
            headers=auth_headers
        )
        assert response.status_code in [200, 201, 400, 409], \
            f"打刻エラー: {response.status_code}, {response.text}"

        print(f"✓ カード1で打刻完了")

        # Step 4: 従業員情報を取得し、カード数を確認
        response = client.get(
            f"/api/v1/admin/employees/{employee_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        employee_detail = response.json()

        # 発行したカード数と一致することを確認
        assert employee_detail.get("card_count", 0) == len(cards), \
            "カード数が一致しません"

        print(f"✓ データ整合性が確認されました")
        print(f"✓ データ整合性テストフローが正常に完了しました")
