#!/usr/bin/env python3
"""
FeliCa API テストスクリプト
実際のハードウェアなしでAPIの動作確認
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"

def test_felica_attendance():
    """FeliCa勤怠記録テスト"""
    print("🧪 FeliCa勤怠記録APIテスト")
    
    # テスト用のダミーFeliCa IDM (16文字)
    test_idm = "012345678ABCDEF0"
    
    payload = {
        "felica_idm": test_idm,
        "timestamp": datetime.utcnow().isoformat(),
        "reader_id": "test-reader-001",
        "method": "felica"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/felica-attendance",
            json=payload,
            timeout=5
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 404:
            print("❌ 未登録のカードです（期待通り）")
        elif response.status_code == 200:
            print("✅ 勤怠記録成功")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

def test_felica_registration():
    """FeliCaカード登録テスト"""
    print("\n🧪 FeliCaカード登録APIテスト")
    
    # テスト用のダミーデータ
    payload = {
        "user_id": 1,  # 田中太郎
        "felica_idm": "012345678ABCDEF0"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/admin/felica/register",
            json=payload,
            timeout=5
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✅ カード登録成功")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

def test_user_list():
    """ユーザー一覧確認"""
    print("\n📋 登録ユーザー一覧")
    
    try:
        response = requests.get(f"{BASE_URL}/api/admin/users")
        users = response.json()
        
        for user in users[:3]:  # 最初の3人表示
            print(f"ID: {user['id']}, 名前: {user['name']}, 社員ID: {user['employee_id']}")
    
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    print("🎯 FeliCa API動作確認テスト")
    print("=" * 50)
    
    # ユーザー一覧表示
    test_user_list()
    
    # カード登録テスト
    test_felica_registration()
    
    # 勤怠記録テスト
    test_felica_attendance()
    
    print("\n✅ テスト完了")