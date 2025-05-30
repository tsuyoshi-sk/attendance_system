"""
非同期対応セキュリティミドルウェア

CORS、セキュリティヘッダー、ホスト検証などのセキュリティ関連ミドルウェアを提供
"""

import uuid
import logging
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """セキュリティヘッダーを追加するミドルウェア"""
    
    def __init__(self, app, settings):
        super().__init__(app)
        self.settings = settings
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """リクエストを処理しセキュリティヘッダーを追加"""
        try:
            # リクエストIDを生成して追加
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id
            
            # レスポンスを取得
            response = await call_next(request)
            
            # リクエストIDヘッダーを追加
            response.headers["X-Request-ID"] = request_id
            
            # セキュリティヘッダーが有効な場合
            if self.settings.SECURITY_HEADERS_ENABLED:
                # XSS対策
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["X-XSS-Protection"] = "1; mode=block"
                
                # HTTPS強制（本番環境のみ）
                if self.settings.ENVIRONMENT == "production":
                    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                
                # コンテンツセキュリティポリシー
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "img-src 'self' data: https:; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "font-src 'self' data:; "
                    "connect-src 'self' wss: https:;"
                )
                
                # その他のセキュリティヘッダー
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in security headers middleware: {e}")
            return StarletteResponse(
                content="Internal Server Error",
                status_code=500,
                headers={"X-Request-ID": getattr(request.state, 'request_id', 'unknown')}
            )


def add_security_middleware(app: FastAPI, settings):
    """
    セキュリティミドルウェアをアプリケーションに追加
    
    Args:
        app: FastAPIアプリケーション
        settings: アプリケーション設定
    """
    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Trusted Hostミドルウェア（本番環境でのみ有効）
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.example.com", "localhost"]  # 本番環境で適切に設定
        )
    
    # セキュリティヘッダーミドルウェア（BaseHTTPMiddleware派生）
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    
    logger.info("Security middleware configured successfully")