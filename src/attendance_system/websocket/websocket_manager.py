"""
WebSocketManager - リアルタイムNFC通信
iPhone Suica対応 企業向け勤怠管理システム
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
import weakref

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..security.security_manager import SecurityManager, SecurityContext
from ..config.config import config

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """WebSocketメッセージタイプ"""
    NFC_SCAN = "nfc_scan"
    ATTENDANCE_RECORD = "attendance_record"
    SESSION_VALIDATE = "session_validate"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    AUTH_REQUIRED = "auth_required"
    AUTH_SUCCESS = "auth_success"
    SYSTEM_STATUS = "system_status"

@dataclass
class WebSocketMessage:
    """WebSocketメッセージ構造"""
    type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_json(self) -> str:
        """JSON形式への変換"""
        data = asdict(self)
        data['type'] = self.type.value
        data['timestamp'] = self.timestamp.isoformat()
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        """JSON形式からの変換"""
        data = json.loads(json_str)
        data['type'] = MessageType(data['type'])
        if 'timestamp' in data:
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class ClientConnection:
    """クライアント接続情報"""
    websocket: WebSocketServerProtocol
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    authenticated: bool = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.utcnow()

class WebSocketManager:
    """
    WebSocket接続管理とリアルタイム通信
    セキュアなNFC通信とリアルタイム勤怠記録
    """
    
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.settings = config
        
        # 接続管理
        self.connections: Dict[WebSocketServerProtocol, ClientConnection] = {}
        self.user_connections: Dict[str, Set[WebSocketServerProtocol]] = {}
        
        # パフォーマンス統計
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'nfc_scans_processed': 0,
            'attendance_records_created': 0,
            'errors_handled': 0
        }
        
        # ハートビート設定
        self.heartbeat_interval = 30  # 30秒
        self.heartbeat_timeout = 60   # 60秒タイムアウト
        
        # セキュリティ設定
        self.max_connections_per_user = 3
        self.message_rate_limit = 100  # メッセージ/分
        
        logger.info("WebSocketManager initialized")
    
    async def register_connection(self, websocket: WebSocketServerProtocol, path: str):
        """新しい接続の登録"""
        try:
            # 接続情報の取得
            ip_address = websocket.remote_address[0] if websocket.remote_address else "unknown"
            user_agent = websocket.request_headers.get('User-Agent', 'unknown')
            
            # 接続制限チェック
            if len(self.connections) >= 1000:  # 最大接続数制限
                await websocket.close(code=1013, reason="Server overloaded")
                return
            
            # クライアント接続オブジェクト作成
            connection = ClientConnection(
                websocket=websocket,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.connections[websocket] = connection
            self.stats['total_connections'] += 1
            self.stats['active_connections'] += 1
            
            logger.info(f"New WebSocket connection from {ip_address}")
            
            # 認証要求送信
            auth_message = WebSocketMessage(
                type=MessageType.AUTH_REQUIRED,
                payload={"message": "Authentication required"}
            )
            await self.send_message(websocket, auth_message)
            
        except Exception as e:
            logger.error(f"Failed to register connection: {str(e)}")
            await websocket.close(code=1011, reason="Registration failed")
    
    async def unregister_connection(self, websocket: WebSocketServerProtocol):
        """接続の登録解除"""
        try:
            if websocket in self.connections:
                connection = self.connections[websocket]
                
                # ユーザー接続から削除
                if connection.user_id and connection.user_id in self.user_connections:
                    self.user_connections[connection.user_id].discard(websocket)
                    if not self.user_connections[connection.user_id]:
                        del self.user_connections[connection.user_id]
                
                # 接続リストから削除
                del self.connections[websocket]
                self.stats['active_connections'] -= 1
                
                logger.info(f"WebSocket connection unregistered for user {connection.user_id}")
                
        except Exception as e:
            logger.error(f"Failed to unregister connection: {str(e)}")
    
    async def authenticate_connection(self, websocket: WebSocketServerProtocol, message: WebSocketMessage):
        """接続の認証"""
        try:
            if websocket not in self.connections:
                return False
            
            connection = self.connections[websocket]
            payload = message.payload
            
            # セッション検証
            session_id = payload.get('session_id')
            if not session_id:
                await self.send_error(websocket, "Session ID required")
                return False
            
            # セキュリティマネージャーでセッション検証
            context = self.security_manager.validate_session(
                session_id,
                connection.ip_address,
                connection.user_agent
            )
            
            if not context:
                await self.send_error(websocket, "Invalid session")
                return False
            
            # 接続情報更新
            connection.user_id = context.user_id
            connection.session_id = session_id
            connection.authenticated = True
            
            # ユーザー接続リストに追加
            if context.user_id not in self.user_connections:
                self.user_connections[context.user_id] = set()
            
            # 接続数制限チェック
            if len(self.user_connections[context.user_id]) >= self.max_connections_per_user:
                await self.send_error(websocket, "Too many connections")
                return False
            
            self.user_connections[context.user_id].add(websocket)
            
            # 認証成功通知
            success_message = WebSocketMessage(
                type=MessageType.AUTH_SUCCESS,
                payload={
                    "user_id": context.user_id,
                    "permissions": context.permissions,
                    "timestamp": datetime.utcnow().isoformat()
                },
                session_id=session_id,
                user_id=context.user_id
            )
            await self.send_message(websocket, success_message)
            
            logger.info(f"WebSocket authentication successful for user {context.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            await self.send_error(websocket, "Authentication failed")
            return False
    
    async def handle_nfc_scan(self, websocket: WebSocketServerProtocol, message: WebSocketMessage):
        """NFC スキャン処理"""
        try:
            if websocket not in self.connections:
                return
            
            connection = self.connections[websocket]
            
            if not connection.authenticated:
                await self.send_error(websocket, "Authentication required")
                return
            
            payload = message.payload
            raw_idm = payload.get('idm')
            
            if not raw_idm:
                await self.send_error(websocket, "IDM required")
                return
            
            # レート制限チェック
            if not self.security_manager.check_rate_limit(
                f"nfc_{connection.user_id}",
                limit=10,  # 10回/分
                window_minutes=1
            ):
                await self.send_error(websocket, "Rate limit exceeded")
                return
            
            #セキュリティコンテキスト作成
            context = SecurityContext(
                user_id=connection.user_id,
                session_id=connection.session_id,
                ip_address=connection.ip_address,
                user_agent=connection.user_agent,
                timestamp=datetime.utcnow()
            )
            
            # IDMの安全なハッシュ化
            hashed_idm = self.security_manager.secure_nfc_idm(raw_idm, context)
            
            # 出勤記録処理（実装は別モジュール）
            attendance_record = await self.process_attendance_record(
                hashed_idm, 
                context,
                payload.get('location', 'office')
            )
            
            # 成功レスポンス
            response_message = WebSocketMessage(
                type=MessageType.ATTENDANCE_RECORD,
                payload={
                    "status": "success",
                    "record_id": attendance_record['id'],
                    "timestamp": attendance_record['timestamp'],
                    "type": attendance_record['type'],  # 'check_in' or 'check_out'
                    "location": attendance_record['location']
                },
                session_id=connection.session_id,
                user_id=connection.user_id
            )
            
            await self.send_message(websocket, response_message)
            
            # 統計更新
            self.stats['nfc_scans_processed'] += 1
            self.stats['attendance_records_created'] += 1
            
            # セキュリティログ
            self.security_manager.log_security_event(
                "nfc_scan_processed",
                context,
                {"record_id": attendance_record['id'], "location": attendance_record['location']}
            )
            
            logger.info(f"NFC scan processed for user {connection.user_id}")
            
        except Exception as e:
            logger.error(f"NFC scan handling failed: {str(e)}")
            await self.send_error(websocket, "NFC scan processing failed")
            self.stats['errors_handled'] += 1
    
    async def process_attendance_record(self, hashed_idm: str, context: SecurityContext, location: str) -> Dict:
        """出勤記録処理（モック実装）"""
        # 実際の実装では、データベースに記録を保存
        record = {
            'id': f"att_{datetime.utcnow().timestamp()}",
            'user_id': context.user_id,
            'idm_hash': hashed_idm,
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'check_in',  # 実際は前回の記録を確認して決定
            'location': location,
            'session_id': context.session_id
        }
        
        # ここでデータベース保存処理を実行
        # await self.attendance_repository.save_record(record)
        
        return record
    
    async def send_message(self, websocket: WebSocketServerProtocol, message: WebSocketMessage):
        """メッセージ送信"""
        try:
            if websocket.closed:
                return
            
            json_message = message.to_json()
            await websocket.send(json_message)
            self.stats['messages_sent'] += 1
            
        except ConnectionClosed:
            logger.debug("Connection closed during send")
        except WebSocketException as e:
            logger.error(f"WebSocket send error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected send error: {str(e)}")
    
    async def send_error(self, websocket: WebSocketServerProtocol, error_message: str):
        """エラーメッセージ送信"""
        error_msg = WebSocketMessage(
            type=MessageType.ERROR,
            payload={"error": error_message}
        )
        await self.send_message(websocket, error_msg)
    
    async def broadcast_to_user(self, user_id: str, message: WebSocketMessage):
        """特定ユーザーの全接続にブロードキャスト"""
        if user_id not in self.user_connections:
            return
        
        connections = list(self.user_connections[user_id])
        for websocket in connections:
            await self.send_message(websocket, message)
    
    async def broadcast_system_status(self):
        """システム状態のブロードキャスト"""
        status_message = WebSocketMessage(
            type=MessageType.SYSTEM_STATUS,
            payload={
                "active_connections": self.stats['active_connections'],
                "system_time": datetime.utcnow().isoformat(),
                "status": "operational"
            }
        )
        
        for websocket in list(self.connections.keys()):
            if self.connections[websocket].authenticated:
                await self.send_message(websocket, status_message)
    
    async def handle_heartbeat(self, websocket: WebSocketServerProtocol, message: WebSocketMessage):
        """ハートビート処理"""
        if websocket in self.connections:
            connection = self.connections[websocket]
            connection.last_heartbeat = datetime.utcnow()
            
            # ハートビート応答
            heartbeat_response = WebSocketMessage(
                type=MessageType.HEARTBEAT,
                payload={"status": "alive", "server_time": datetime.utcnow().isoformat()}
            )
            await self.send_message(websocket, heartbeat_response)
    
    async def cleanup_stale_connections(self):
        """古い接続のクリーンアップ"""
        current_time = datetime.utcnow()
        stale_connections = []
        
        for websocket, connection in self.connections.items():
            if connection.last_heartbeat:
                time_diff = (current_time - connection.last_heartbeat).total_seconds()
                if time_diff > self.heartbeat_timeout:
                    stale_connections.append(websocket)
        
        for websocket in stale_connections:
            logger.info("Closing stale connection")
            await websocket.close(code=1000, reason="Heartbeat timeout")
            await self.unregister_connection(websocket)
    
    async def message_handler(self, websocket: WebSocketServerProtocol, path: str):
        """WebSocketメッセージハンドラー"""
        await self.register_connection(websocket, path)
        
        try:
            async for raw_message in websocket:
                try:
                    message = WebSocketMessage.from_json(raw_message)
                    self.stats['messages_received'] += 1
                    
                    # メッセージタイプによる処理分岐
                    if message.type == MessageType.SESSION_VALIDATE:
                        await self.authenticate_connection(websocket, message)
                    
                    elif message.type == MessageType.NFC_SCAN:
                        await self.handle_nfc_scan(websocket, message)
                    
                    elif message.type == MessageType.HEARTBEAT:
                        await self.handle_heartbeat(websocket, message)
                    
                    else:
                        await self.send_error(websocket, "Unknown message type")
                
                except json.JSONDecodeError:
                    await self.send_error(websocket, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"Message processing error: {str(e)}")
                    await self.send_error(websocket, "Message processing failed")
                    self.stats['errors_handled'] += 1
        
        except ConnectionClosed:
            logger.debug("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket handler error: {str(e)}")
        finally:
            await self.unregister_connection(websocket)
    
    async def start_background_tasks(self):
        """バックグラウンドタスクの開始"""
        # 定期クリーンアップタスク
        asyncio.create_task(self._periodic_cleanup())
        
        # システム状態ブロードキャストタスク
        asyncio.create_task(self._periodic_status_broadcast())
        
        logger.info("Background tasks started")
    
    async def _periodic_cleanup(self):
        """定期クリーンアップタスク"""
        while True:
            try:
                await asyncio.sleep(60)  # 1分間隔
                await self.cleanup_stale_connections()
            except Exception as e:
                logger.error(f"Periodic cleanup error: {str(e)}")
    
    async def _periodic_status_broadcast(self):
        """定期状態ブロードキャストタスク"""
        while True:
            try:
                await asyncio.sleep(300)  # 5分間隔
                await self.broadcast_system_status()
            except Exception as e:
                logger.error(f"Status broadcast error: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報の取得"""
        return {
            **self.stats,
            'users_online': len(self.user_connections),
            'avg_connections_per_user': (
                self.stats['active_connections'] / max(len(self.user_connections), 1)
            ),
            'uptime': datetime.utcnow().isoformat()
        }

# WebSocketサーバー起動用のファクトリ関数
def create_websocket_server(security_manager: SecurityManager, host: str = "localhost", port: int = 8001):
    """WebSocketサーバーの作成"""
    ws_manager = WebSocketManager(security_manager)
    
    async def server_with_background_tasks():
        # バックグラウンドタスク開始
        await ws_manager.start_background_tasks()
        
        # WebSocketサーバー起動
        server = await websockets.serve(
            ws_manager.message_handler,
            host,
            port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        )
        
        logger.info(f"WebSocket server started on ws://{host}:{port}")
        return server, ws_manager
    
    return server_with_background_tasks

# グローバルインスタンス管理
_websocket_managers: Dict[str, WebSocketManager] = {}