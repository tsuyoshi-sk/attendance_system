"""
SecurityManager の包括的テスト
OWASP ASVS Level 2 要件検証
"""
import pytest
import asyncio
import os
import json
from unittest.mock import patch, Mock, AsyncMock
import secrets

# テスト用環境変数設定
os.environ[
    "SECRET_KEY"
] = "test-secret-key-64-characters-long-for-comprehensive-testing-ok"
os.environ[
    "JWT_SECRET_KEY"
] = "test-jwt-secret-64-characters-long-for-comprehensive-testing-ok"
os.environ[
    "IDM_HASH_SECRET"
] = "test-idm-hash-secret-64-characters-long-for-testing-purposes"

from backend.app.security.enhanced_auth import (
    SecurityManager,
    TokenManager,
    IntrusionDetector,
    SecurityAuditor,
)


class TestSecurityManager:
    """SecurityManager のテストクラス"""

    @pytest.fixture
    async def security_manager(self):
        """SecurityManager インスタンス"""
        # Redisをモックして初期化
        with patch("redis.asyncio.Redis") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.from_url.return_value = mock_redis_instance

            sm = SecurityManager(redis_url="redis://localhost:6379")
            await sm.initialize()
            return sm

    @pytest.mark.asyncio
    async def test_initialization_success(self):
        """正常な初期化テスト"""
        with patch("redis.asyncio.Redis") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.from_url.return_value = mock_redis_instance

            sm = SecurityManager()
            await sm.initialize()

            assert sm is not None
            assert hasattr(sm, "token_manager")
            assert hasattr(sm, "intrusion_detector")
            assert hasattr(sm, "security_auditor")
            assert hasattr(sm, "validator")

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_card_data(self, security_manager):
        """カードデータ暗号化・復号化テスト"""
        test_card_data = {
            "card_id": "0123456789ABCDEF",
            "scan_time": "2023-12-01T10:00:00Z",
            "location": "entrance",
        }

        # 暗号化
        encrypted = security_manager.encrypt_card_data(test_card_data)
        assert encrypted is not None
        assert isinstance(encrypted, str)
        assert encrypted != json.dumps(test_card_data)

        # 復号化
        decrypted = security_manager.decrypt_card_data(encrypted)
        assert decrypted == test_card_data

    @pytest.mark.asyncio
    async def test_validate_nfc_request_valid(self, security_manager):
        """正常なNFC要求の検証テスト"""
        valid_request = {
            "card_id": "0123456789ABCDEF",
            "timestamp": "2023-12-01T10:00:00Z",
            "reader_id": "reader_001",
        }
        client_id = "test_client_001"

        # モックで正常な検証を設定
        with patch.object(
            security_manager.intrusion_detector, "is_client_blocked", return_value=False
        ), patch.object(
            security_manager.validator, "validate_nfc_scan_request", return_value=True
        ), patch.object(
            security_manager.intrusion_detector,
            "detect_suspicious_activity",
            return_value=[],
        ), patch.object(
            security_manager.intrusion_detector, "track_request", return_value=None
        ):
            result = await security_manager.validate_nfc_request(
                valid_request, client_id
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_nfc_request_blocked_client(self, security_manager):
        """ブロックされたクライアントのNFC要求テスト"""
        valid_request = {
            "card_id": "0123456789ABCDEF",
            "timestamp": "2023-12-01T10:00:00Z",
            "reader_id": "reader_001",
        }
        client_id = "blocked_client_001"

        # クライアントをブロック状態に設定
        with patch.object(
            security_manager.intrusion_detector, "is_client_blocked", return_value=True
        ):
            result = await security_manager.validate_nfc_request(
                valid_request, client_id
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_validate_nfc_request_invalid_data(self, security_manager):
        """無効なNFC要求データのテスト"""
        invalid_request = {"invalid_field": "invalid_value"}
        client_id = "test_client_001"

        with patch.object(
            security_manager.intrusion_detector, "is_client_blocked", return_value=False
        ), patch.object(
            security_manager.validator, "validate_nfc_scan_request", return_value=False
        ), patch.object(
            security_manager.intrusion_detector, "track_request", return_value=None
        ):
            result = await security_manager.validate_nfc_request(
                invalid_request, client_id
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_websocket_success(self, security_manager):
        """WebSocket認証成功テスト"""
        token = "valid_jwt_token"
        client_id = "test_client_001"
        expected_payload = {"user_id": "user_123", "exp": 1234567890}

        with patch.object(
            security_manager.token_manager,
            "validate_websocket_token",
            return_value=expected_payload,
        ), patch.object(
            security_manager.intrusion_detector, "is_client_blocked", return_value=False
        ), patch.object(
            security_manager.intrusion_detector, "track_request", return_value=None
        ), patch.object(
            security_manager.security_auditor,
            "log_authentication_event",
            return_value=None,
        ):
            result = await security_manager.authenticate_websocket(token, client_id)
            assert result == expected_payload

    @pytest.mark.asyncio
    async def test_authenticate_websocket_blocked_client(self, security_manager):
        """ブロックされたクライアントのWebSocket認証テスト"""
        token = "valid_jwt_token"
        client_id = "blocked_client_001"

        with patch.object(
            security_manager.token_manager,
            "validate_websocket_token",
            return_value={"user_id": "user_123"},
        ), patch.object(
            security_manager.intrusion_detector, "is_client_blocked", return_value=True
        ):
            with pytest.raises(Exception):  # HTTPException or similar
                await security_manager.authenticate_websocket(token, client_id)

    @pytest.mark.asyncio
    async def test_get_security_status(self, security_manager):
        """セキュリティステータス取得テスト"""
        mock_events = [
            {"timestamp": "2023-12-01T10:00:00Z", "event": "login_attempt"},
            {"timestamp": "2023-12-01T10:01:00Z", "event": "failed_login"},
        ]

        with patch.object(
            security_manager.security_auditor,
            "get_audit_trail",
            return_value=mock_events,
        ), patch.object(
            security_manager.intrusion_detector, "redis_client"
        ) as mock_redis:
            mock_redis.keys.return_value = ["blocked:client1", "blocked:client2"]

            status = await security_manager.get_security_status()

            assert "recent_events" in status
            assert "blocked_clients" in status
            assert status["blocked_clients"] == 2


@pytest.mark.integration
class TestSecurityManagerIntegration:
    """統合テストクラス"""

    @pytest.mark.asyncio
    async def test_full_nfc_workflow(self):
        """完全なNFCワークフローテスト"""
        with patch("redis.asyncio.Redis") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.from_url.return_value = mock_redis_instance

            sm = SecurityManager()
            await sm.initialize()

            # iPhone Suica IDMのシミュレーション
            iphone_idms = ["0123456789ABCDEF", "FEDCBA9876543210", "1111222233334444"]

            for idm in iphone_idms:
                card_data = {
                    "card_id": idm,
                    "scan_time": "2023-12-01T10:00:00Z",
                    "location": "entrance",
                }

                # 暗号化・復号化テスト
                encrypted = sm.encrypt_card_data(card_data)
                decrypted = sm.decrypt_card_data(encrypted)
                assert decrypted == card_data

                # NFC要求検証テスト
                with patch.object(
                    sm.intrusion_detector, "is_client_blocked", return_value=False
                ), patch.object(
                    sm.validator, "validate_nfc_scan_request", return_value=True
                ), patch.object(
                    sm.intrusion_detector, "detect_suspicious_activity", return_value=[]
                ), patch.object(
                    sm.intrusion_detector, "track_request", return_value=None
                ):
                    result = await sm.validate_nfc_request(card_data, f"client_{idm}")
                    assert result is True

    @pytest.mark.asyncio
    async def test_performance_benchmark(self):
        """パフォーマンステスト"""
        import time

        with patch("redis.asyncio.Redis") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.from_url.return_value = mock_redis_instance

            sm = SecurityManager()
            await sm.initialize()

            test_data = {"card_id": "0123456789ABCDEF", "data": "test"}

            # 暗号化パフォーマンス
            start_time = time.time()
            for _ in range(100):
                encrypted = sm.encrypt_card_data(test_data)
                sm.decrypt_card_data(encrypted)
            crypto_time = time.time() - start_time

            # パフォーマンス要件（100回で1秒以内）
            assert crypto_time < 1.0, f"Crypto performance too slow: {crypto_time}s"

            print(f"Crypto performance: {crypto_time:.3f}s for 100 operations")
