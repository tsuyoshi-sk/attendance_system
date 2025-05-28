"""
WebSocketManager統合テスト
リアルタイムNFC通信のテスト
"""
import pytest
import asyncio
import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

# テスト用環境変数設定
os.environ["SECRET_KEY"] = "test-secret-key-64-characters-long-for-comprehensive-testing-extended-version"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-64-characters-long-for-comprehensive-testing-extended-version"
os.environ["IDM_HASH_SECRET"] = "test-idm-hash-secret-64-characters-long-for-comprehensive-testing-extended"
os.environ["ENVIRONMENT"] = "testing"

from src.attendance_system.websocket.websocket_manager import (
    WebSocketManager,
    WebSocketMessage,
    MessageType,
    ClientConnection
)
from src.attendance_system.security.security_manager import SecurityManager, SecurityContext

# WebSocketのモック
class MockWebSocket:
    def __init__(self):
        self.closed = False
        self.messages_sent = []
        self.messages_to_receive = []
        self.remote_address = ("127.0.0.1", 12345)
        self.request_headers = {"User-Agent": "test-client/1.0"}
    
    async def send(self, message):
        if not self.closed:
            self.messages_sent.append(message)
    
    async def close(self, code=1000, reason=""):
        self.closed = True
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.messages_to_receive:
            return self.messages_to_receive.pop(0)
        raise StopAsyncIteration

