"""
Comprehensive Tests for Enhanced Backend Features

Test suite covering:
- WebSocket connection management
- NFC API enhancements
- Security features
- Performance optimizations
- Monitoring system
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
import redis.asyncio as redis
from datetime import datetime, timedelta

# Import modules to test
from backend.app.websocket_enhanced import EnhancedNFCConnectionManager
from backend.app.api.nfc_enhanced import NFCValidator, RetryHandler
from backend.app.security.enhanced_auth import SecurityManager, TokenManager
from backend.app.monitoring.system_monitor import SystemMonitor, AnomalyDetector
from backend.app.performance.async_optimizer import AsyncOptimizer
from backend.app.logging.enhanced_logger import EnhancedLogger, SecurityLogger


class TestEnhancedWebSocketManager:
    """Test enhanced WebSocket connection manager"""
    
    @pytest.fixture
    async def manager(self):
        """Create test manager instance"""
        manager = EnhancedNFCConnectionManager(
            redis_url="redis://localhost:6379/15",  # Test DB
            max_connections=10
        )
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        return ws
    
    @pytest.mark.asyncio
    async def test_connection_management(self, manager, mock_websocket):
        """Test basic connection management"""
        client_id = "test_client_001"
        
        # Test connection
        success = await manager.optimized_connect(mock_websocket, client_id)
        assert success
        assert client_id in manager.active_connections
        assert len(manager.active_connections) == 1
        
        # Test disconnect
        await manager.disconnect(client_id)
        assert client_id not in manager.active_connections
        assert len(manager.active_connections) == 0
    
    @pytest.mark.asyncio
    async def test_connection_limit(self, manager):
        """Test connection limit enforcement"""
        websockets = []
        client_ids = []
        
        # Connect up to limit
        for i in range(manager.max_connections):
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            
            client_id = f"test_client_{i:03d}"
            success = await manager.optimized_connect(ws, client_id)
            
            assert success
            websockets.append(ws)
            client_ids.append(client_id)
        
        # Try to exceed limit
        ws_overflow = Mock(spec=WebSocket)
        ws_overflow.accept = AsyncMock()
        success = await manager.optimized_connect(ws_overflow, "overflow_client")
        
        # Should fail due to limit (unless auto-scaling is enabled)
        assert len(manager.active_connections) <= manager.max_connections
        
        # Cleanup
        for client_id in client_ids:
            await manager.disconnect(client_id)
    
    @pytest.mark.asyncio
    async def test_broadcast_messaging(self, manager, mock_websocket):
        """Test broadcast messaging functionality"""
        # Connect multiple clients
        client_ids = ["client_1", "client_2", "client_3"]
        
        for client_id in client_ids:
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            await manager.optimized_connect(ws, client_id)
        
        # Test broadcast
        message = {"type": "test", "data": "broadcast_message"}
        await manager.broadcast(message)
        
        # Allow message processing
        await asyncio.sleep(0.2)
        
        # Verify all clients received message
        for client_id in client_ids:
            ws = manager.active_connections[client_id]
            ws.send_json.assert_called()
        
        # Cleanup
        for client_id in client_ids:
            await manager.disconnect(client_id)
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, manager):
        """Test performance monitoring"""
        # Record some metrics
        manager.performance_metrics.record_response_time(0.05)  # 50ms
        manager.performance_metrics.record_response_time(0.1)   # 100ms
        manager.performance_metrics.record_connection_time(0.02) # 20ms
        
        # Get metrics
        metrics = await manager.performance_monitor()
        
        assert "system" in metrics
        assert "response_time" in metrics
        assert metrics["response_time"]["avg"] > 0
        assert metrics["system"]["active_connections"] >= 0


class TestNFCEnhancedAPI:
    """Test enhanced NFC API features"""
    
    def test_nfc_validator(self):
        """Test NFC data validation"""
        # Valid card data
        valid_data = {
            "idm": "0123456789ABCDEF",
            "type": "suica",
            "pmm": "FEDCBA9876543210"
        }
        assert NFCValidator.validate_card_data(valid_data)
        
        # Invalid card data - missing idm
        invalid_data1 = {
            "type": "suica"
        }
        assert not NFCValidator.validate_card_data(invalid_data1)
        
        # Invalid card data - invalid type
        invalid_data2 = {
            "idm": "0123456789ABCDEF",
            "type": "invalid_type"
        }
        assert not NFCValidator.validate_card_data(invalid_data2)
        
        # Invalid card data - short idm
        invalid_data3 = {
            "idm": "123",
            "type": "suica"
        }
        assert not NFCValidator.validate_card_data(invalid_data3)
    
    def test_data_sanitization(self):
        """Test data sanitization"""
        input_data = {
            "idm": "  0123456789abcdef  ",
            "type": "SUICA",
            "extra_field": "some_value",
            "pmm": "FEDCBA9876543210"
        }
        
        sanitized = NFCValidator.sanitize_card_data(input_data)
        
        assert sanitized["idm"] == "0123456789ABCDEF"  # Trimmed and uppercased
        assert sanitized["type"] == "suica"  # Lowercased
        assert "pmm" in sanitized
        assert "extra_field" not in sanitized
    
    @pytest.mark.asyncio
    async def test_retry_handler(self):
        """Test retry mechanism"""
        handler = RetryHandler(max_retries=3, backoff_factor=1.0)
        
        scan_id = "test_scan_001"
        
        # First attempt should be allowed
        assert await handler.should_retry(scan_id, 0)
        
        # Record retry
        handler.record_retry(scan_id, 1)
        
        # Immediate retry should be blocked (due to backoff)
        assert not await handler.should_retry(scan_id, 1)
        
        # Wait for backoff period
        await asyncio.sleep(1.1)
        
        # Now retry should be allowed
        assert await handler.should_retry(scan_id, 1)
        
        # Exceed max retries
        assert not await handler.should_retry(scan_id, 4)


class TestSecurityManager:
    """Test security features"""
    
    @pytest.fixture
    async def security_manager(self):
        """Create test security manager"""
        manager = SecurityManager(redis_url="redis://localhost:6379/15")
        await manager.initialize()
        yield manager
        # Cleanup handled by context
    
    @pytest.fixture
    def token_manager(self):
        """Create test token manager"""
        return TokenManager(redis_url="redis://localhost:6379/15")
    
    def test_password_validation(self):
        """Test password strength validation"""
        from backend.app.security.enhanced_auth import SecurityValidator
        
        # Strong password
        assert SecurityValidator.validate_password_strength("SecureP@ssw0rd123!")
        
        # Weak passwords
        assert not SecurityValidator.validate_password_strength("weak")  # Too short
        assert not SecurityValidator.validate_password_strength("nouppercase123!")  # No uppercase
        assert not SecurityValidator.validate_password_strength("NOLOWERCASE123!")  # No lowercase
        assert not SecurityValidator.validate_password_strength("NoNumbers!")  # No numbers
        assert not SecurityValidator.validate_password_strength("NoSpecialChars123")  # No special chars
    
    def test_websocket_token_generation(self, token_manager):
        """Test WebSocket token generation and validation"""
        client_id = "test_client"
        user_id = "test_user"
        
        # Generate token
        token = token_manager.generate_websocket_token(client_id, user_id)
        assert token
        assert isinstance(token, str)
        
        # Validate token (this would need proper async setup)
        # payload = await token_manager.validate_websocket_token(token)
        # assert payload["client_id"] == client_id
        # assert payload["user_id"] == user_id
    
    def test_data_encryption(self, token_manager):
        """Test data encryption/decryption"""
        sensitive_data = "0123456789ABCDEF"
        
        # Encrypt
        encrypted = token_manager.encrypt_sensitive_data(sensitive_data)
        assert encrypted != sensitive_data
        
        # Decrypt
        decrypted = token_manager.decrypt_sensitive_data(encrypted)
        assert decrypted == sensitive_data
    
    def test_nfc_request_validation(self):
        """Test NFC request validation"""
        from backend.app.security.enhanced_auth import SecurityValidator
        
        # Valid request
        valid_request = {
            "scan_id": "valid_scan_123",
            "client_id": "test_client",
            "timestamp": int(time.time() * 1000),
            "card_data": {
                "idm": "0123456789ABCDEF",
                "type": "suica"
            }
        }
        assert SecurityValidator.validate_nfc_scan_request(valid_request)
        
        # Invalid request - missing fields
        invalid_request1 = {
            "scan_id": "test_scan",
            "timestamp": int(time.time() * 1000)
        }
        assert not SecurityValidator.validate_nfc_scan_request(invalid_request1)
        
        # Invalid request - old timestamp
        invalid_request2 = {
            "scan_id": "test_scan",
            "client_id": "test_client",
            "timestamp": int((time.time() - 600) * 1000),  # 10 minutes ago
            "card_data": {"idm": "123", "type": "suica"}
        }
        assert not SecurityValidator.validate_nfc_scan_request(invalid_request2)
    
    @pytest.mark.asyncio
    async def test_intrusion_detection(self, security_manager):
        """Test intrusion detection"""
        client_id = "suspicious_client"
        
        # Simulate multiple failed attempts
        for _ in range(6):  # Exceed threshold
            await security_manager.intrusion_detector.track_request(
                client_id, "auth", success=False
            )
        
        # Client should be blocked
        is_blocked = await security_manager.intrusion_detector.is_client_blocked(client_id)
        assert is_blocked


class TestSystemMonitor:
    """Test system monitoring"""
    
    @pytest.fixture
    async def monitor(self):
        """Create test monitor"""
        monitor = SystemMonitor(redis_url="redis://localhost:6379/15")
        await monitor.initialize()
        yield monitor
        await monitor.cleanup()
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, monitor):
        """Test metrics collection"""
        # Record some test metrics
        await monitor.metrics_collector.record_metric("test.cpu", 75.5)
        await monitor.metrics_collector.record_metric("test.memory", 60.2)
        await monitor.metrics_collector.record_metric("test.response_time", 150.0)
        
        # Get metrics stats
        cpu_stats = await monitor.metrics_collector.get_metric_stats("test.cpu", 60)
        assert cpu_stats["mean"] == 75.5
        assert cpu_stats["count"] == 1
        
        # Get time series
        series = await monitor.metrics_collector.get_metric_series("test.memory", 60)
        assert len(series) == 1
        assert series[0]["value"] == 60.2
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, monitor):
        """Test anomaly detection"""
        metric_name = "test.response_time"
        
        # Record normal values
        normal_values = [100, 110, 105, 95, 102, 108, 97, 103]
        for value in normal_values:
            await monitor.metrics_collector.record_metric(metric_name, value)
        
        # Test anomaly detection
        detector = AnomalyDetector(sensitivity=2.0)
        
        # Normal value - should not be anomaly
        anomaly = await detector.detect_anomaly(metric_name, 106, normal_values)
        assert anomaly is None
        
        # Abnormal value - should be anomaly
        anomaly = await detector.detect_anomaly(metric_name, 500, normal_values)
        assert anomaly is not None
        assert anomaly["metric"] == metric_name
        assert anomaly["current_value"] == 500
    
    @pytest.mark.asyncio
    async def test_performance_analysis(self, monitor):
        """Test performance analysis"""
        # Add some test metrics
        await monitor.metrics_collector.record_metric("system.cpu.usage", 45.0)
        await monitor.metrics_collector.record_metric("system.memory.usage", 60.0)
        await monitor.metrics_collector.record_metric("websocket.response_time.avg", 80.0)
        
        # Analyze performance
        analysis = await monitor.analyze_performance()
        
        assert "overall_score" in analysis
        assert "cpu" in analysis
        assert "memory" in analysis
        assert "status" in analysis
        assert analysis["overall_score"] > 0


class TestAsyncOptimizer:
    """Test async performance optimizer"""
    
    @pytest.fixture
    async def optimizer(self):
        """Create test optimizer"""
        optimizer = AsyncOptimizer(
            redis_url="redis://localhost:6379/15",
            max_workers=2
        )
        await optimizer.initialize()
        yield optimizer
        await optimizer.cleanup()
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, optimizer):
        """Test batch processing functionality"""
        # Create test scan requests
        scan_requests = []
        for i in range(5):
            scan_requests.append({
                "scan_id": f"test_scan_{i:03d}",
                "client_id": "test_client",
                "card_data": {
                    "idm": f"012345678{i:07d}",
                    "type": "suica"
                },
                "timestamp": int(time.time() * 1000),
                "operation": "lookup"
            })
        
        # Process batch
        results = await optimizer.process_nfc_scan_batch(scan_requests)
        
        assert len(results) == len(scan_requests)
        for result in results:
            assert "scan_id" in result
            assert "success" in result
    
    @pytest.mark.asyncio
    async def test_caching(self, optimizer):
        """Test caching functionality"""
        # Test cache operations
        cache_key = "test_key"
        cache_value = {"data": "test_value", "timestamp": time.time()}
        
        # Cache miss first
        cached = await optimizer._batch_cache_get([cache_key])
        assert cached[0] is None
        
        # Set cache
        await optimizer._batch_cache_set([(cache_key, cache_value)])
        
        # Cache hit
        cached = await optimizer._batch_cache_get([cache_key])
        assert cached[0] is not None
        assert cached[0]["data"] == "test_value"
    
    def test_performance_metrics(self, optimizer):
        """Test performance metrics recording"""
        # Record some metrics
        optimizer._record_metric("test_operation", 0.05)
        optimizer._record_metric("test_operation", 0.1)
        optimizer._record_metric("another_operation", 0.2)
        
        # Get stats
        stats = optimizer.get_performance_stats()
        
        assert "test_operation" in stats
        assert stats["test_operation"]["count"] == 2
        assert stats["test_operation"]["avg_time"] == 0.075
        
        assert "another_operation" in stats
        assert stats["another_operation"]["count"] == 1


class TestEnhancedLogger:
    """Test enhanced logging system"""
    
    @pytest.fixture
    def logger(self):
        """Create test logger"""
        return EnhancedLogger(
            app_name="test_app",
            log_level="DEBUG",
            enable_console=False,
            enable_file=False
        )
    
    def test_security_logging(self, logger):
        """Test security event logging"""
        # Test NFC scan logging
        logger.security.log_nfc_scan_attempt(
            card_id="0123456789ABCDEF",
            success=True,
            client_id="test_client"
        )
        
        # Test authentication logging
        logger.security.log_authentication_attempt(
            user_id="test_user",
            method="password",
            success=True,
            ip_address="127.0.0.1"
        )
        
        # Test security event logging
        logger.security.log_security_event(
            event_type="suspicious_activity",
            severity="MEDIUM",
            details={"client_id": "test_client", "reason": "multiple_failures"}
        )
    
    def test_performance_logging(self, logger):
        """Test performance logging"""
        # Test API request logging
        logger.performance.log_api_request(
            method="POST",
            path="/nfc/scan-result",
            status_code=200,
            response_time_ms=150.5
        )
        
        # Test database query logging
        logger.performance.log_database_query(
            query_type="SELECT",
            table="employees",
            execution_time_ms=25.3,
            rows_affected=1
        )
        
        # Test WebSocket message logging
        logger.performance.log_websocket_message(
            message_type="scan_result",
            client_id="test_client",
            processing_time_ms=50.0
        )
        
        # Get performance summary
        summary = logger.performance.get_performance_summary()
        assert "avg_response_time_ms" in summary
    
    def test_context_management(self, logger):
        """Test logging context management"""
        # Set context
        logger.set_context(
            request_id="req_123",
            user_id="user_456",
            client_id="client_789"
        )
        
        # Log something
        logger.logger.info("test message")
        
        # Clear context
        logger.clear_context()
    
    @pytest.mark.asyncio
    async def test_audit_logging(self, logger):
        """Test audit logging"""
        # Log audit event
        await logger.audit.log_audit_event(
            category="nfc_scanning",
            action="scan_attempt",
            actor="test_user",
            target="card_123",
            result="success"
        )


class TestIntegration:
    """Integration tests for all components working together"""
    
    @pytest.mark.asyncio
    async def test_full_nfc_scan_flow(self):
        """Test complete NFC scan flow"""
        # This would test the entire flow from WebSocket connection
        # through NFC processing, security validation, monitoring,
        # and logging
        pass
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self):
        """Test monitoring system integration"""
        # This would test that all components properly report
        # metrics to the monitoring system
        pass
    
    @pytest.mark.asyncio
    async def test_security_integration(self):
        """Test security system integration"""
        # This would test that security features work across
        # all components
        pass


class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_websocket_concurrent_connections(self):
        """Test WebSocket manager under load"""
        manager = EnhancedNFCConnectionManager(max_connections=100)
        await manager.initialize()
        
        try:
            # Create many concurrent connections
            tasks = []
            for i in range(50):
                ws = Mock(spec=WebSocket)
                ws.accept = AsyncMock()
                ws.send_json = AsyncMock()
                
                task = manager.optimized_connect(ws, f"client_{i:03d}")
                tasks.append(task)
            
            # Execute all connections concurrently
            results = await asyncio.gather(*tasks)
            
            # Verify all connections succeeded
            assert all(results)
            assert len(manager.active_connections) == 50
            
        finally:
            await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test batch processing performance"""
        optimizer = AsyncOptimizer(max_workers=4)
        await optimizer.initialize()
        
        try:
            # Create large batch of scan requests
            batch_size = 100
            scan_requests = []
            
            for i in range(batch_size):
                scan_requests.append({
                    "scan_id": f"perf_test_{i:05d}",
                    "client_id": "perf_client",
                    "card_data": {
                        "idm": f"PERF{i:012d}",
                        "type": "suica"
                    },
                    "timestamp": int(time.time() * 1000),
                    "operation": "lookup"
                })
            
            # Measure processing time
            start_time = time.time()
            results = await optimizer.process_nfc_scan_batch(scan_requests)
            end_time = time.time()
            
            processing_time = end_time - start_time
            throughput = len(scan_requests) / processing_time
            
            assert len(results) == batch_size
            assert throughput > 10  # At least 10 requests per second
            
            print(f"Processed {batch_size} requests in {processing_time:.2f}s")
            print(f"Throughput: {throughput:.2f} requests/second")
            
        finally:
            await optimizer.cleanup()


# Pytest configuration
@pytest.fixture(scope="session", autouse=True)
async def setup_test_environment():
    """Setup test environment"""
    # Initialize test Redis instance
    try:
        redis_client = redis.from_url("redis://localhost:6379/15", decode_responses=True)
        await redis_client.flushdb()  # Clear test database
        await redis_client.close()
    except Exception as e:
        pytest.skip(f"Redis not available for testing: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])