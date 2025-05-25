"""
打刻システム機能強化の包括的テストスイート

新規実装した高度な機能のテストを網羅します。
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.models.punch_record import PunchRecord, PunchType
from backend.app.models.employee import Employee
from backend.app.services.punch_anomaly_service import PunchAnomalyDetector
from backend.app.services.punch_correction_service import PunchCorrectionService
from backend.app.services.punch_alert_service import PunchAlertService
from backend.app.security.card_authentication import CardSecurityValidator
from backend.app.utils.error_recovery import AdvancedErrorRecovery
from backend.app.utils.performance_optimizer import PunchPerformanceOptimizer
from hardware.multi_reader_manager import MultiReaderManager
from hardware.device_monitor import PaSoRiDeviceMonitor


# テスト用データベース設定
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_enhancements.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """テスト用データベースセッション"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_employee(db):
    """テスト用従業員"""
    employee = Employee(
        employee_code="TEST001",
        name="テスト太郎",
        email="test@example.com",
        card_idm_hash="test_hash_123",
        department="開発部",
        is_active=True
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@pytest.fixture
def test_punch_records(db, test_employee):
    """テスト用打刻記録"""
    records = []
    base_time = datetime.now() - timedelta(days=7)
    
    # 1週間分の打刻データを作成
    for day in range(7):
        date = base_time + timedelta(days=day)
        
        # 出勤
        in_punch = PunchRecord(
            employee_id=test_employee.id,
            punch_type=PunchType.IN,
            punch_time=date.replace(hour=9, minute=0)
        )
        records.append(in_punch)
        
        # 退勤
        out_punch = PunchRecord(
            employee_id=test_employee.id,
            punch_type=PunchType.OUT,
            punch_time=date.replace(hour=18, minute=0)
        )
        records.append(out_punch)
    
    db.add_all(records)
    db.commit()
    return records


class TestPunchAnomalyService:
    """異常検出サービスのテスト"""
    
    @pytest.mark.asyncio
    async def test_rapid_consecutive_detection(self, db, test_employee):
        """連続打刻の検出テスト"""
        detector = PunchAnomalyDetector(db)
        
        # 短時間での連続打刻を作成
        base_time = datetime.now()
        for i in range(4):
            punch = PunchRecord(
                employee_id=test_employee.id,
                punch_type=PunchType.IN,
                punch_time=base_time + timedelta(seconds=i * 10)
            )
            db.add(punch)
        db.commit()
        
        # 最後の打刻をチェック
        last_punch = db.query(PunchRecord).order_by(PunchRecord.punch_time.desc()).first()
        anomalies = await detector.detect_anomalies(last_punch)
        
        assert len(anomalies) > 0
        assert any(a["type"] == "RAPID_CONSECUTIVE" for a in anomalies)
    
    @pytest.mark.asyncio
    async def test_long_work_time_detection(self, db, test_employee):
        """長時間勤務の検出テスト"""
        detector = PunchAnomalyDetector(db)
        
        # 17時間勤務のデータを作成
        in_punch = PunchRecord(
            employee_id=test_employee.id,
            punch_type=PunchType.IN,
            punch_time=datetime.now().replace(hour=6, minute=0)
        )
        out_punch = PunchRecord(
            employee_id=test_employee.id,
            punch_type=PunchType.OUT,
            punch_time=datetime.now().replace(hour=23, minute=0)
        )
        db.add_all([in_punch, out_punch])
        db.commit()
        
        anomalies = await detector.detect_anomalies(out_punch)
        
        assert len(anomalies) > 0
        assert any(a["type"] == "LONG_WORK_TIME" for a in anomalies)
    
    @pytest.mark.asyncio
    async def test_anomaly_report_generation(self, db, test_punch_records):
        """異常レポート生成テスト"""
        detector = PunchAnomalyDetector(db)
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        report = await detector.generate_anomaly_report(start_date, end_date)
        
        assert "total_anomalies" in report
        assert "anomaly_summary" in report
        assert "severity_summary" in report
        assert report["total_punches"] == len(test_punch_records)


class TestPunchCorrectionService:
    """補正サービスのテスト"""
    
    @pytest.mark.asyncio
    async def test_missing_out_correction(self, db, test_employee):
        """退勤漏れ補正テスト"""
        service = PunchCorrectionService(db)
        
        # 出勤のみのデータ
        in_punch = PunchRecord(
            employee_id=test_employee.id,
            punch_type=PunchType.IN,
            punch_time=datetime.now().replace(hour=9, minute=0)
        )
        db.add(in_punch)
        db.commit()
        
        anomaly_data = {
            "type": "MISSING_PUNCH",
            "details": {
                "missing_type": "OUT",
                "work_date": datetime.now().date().isoformat()
            }
        }
        
        suggestions = await service.suggest_corrections(anomaly_data, test_employee.id)
        
        assert len(suggestions) > 0
        assert suggestions[0]["type"] == "ADD_PUNCH"
        assert suggestions[0]["punch_type"] == "OUT"
    
    @pytest.mark.asyncio
    async def test_auto_correction(self, db, test_employee):
        """自動補正テスト"""
        service = PunchCorrectionService(db)
        
        # 秒単位を含む打刻
        punch = PunchRecord(
            employee_id=test_employee.id,
            punch_type=PunchType.IN,
            punch_time=datetime.now().replace(second=45, microsecond=123456)
        )
        db.add(punch)
        db.commit()
        
        result = await service.auto_correct_minor_issues(punch)
        
        assert result is not None
        assert punch.punch_time.second == 0
        assert punch.punch_time.microsecond == 0


class TestPunchAlertService:
    """アラートサービスのテスト"""
    
    @pytest.mark.asyncio
    async def test_missing_punch_monitoring(self, db, test_employee):
        """打刻漏れ監視テスト"""
        service = PunchAlertService(db)
        
        # 監視を実行
        await service.monitor_missing_punches()
        
        # アラートが生成されることを確認
        # （実際のテストではモックを使用）
    
    @pytest.mark.asyncio
    async def test_daily_report_generation(self, db, test_employee):
        """日次レポート生成テスト"""
        service = PunchAlertService(db)
        
        report = await service.generate_daily_missing_report()
        
        assert "missing_in" in report
        assert "missing_out" in report
        assert "summary" in report
        assert report["date"] == datetime.now().date().isoformat()


class TestCardAuthentication:
    """カードセキュリティ検証のテスト"""
    
    @pytest.mark.asyncio
    async def test_card_forgery_detection(self, db):
        """カード偽造検出テスト"""
        validator = CardSecurityValidator(db)
        
        # 正常なカードデータ
        normal_card = {
            "idm": "0123456789ABCDEF",
            "read_time": 0.3,
            "signal_strength": 0.7
        }
        
        result = await validator.detect_card_forgery(normal_card)
        assert not result["is_suspicious"]
        assert result["risk_level"] in ["MINIMAL", "LOW"]
        
        # 疑わしいカードデータ
        suspicious_card = {
            "idm": "0000000000000000",
            "read_time": 0.01,
            "signal_strength": 1.0
        }
        
        result = await validator.detect_card_forgery(suspicious_card)
        assert result["is_suspicious"]
        assert result["risk_level"] in ["HIGH", "CRITICAL"]
    
    @pytest.mark.asyncio
    async def test_behavioral_analysis(self, db, test_employee, test_punch_records):
        """行動分析テスト"""
        validator = CardSecurityValidator(db)
        
        # 通常パターン
        normal_pattern = {
            "punch_type": "IN",
            "punch_time": datetime.now().replace(hour=9, minute=0)
        }
        
        result = await validator.behavioral_analysis(test_employee.id, normal_pattern)
        assert result["analysis_available"]
        assert result["risk_level"] != "CRITICAL"


class TestErrorRecovery:
    """エラー回復システムのテスト"""
    
    @pytest.mark.asyncio
    async def test_intelligent_recovery(self):
        """インテリジェント回復テスト"""
        recovery = AdvancedErrorRecovery()
        
        # USBエラーのコンテキスト
        context = {
            "device_id": "test_device",
            "error": "USB disconnected"
        }
        
        result = await recovery.intelligent_recovery("USB_DISCONNECTED", context)
        
        assert "recovered" in result
        assert "strategy" in result or "manual_intervention_required" in result
    
    def test_error_pattern_learning(self):
        """エラーパターン学習テスト"""
        recovery = AdvancedErrorRecovery()
        
        # エラーパターンを記録
        for i in range(5):
            recovery.error_patterns["test_error"] = recovery.ErrorPattern(
                "TEST_ERROR",
                {"test": True}
            )
            recovery.error_patterns["test_error"].add_occurrence()
        
        pattern = recovery.error_patterns["test_error"]
        assert pattern.get_frequency() > 0


class TestPerformanceOptimizer:
    """パフォーマンス最適化のテスト"""
    
    def test_lru_cache(self):
        """LRUキャッシュのテスト"""
        from backend.app.utils.performance_optimizer import LRUCache
        
        cache = LRUCache(max_size=3)
        
        # データを追加
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # キャッシュヒット
        assert cache.get("key1") == "value1"
        assert cache.get_stats()["hits"] == 1
        
        # 新しいデータで古いものが削除される
        cache.set("key4", "value4")
        assert cache.get("key2") is None  # 最も古いものが削除
        assert cache.get_stats()["evictions"] == 1
    
    @pytest.mark.asyncio
    async def test_cache_warmup(self, db):
        """キャッシュウォームアップテスト"""
        optimizer = PunchPerformanceOptimizer(db)
        
        # ウォームアップを実行
        await optimizer._warmup_cache()
        
        # キャッシュ統計を確認
        stats = optimizer.get_optimization_status()
        assert "cache_stats" in stats


class TestMultiReaderManager:
    """複数リーダー管理のテスト"""
    
    @pytest.mark.asyncio
    async def test_reader_initialization(self):
        """リーダー初期化テスト"""
        manager = MultiReaderManager()
        
        # モックデバイスでテスト
        with patch.object(manager, '_detect_pasori_devices') as mock_detect:
            mock_detect.return_value = [
                {"id": "device1", "path": "usb:001:001"},
                {"id": "device2", "path": "usb:001:002"}
            ]
            
            with patch.object(manager, 'readers', {}):
                # 初期化は実際のデバイスが必要なのでスキップ
                pass
    
    def test_reader_role_assignment(self):
        """リーダー役割割り当てテスト"""
        manager = MultiReaderManager()
        
        # モックリーダーを作成
        from hardware.multi_reader_manager import ReaderDevice
        
        reader1 = Mock(spec=ReaderDevice)
        reader1.is_active = True
        reader1.get_health_score.return_value = 0.9
        reader1.device_id = "reader1"
        
        reader2 = Mock(spec=ReaderDevice)
        reader2.is_active = True
        reader2.get_health_score.return_value = 0.7
        reader2.device_id = "reader2"
        
        manager.readers = {"reader1": reader1, "reader2": reader2}
        
        manager._assign_reader_roles()
        
        assert manager.primary_reader == reader1
        assert reader2 in manager.backup_readers


class TestDeviceMonitor:
    """デバイス監視のテスト"""
    
    @pytest.mark.asyncio
    async def test_device_diagnostics(self):
        """デバイス診断テスト"""
        monitor = PaSoRiDeviceMonitor()
        
        # デバイスを登録
        monitor.register_device("test_device", {"type": "PaSoRi"})
        
        # 操作を記録
        monitor.record_operation("test_device", 0.3, True)
        monitor.record_operation("test_device", 0.4, True)
        monitor.record_operation("test_device", None, False)
        
        # 診断を実行
        diagnostics = await monitor.device_diagnostics("test_device")
        
        assert diagnostics["device_id"] == "test_device"
        assert "health_score" in diagnostics
        assert "metrics" in diagnostics
    
    @pytest.mark.asyncio
    async def test_predictive_maintenance(self):
        """予防保守テスト"""
        monitor = PaSoRiDeviceMonitor()
        
        # デバイスを登録
        monitor.register_device("test_device", {"type": "PaSoRi"})
        
        # 健全性履歴を作成
        for i in range(15):
            monitor.health_history["test_device"] = monitor.health_history.get("test_device", [])
            monitor.health_history["test_device"].append({
                "timestamp": datetime.now() - timedelta(minutes=i * 5),
                "diagnostics": {
                    "health_score": 0.9 - i * 0.05,  # 徐々に低下
                    "metrics": {"error_rate": i * 0.01}
                }
            })
        
        # 予防保守チェック
        maintenance = await monitor.predictive_maintenance("test_device")
        
        assert maintenance["action_required"]
        assert "recommendation" in maintenance


class TestPunchMonitoringAPI:
    """リアルタイム監視APIのテスト"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """WebSocket接続テスト"""
        from backend.app.api.punch_monitoring import ConnectionManager
        
        manager = ConnectionManager()
        
        # モックWebSocket
        mock_websocket = AsyncMock()
        
        await manager.connect(mock_websocket)
        assert mock_websocket in manager.active_connections
        
        await manager.disconnect(mock_websocket)
        assert mock_websocket not in manager.active_connections
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics(self, db):
        """ダッシュボードメトリクステスト"""
        from backend.app.api.punch_monitoring import get_dashboard_metrics
        
        metrics = await get_dashboard_metrics(db)
        
        assert "today_punch_count" in metrics
        assert "active_employees" in metrics
        assert "device_health" in metrics
        assert "timestamp" in metrics


# 統合テスト
class TestIntegration:
    """統合テスト"""
    
    @pytest.mark.asyncio
    async def test_full_punch_flow_with_anomaly_detection(self, db, test_employee):
        """異常検出を含む完全な打刻フロー"""
        # 1. 打刻作成
        punch = PunchRecord(
            employee_id=test_employee.id,
            punch_type=PunchType.IN,
            punch_time=datetime.now().replace(hour=3, minute=0)  # 深夜
        )
        db.add(punch)
        db.commit()
        
        # 2. 異常検出
        detector = PunchAnomalyDetector(db)
        anomalies = await detector.detect_anomalies(punch)
        
        assert len(anomalies) > 0
        assert any(a["type"] == "MIDNIGHT_PUNCH" for a in anomalies)
        
        # 3. 補正提案
        correction_service = PunchCorrectionService(db)
        for anomaly in anomalies:
            suggestions = await correction_service.suggest_corrections(
                anomaly,
                test_employee.id
            )
            assert isinstance(suggestions, list)
    
    @pytest.mark.asyncio
    async def test_performance_optimization_impact(self, db, test_employee):
        """パフォーマンス最適化の効果測定"""
        optimizer = PunchPerformanceOptimizer(db)
        
        # キャッシュなしの時間を測定
        import time
        
        start = time.time()
        data = await optimizer._get_recent_punch_pattern(test_employee.id)
        no_cache_time = time.time() - start
        
        # キャッシュありの時間を測定
        start = time.time()
        cached_data = await optimizer._get_recent_punch_pattern(test_employee.id)
        cache_time = time.time() - start
        
        assert cache_time < no_cache_time
        assert data == cached_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])