class TestWebSocketManager:
    """WebSocketManager テストクラス"""
    
    @pytest.fixture
    def security_manager(self):
        """SecurityManager インスタンス"""
        return SecurityManager()
    
    @pytest.fixture
    def websocket_manager(self, security_manager):
        """WebSocketManager インスタンス"""
        return WebSocketManager(security_manager)
    
    @pytest.fixture
    def mock_websocket(self):
        """モックWebSocket"""
        return MockWebSocket()
    
    @pytest.fixture
    def security_context(self):
        """SecurityContext インスタンス"""
        return SecurityContext(
            user_id="test_user",
            session_id="test_session",
            ip_address="127.0.0.1",
            user_agent="test-client/1.0",
            timestamp=datetime.utcnow(),
            permissions=["attendance.read", "attendance.write"]
        )
    
    # ===========================================
    # 接続管理テスト
    # ===========================================
    
    @pytest.mark.asyncio
    async def test_register_connection(self, websocket_manager, mock_websocket):
        """接続登録テスト"""
        await websocket_manager.register_connection(mock_websocket, "/ws")
        
        assert mock_websocket in websocket_manager.connections
        assert websocket_manager.stats['active_connections'] == 1
        assert websocket_manager.stats['total_connections'] == 1
        
        # 認証要求メッセージが送信されることを確認
        assert len(mock_websocket.messages_sent) == 1
        
        sent_message = json.loads(mock_websocket.messages_sent[0])
        assert sent_message['type'] == MessageType.AUTH_REQUIRED.value
    
    @pytest.mark.asyncio
    async def test_unregister_connection(self, websocket_manager, mock_websocket):
        """接続登録解除テスト"""
        # 接続登録
        await websocket_manager.register_connection(mock_websocket, "/ws")
        assert websocket_manager.stats['active_connections'] == 1
        
        # 接続解除
        await websocket_manager.unregister_connection(mock_websocket)
        assert mock_websocket not in websocket_manager.connections
        assert websocket_manager.stats['active_connections'] == 0
    
    @pytest.mark.asyncio
    async def test_connection_limit(self, websocket_manager):
        """接続数制限テスト"""
        # 最大接続数を一時的に2に設定
        original_limit = 1000
        websocket_manager.connections = {f"mock_{i}": None for i in range(1000)}
        
        mock_websocket = MockWebSocket()
        
        await websocket_manager.register_connection(mock_websocket, "/ws")
        
        # 接続が拒否されることを確認
        assert mock_websocket.closed
    
    # ===========================================
    # 認証テスト
    # ===========================================
    
    @pytest.mark.asyncio
    async def test_authenticate_connection_success(self, websocket_manager, mock_websocket, security_manager):
        """認証成功テスト"""
        # 接続登録
        await websocket_manager.register_connection(mock_websocket, "/ws")
        
        # セッション作成
        session_id = security_manager.create_session("test_user", "127.0.0.1", "test-client/1.0")
        
        # 認証メッセージ作成
        auth_message = WebSocketMessage(
            type=MessageType.SESSION_VALIDATE,
            payload={"session_id": session_id}
        )
        
        # 認証実行
        result = await websocket_manager.authenticate_connection(mock_websocket, auth_message)
        
        assert result is True
        
        connection = websocket_manager.connections[mock_websocket]
        assert connection.authenticated is True
        assert connection.user_id == "test_user"
        assert connection.session_id == session_id
    
    @pytest.mark.asyncio
    async def test_authenticate_connection_invalid_session(self, websocket_manager, mock_websocket):
        """無効セッション認証テスト"""
        # 接続登録
        await websocket_manager.register_connection(mock_websocket, "/ws")
        
        # 無効セッションで認証試行
        auth_message = WebSocketMessage(
            type=MessageType.SESSION_VALIDATE,
            payload={"session_id": "invalid_session"}
        )
        
        result = await websocket_manager.authenticate_connection(mock_websocket, auth_message)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_authenticate_connection_missing_session_id(self, websocket_manager, mock_websocket):
        """セッションID不足認証テスト"""
        # 接続登録
        await websocket_manager.register_connection(mock_websocket, "/ws")
        
        # セッションIDなしで認証試行
        auth_message = WebSocketMessage(
            type=MessageType.SESSION_VALIDATE,
            payload={}
        )
        
        result = await websocket_manager.authenticate_connection(mock_websocket, auth_message)
        
        assert result is False
    
    # ===========================================
    # NFC スキャンテスト
    # ===========================================
    
    @pytest.mark.asyncio
    async def test_handle_nfc_scan_success(self, websocket_manager, mock_websocket, security_manager):
        """NFC スキャン成功テスト"""
        # 接続登録と認証
        await websocket_manager.register_connection(mock_websocket, "/ws")
        session_id = security_manager.create_session("test_user", "127.0.0.1", "test-client/1.0")
        
        auth_message = WebSocketMessage(
            type=MessageType.SESSION_VALIDATE,
            payload={"session_id": session_id}
        )
        await websocket_manager.authenticate_connection(mock_websocket, auth_message)
        
        # NFC スキャンメッセージ
        nfc_message = WebSocketMessage(
            type=MessageType.NFC_SCAN,
            payload={
                "idm": "0123456789ABCDEF",
                "location": "office"
            }
        )
        
        # NFC スキャン処理
        await websocket_manager.handle_nfc_scan(mock_websocket, nfc_message)
        
        # レスポンス確認
        response_messages = [json.loads(msg) for msg in mock_websocket.messages_sent]
        attendance_responses = [msg for msg in response_messages if msg['type'] == MessageType.ATTENDANCE_RECORD.value]
        
        assert len(attendance_responses) == 1
        assert attendance_responses[0]['payload']['status'] == 'success'
        assert 'record_id' in attendance_responses[0]['payload']
        
        # 統計確認
        assert websocket_manager.stats['nfc_scans_processed'] == 1
        assert websocket_manager.stats['attendance_records_created'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_nfc_scan_unauthenticated(self, websocket_manager, mock_websocket):
        """未認証NFC スキャンテスト"""
        # 接続登録のみ（認証なし）
        await websocket_manager.register_connection(mock_websocket, "/ws")
        
        # NFC スキャンメッセージ
        nfc_message = WebSocketMessage(
            type=MessageType.NFC_SCAN,
            payload={"idm": "0123456789ABCDEF"}
        )
        
        # NFC スキャン処理
        await websocket_manager.handle_nfc_scan(mock_websocket, nfc_message)
        
        # エラーレスポンス確認
        response_messages = [json.loads(msg) for msg in mock_websocket.messages_sent]
        error_responses = [msg for msg in response_messages if msg['type'] == MessageType.ERROR.value]
        
        assert len(error_responses) > 0
        assert "Authentication required" in error_responses[-1]['payload']['error']
    
    @pytest.mark.asyncio
    async def test_handle_nfc_scan_missing_idm(self, websocket_manager, mock_websocket, security_manager):
        """IDM不足NFC スキャンテスト"""
        # 接続登録と認証
        await websocket_manager.register_connection(mock_websocket, "/ws")
        session_id = security_manager.create_session("test_user", "127.0.0.1", "test-client/1.0")
        
        auth_message = WebSocketMessage(
            type=MessageType.SESSION_VALIDATE,
            payload={"session_id": session_id}
        )
        await websocket_manager.authenticate_connection(mock_websocket, auth_message)
        
        # IDMなしのNFC スキャンメッセージ
        nfc_message = WebSocketMessage(
            type=MessageType.NFC_SCAN,
            payload={"location": "office"}
        )
        
        # NFC スキャン処理
        await websocket_manager.handle_nfc_scan(mock_websocket, nfc_message)
        
        # エラーレスポンス確認
        response_messages = [json.loads(msg) for msg in mock_websocket.messages_sent]
        error_responses = [msg for msg in response_messages if msg['type'] == MessageType.ERROR.value]
        
        assert len(error_responses) > 0
        assert "IDM required" in error_responses[-1]['payload']['error']
    
    # ===========================================
    # ハートビートテスト
    # ===========================================
    
    @pytest.mark.asyncio
    async def test_handle_heartbeat(self, websocket_manager, mock_websocket):
        """ハートビート処理テスト"""
        # 接続登録
        await websocket_manager.register_connection(mock_websocket, "/ws")
        
        # ハートビートメッセージ
        heartbeat_message = WebSocketMessage(
            type=MessageType.HEARTBEAT,
            payload={"ping": "ping"}
        )
        
        # ハートビート処理
        await websocket_manager.handle_heartbeat(mock_websocket, heartbeat_message)
        
        # ハートビート更新確認
        connection = websocket_manager.connections[mock_websocket]
        assert connection.last_heartbeat is not None
        
        # ハートビートレスポンス確認
        response_messages = [json.loads(msg) for msg in mock_websocket.messages_sent]
        heartbeat_responses = [msg for msg in response_messages if msg['type'] == MessageType.HEARTBEAT.value]
        
        assert len(heartbeat_responses) == 1
        assert heartbeat_responses[0]['payload']['status'] == 'alive'
    
    # ===========================================
    # メッセージ処理テスト
    # ===========================================
    
    def test_websocket_message_to_json(self):
        """WebSocketMessage JSON変換テスト"""
        message = WebSocketMessage(
            type=MessageType.NFC_SCAN,
            payload={"idm": "0123456789ABCDEF"},
            user_id="test_user"
        )
        
        json_str = message.to_json()
        parsed = json.loads(json_str)
        
        assert parsed['type'] == MessageType.NFC_SCAN.value
        assert parsed['payload']['idm'] == "0123456789ABCDEF"
        assert parsed['user_id'] == "test_user"
        assert 'timestamp' in parsed
    
    def test_websocket_message_from_json(self):
        """WebSocketMessage JSON解析テスト"""
        json_data = {
            "type": MessageType.NFC_SCAN.value,
            "payload": {"idm": "0123456789ABCDEF"},
            "user_id": "test_user",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        json_str = json.dumps(json_data)
        message = WebSocketMessage.from_json(json_str)
        
        assert message.type == MessageType.NFC_SCAN
        assert message.payload['idm'] == "0123456789ABCDEF"
        assert message.user_id == "test_user"
        assert isinstance(message.timestamp, datetime)
    
    # ===========================================
    # ブロードキャスト機能テスト
    # ===========================================
    
    @pytest.mark.asyncio
    async def test_broadcast_to_user(self, websocket_manager, security_manager):
        """ユーザーブロードキャストテスト"""
        # 複数の接続を作成
        mock_websockets = [MockWebSocket() for _ in range(3)]
        user_id = "test_user"
        
        # 接続登録と認証
        for ws in mock_websockets:
            await websocket_manager.register_connection(ws, "/ws")
            session_id = security_manager.create_session(user_id, "127.0.0.1", "test-client/1.0")
            
            auth_message = WebSocketMessage(
                type=MessageType.SESSION_VALIDATE,
                payload={"session_id": session_id}
            )
            await websocket_manager.authenticate_connection(ws, auth_message)
        
        # ブロードキャストメッセージ作成
        broadcast_message = WebSocketMessage(
            type=MessageType.SYSTEM_STATUS,
            payload={"message": "System update"}
        )
        
        # ブロードキャスト実行
        await websocket_manager.broadcast_to_user(user_id, broadcast_message)
        
        # 全ての接続にメッセージが送信されたことを確認
        for ws in mock_websockets:
            response_messages = [json.loads(msg) for msg in ws.messages_sent]
            system_messages = [msg for msg in response_messages if msg['type'] == MessageType.SYSTEM_STATUS.value]
            
            # 認証成功メッセージと合わせて2つのSYSTEM_STATUSメッセージがあることを確認
            # （認証成功は AUTH_SUCCESS なので、実際は1つのみ）
            system_broadcast_messages = [msg for msg in system_messages if msg['payload'].get('message') == 'System update']
            assert len(system_broadcast_messages) == 1
    
    # ===========================================
    # 統計情報テスト
    # ===========================================
    
    def test_get_stats(self, websocket_manager):
        """統計情報取得テスト"""
        stats = websocket_manager.get_stats()
        
        required_keys = [
            'total_connections', 'active_connections', 'messages_sent',
            'messages_received', 'nfc_scans_processed', 'attendance_records_created',
            'errors_handled', 'users_online', 'avg_connections_per_user', 'uptime'
        ]
        
        for key in required_keys:
            assert key in stats
        
        assert isinstance(stats['uptime'], str)
        assert stats['users_online'] >= 0
        assert stats['avg_connections_per_user'] >= 0

# ===========================================
# 統合テスト
# ===========================================

class TestWebSocketIntegration:
    """WebSocket統合テスト"""
    
    @pytest.mark.asyncio
    async def test_full_nfc_workflow(self):
        """完全なNFCワークフローテスト"""
        # セキュリティマネージャーとWebSocketマネージャー初期化
        security_manager = SecurityManager()
        websocket_manager = WebSocketManager(security_manager)
        
        mock_websocket = MockWebSocket()
        
        # 1. 接続登録
        await websocket_manager.register_connection(mock_websocket, "/ws")
        
        # 2. 認証
        session_id = security_manager.create_session("test_user", "127.0.0.1", "test-client/1.0")
        auth_message = WebSocketMessage(
            type=MessageType.SESSION_VALIDATE,
            payload={"session_id": session_id}
        )
        auth_result = await websocket_manager.authenticate_connection(mock_websocket, auth_message)
        assert auth_result is True
        
        # 3. NFC スキャン
        nfc_message = WebSocketMessage(
            type=MessageType.NFC_SCAN,
            payload={
                "idm": "0123456789ABCDEF",
                "location": "office"
            }
        )
        await websocket_manager.handle_nfc_scan(mock_websocket, nfc_message)
        
        # 4. レスポンス検証
        response_messages = [json.loads(msg) for msg in mock_websocket.messages_sent]
        
        # 認証要求、認証成功、出勤記録の3つのメッセージを確認
        message_types = [msg['type'] for msg in response_messages]
        assert MessageType.AUTH_REQUIRED.value in message_types
        assert MessageType.AUTH_SUCCESS.value in message_types
        assert MessageType.ATTENDANCE_RECORD.value in message_types
        
        # 5. 接続解除
        await websocket_manager.unregister_connection(mock_websocket)
        assert mock_websocket not in websocket_manager.connections

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/attendance_system/websocket"])