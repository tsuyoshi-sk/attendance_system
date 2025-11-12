#!/usr/bin/env python3
"""
勤怠管理システム 包括的テストスクリプト
世界最高レベルのエンタープライズ級iPhone Suica対応システム検証
"""

import asyncio
import json
import time
import requests
import websockets
from concurrent.futures import ThreadPoolExecutor
import threading
import sys

# テスト設定
BASE_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/ws"
TEST_IDM = "0123456789ABCDEF"

class ComprehensiveSystemTest:
    def __init__(self):
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        
    def log(self, message, status="INFO"):
        print(f"[{status}] {message}")
        
    def test_api_health(self):
        """APIヘルスチェック"""
        self.log("Testing API Health Check...")
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Health Check: {data['status']}")
                self.passed_tests += 1
                return True
        except Exception as e:
            self.log(f"❌ Health Check Failed: {e}", "ERROR")
        self.total_tests += 1
        return False
        
    def test_nfc_functionality(self):
        """NFC機能テスト"""
        self.log("Testing NFC Functionality...")
        try:
            # NFC IDMハッシュ化テスト
            response = requests.post(
                f"{BASE_URL}/api/nfc/process_idm",
                json={"idm": TEST_IDM},
                timeout=5
            )
            if response.status_code == 200:
                self.log("✅ NFC IDM Processing: OK")
                self.passed_tests += 1
                return True
        except Exception as e:
            self.log(f"❌ NFC Test Failed: {e}", "ERROR")
        self.total_tests += 1
        return False
        
    def test_attendance_punch(self):
        """打刻機能テスト"""
        self.log("Testing Attendance Punch...")
        try:
            # 出勤打刻
            response = requests.post(
                f"{BASE_URL}/api/punch/in",
                json={
                    "idm": TEST_IDM,
                    "location": "本社",
                    "device_id": "test_device_001"
                },
                timeout=5
            )
            if response.status_code in [200, 201]:
                self.log("✅ Attendance Punch In: OK")
                self.passed_tests += 1
                return True
        except Exception as e:
            self.log(f"❌ Punch Test Failed: {e}", "ERROR")
        self.total_tests += 1
        return False
        
    async def test_websocket_connection(self):
        """WebSocket接続テスト"""
        self.log("Testing WebSocket Connection...")
        try:
            async with websockets.connect(WS_URL) as websocket:
                # 接続テスト
                test_message = {
                    "type": "nfc_scan",
                    "data": {
                        "idm": TEST_IDM,
                        "location": "test_location"
                    }
                }
                await websocket.send(json.dumps(test_message))
                
                # レスポンス待機
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                if response:
                    self.log("✅ WebSocket Communication: OK")
                    self.passed_tests += 1
                    return True
        except Exception as e:
            self.log(f"❌ WebSocket Test Failed: {e}", "ERROR")
        self.total_tests += 1
        return False
        
    def test_performance_load(self):
        """パフォーマンステスト"""
        self.log("Testing Performance (10 concurrent requests)...")
        
        def make_request():
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=10)
                return response.status_code == 200
            except:
                return False
                
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]
            
        end_time = time.time()
        success_rate = sum(results) / len(results) * 100
        duration = end_time - start_time
        
        if success_rate >= 90:
            self.log(f"✅ Performance Test: {success_rate:.1f}% success in {duration:.2f}s")
            self.passed_tests += 1
        else:
            self.log(f"❌ Performance Test: {success_rate:.1f}% success", "ERROR")
        self.total_tests += 1
        
    def test_security_headers(self):
        """セキュリティヘッダーテスト"""
        self.log("Testing Security Headers...")
        try:
            response = requests.get(f"{BASE_URL}/app", timeout=5)
            headers = response.headers
            
            security_checks = [
                ("X-Content-Type-Options", "nosniff"),
                ("X-Frame-Options", "DENY"),
                ("X-XSS-Protection", "1; mode=block")
            ]
            
            passed = 0
            for header, expected in security_checks:
                if header in headers and expected in headers[header]:
                    passed += 1
                    
            if passed >= 2:  # 最低2つのセキュリティヘッダー
                self.log("✅ Security Headers: OK")
                self.passed_tests += 1
            else:
                self.log("❌ Security Headers: Insufficient", "ERROR")
        except Exception as e:
            self.log(f"❌ Security Test Failed: {e}", "ERROR")
        self.total_tests += 1
        
    def test_pwa_functionality(self):
        """PWA機能テスト"""
        self.log("Testing PWA Functionality...")
        try:
            # Manifest.json テスト
            response = requests.get(f"{BASE_URL}/manifest.json", timeout=5)
            if response.status_code == 200:
                manifest = response.json()
                if "name" in manifest and "icons" in manifest:
                    self.log("✅ PWA Manifest: OK")
                    
            # Service Worker テスト
            response = requests.get(f"{BASE_URL}/sw.js", timeout=5)
            if response.status_code == 200:
                self.log("✅ Service Worker: OK")
                self.passed_tests += 1
                return True
        except Exception as e:
            self.log(f"❌ PWA Test Failed: {e}", "ERROR")
        self.total_tests += 1
        return False
        
    async def run_all_tests(self):
        """全テスト実行"""
        self.log("=" * 60)
        self.log("🚀 勤怠管理システム 包括的テスト開始")
        self.log("=" * 60)
        
        # 同期テスト
        tests = [
            self.test_api_health,
            self.test_nfc_functionality,
            self.test_attendance_punch,
            self.test_performance_load,
            self.test_security_headers,
            self.test_pwa_functionality
        ]
        
        for test in tests:
            test()
            time.sleep(0.5)
            
        # 非同期テスト
        await self.test_websocket_connection()
        
        # 結果表示
        self.log("=" * 60)
        self.log("📊 テスト結果サマリー")
        self.log("=" * 60)
        success_rate = (self.passed_tests / self.total_tests) * 100
        self.log(f"総テスト数: {self.total_tests}")
        self.log(f"成功: {self.passed_tests}")
        self.log(f"失敗: {self.total_tests - self.passed_tests}")
        self.log(f"成功率: {success_rate:.1f}%")
        
        if success_rate >= 85:
            self.log("🎉 システム品質: EXCELLENT", "SUCCESS")
        elif success_rate >= 70:
            self.log("✅ システム品質: GOOD", "SUCCESS")
        else:
            self.log("⚠️  システム品質: NEEDS IMPROVEMENT", "WARNING")
            
        self.log("=" * 60)
        self.log("📱 次のテストステップ:")
        self.log("1. ブラウザで http://localhost:8001/app をテスト")
        self.log("2. iPhone実機でSuicaテスト")
        self.log("3. 高負荷テスト実行")
        self.log("=" * 60)

if __name__ == "__main__":
    test_runner = ComprehensiveSystemTest()
    asyncio.run(test_runner.run_all_tests())