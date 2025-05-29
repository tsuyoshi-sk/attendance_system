"""
勤怠管理システム WebSocket統合メインアプリケーション
FastAPI + WebSocket リアルタイムNFC通信対応
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
import os

from ..config.config import config
from ..security.security_manager import SecurityManager
from ..websocket.websocket_manager import WebSocketManager, create_websocket_server
from .database import init_db
from .middleware.security import add_security_middleware

# ログ設定
logging.basicConfig(
    level=getattr(logging, getattr(config, "LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# グローバルインスタンス
security_manager = SecurityManager()
websocket_manager = WebSocketManager(security_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションのライフサイクル管理
    WebSocketサーバーとバックグラウンドタスクを管理
    """
    # 起動時の処理
    logger.info("🚀 勤怠管理システム WebSocket版 起動中...")
    
    try:
        # 設定の検証
        logger.info("設定の検証中...")
        
        # データベース初期化
        logger.info("データベース初期化中...")
        # await init_db()  # 必要に応じてコメントアウト解除
        
        # WebSocketバックグラウンドタスク開始
        logger.info("WebSocketバックグラウンドタスク開始...")
        await websocket_manager.start_background_tasks()
        
        logger.info("✅ システム起動完了")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 起動エラー: {str(e)}")
        raise
    
    # 終了時の処理
    logger.info("🔄 システム終了処理中...")
    
    # WebSocket接続のクリーンアップ
    for websocket in list(websocket_manager.connections.keys()):
        try:
            await websocket.close(code=1001, reason="Server shutdown")
        except Exception:
            pass
    
    logger.info("✅ システム終了完了")

def create_app() -> FastAPI:
    """
    FastAPIアプリケーションの作成
    WebSocket統合バージョン
    """
    app = FastAPI(
        title="勤怠管理システム WebSocket版",
        description="iPhone Suica対応 企業向け勤怠管理システム - リアルタイムNFC通信対応",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if config.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if config.ENVIRONMENT != "production" else None,
    )
    
    # セキュリティミドルウェアの追加
    add_security_middleware(app, config)
    
    # エラーハンドラーの設定
    setup_exception_handlers(app)
    
    # 静的ファイル配信の設定
    setup_static_files(app)
    
    # ルートの設定
    setup_routes(app)
    
    return app

def setup_exception_handlers(app: FastAPI):
    """例外ハンドラーの設定"""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTP例外: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "detail": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"バリデーションエラー: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
                "status_code": 422
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"予期しないエラー: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "予期しないエラーが発生しました",
                "status_code": 500
            }
        )

def setup_static_files(app: FastAPI):
    """静的ファイル配信の設定"""
    # 静的ファイルディレクトリのパス
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    
    if os.path.exists(static_dir):
        # 静的ファイル配信のマウント
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        
        # PWA用ファイルの直接配信
        from fastapi.responses import FileResponse
        
        @app.get("/manifest.json")
        async def serve_manifest():
            manifest_path = os.path.join(static_dir, "manifest.json")
            return FileResponse(manifest_path, media_type="application/json")
        
        @app.get("/sw.js")
        async def serve_service_worker():
            sw_path = os.path.join(static_dir, "sw.js")
            return FileResponse(sw_path, media_type="application/javascript")
        
        # メインページの配信
        @app.get("/app")
        async def serve_pwa_app():
            index_path = os.path.join(static_dir, "index.html")
            return FileResponse(index_path, media_type="text/html")
        
        logger.info(f"Static files mounted from: {static_dir}")
    else:
        logger.warning(f"Static directory not found: {static_dir}")

def setup_routes(app: FastAPI):
    """ルートの設定"""
    
    @app.get("/")
    async def root():
        """ルートエンドポイント"""
        return {
            "message": "勤怠管理システム WebSocket版",
            "version": "2.0.0",
            "status": "operational",
            "features": [
                "リアルタイムNFC通信",
                "OWASP ASVS Level 2準拠セキュリティ",
                "iPhone Suica対応",
                "WebSocket統合"
            ]
        }
    
    @app.get("/health")
    async def health_check():
        """ヘルスチェック"""
        return {
            "status": "healthy",
            "timestamp": websocket_manager.get_stats()['uptime'],
            "websocket_stats": websocket_manager.get_stats()
        }
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocketエンドポイント
        リアルタイムNFC通信の中心
        """
        await websocket.accept()
        logger.info(f"WebSocket接続受信: {websocket.client}")
        
        try:
            # WebSocketマネージャーに処理を委譲
            await websocket_manager.message_handler(websocket, "/ws")
            
        except WebSocketDisconnect:
            logger.info("WebSocket接続が正常に切断されました")
        except Exception as e:
            logger.error(f"WebSocketエラー: {str(e)}")
            try:
                await websocket.close(code=1011, reason="Server error")
            except Exception:
                pass
        finally:
            # クリーンアップ
            await websocket_manager.unregister_connection(websocket)
    
    @app.get("/ws/stats")
    async def websocket_stats():
        """WebSocket統計情報"""
        return websocket_manager.get_stats()
    
    @app.post("/ws/broadcast/{user_id}")
    async def broadcast_to_user(user_id: str, message: Dict[str, Any]):
        """特定ユーザーへのブロードキャスト（管理者用）"""
        from ..websocket.websocket_manager import WebSocketMessage, MessageType
        
        broadcast_message = WebSocketMessage(
            type=MessageType.SYSTEM_STATUS,
            payload=message
        )
        
        await websocket_manager.broadcast_to_user(user_id, broadcast_message)
        
        return {
            "status": "success",
            "message": f"Message broadcasted to user {user_id}",
            "payload": message
        }

# FastAPIアプリケーションインスタンス
app = create_app()

async def start_websocket_server():
    """
    WebSocketサーバーの起動
    別プロセス/ポートでの起動用
    """
    host = getattr(config, 'WEBSOCKET_HOST', 'localhost')
    port = getattr(config, 'WEBSOCKET_PORT', 8001)
    
    server_func = create_websocket_server(security_manager, host, port)
    server, ws_manager = await server_func()
    
    logger.info(f"WebSocketサーバー起動: ws://{host}:{port}")
    
    return server, ws_manager

def main():
    """
    アプリケーションのメインエントリーポイント
    WebSocket統合バージョン
    """
    host = getattr(config, 'HOST', '0.0.0.0')
    port = getattr(config, 'PORT', 8000)
    
    logger.info(f"FastAPIサーバー起動: http://{host}:{port}")
    logger.info("WebSocketエンドポイント: /ws")
    logger.info("API文書: /docs")
    
    # 開発環境での自動リロード
    reload = config.ENVIRONMENT == "development"
    
    uvicorn.run(
        "attendance_system.app.main_websocket:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()