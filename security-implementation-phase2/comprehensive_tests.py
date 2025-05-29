"""
包括的セキュリティテストスイート
Phase 3で使用予定
"""
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from security_manager_full import SecurityManager

class TestSecurityManagerAdvanced:
    """高度なセキュリティテスト"""
    
    def test_concurrent_nfc_processing(self):
        """並行NFC処理のテスト"""
        sm = SecurityManager()
        test_idms = [f"TEST{i:012X}" for i in range(100)]
        
        def process_idm(idm):
            secured = sm.secure_nfc_idm(idm)
            return sm.verify_nfc_idm(idm, secured)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(process_idm, test_idms))
        
        assert all(results), "All concurrent NFC processing should succeed"
    
    def test_timing_attack_resistance(self):
        """タイミング攻撃耐性テスト"""
        sm = SecurityManager()
        test_idm = "0123456789ABCDEF"
        secured = sm.secure_nfc_idm(test_idm)
        
        # 正しい検証の時間測定
        times_correct = []
        for _ in range(100):
            start = time.perf_counter()
            sm.verify_nfc_idm(test_idm, secured)
            times_correct.append(time.perf_counter() - start)
        
        # 間違った検証の時間測定
        times_wrong = []
        for _ in range(100):
            start = time.perf_counter()
            sm.verify_nfc_idm("WRONG_IDM", secured)
            times_wrong.append(time.perf_counter() - start)
        
        avg_correct = sum(times_correct) / len(times_correct)
        avg_wrong = sum(times_wrong) / len(times_wrong)
        
        # タイミング差が10%以内であることを確認
        timing_diff = abs(avg_correct - avg_wrong) / max(avg_correct, avg_wrong)
        assert timing_diff < 0.1, f"Timing attack vulnerability detected: {timing_diff}"
    
    def test_session_security(self):
        """セッションセキュリティテスト"""
        sm = SecurityManager()
        
        # セッション作成
        session_id = sm.create_session("user123", "192.168.1.100")
        
        # 正常な検証
        session = sm.validate_session(session_id, "192.168.1.100")
        assert session is not None
        assert session['user_id'] == "user123"
        
        # IPアドレス変更による無効化
        invalid_session = sm.validate_session(session_id, "192.168.1.200")
        assert invalid_session is None
    
    def test_rate_limiting(self):
        """レート制限テスト"""
        sm = SecurityManager()
        client_id = "test_client"
        
        # 制限内でのリクエスト
        for _ in range(50):
            assert sm.check_rate_limit(client_id, limit=100) is True
        
        # 制限を超えるリクエスト
        for _ in range(60):
            sm.check_rate_limit(client_id, limit=100)
        
        # 制限に達した後は拒否される
        assert sm.check_rate_limit(client_id, limit=100) is False
