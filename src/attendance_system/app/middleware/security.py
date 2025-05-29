"""
セキュリティミドルウェア

CORS、セキュリティヘッダー、ホスト検証などのセキュリティ関連ミドルウェアを提供
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)


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
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Trusted Hostミドルウェア（本番環境でのみ有効）
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.example.com", "localhost"],  # 本番環境で適切に設定
        )

    # セキュリティヘッダーミドルウェア
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """セキュリティヘッダーを追加"""
        try:
            response = await call_next(request)

            if settings.SECURITY_HEADERS_ENABLED:
                # XSS対策
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["X-XSS-Protection"] = "1; mode=block"

                # HTTPS強制（本番環境のみ）
                if settings.ENVIRONMENT == "production":
                    response.headers[
                        "Strict-Transport-Security"
                    ] = "max-age=31536000; includeSubDomains"

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
                response.headers[
                    "Permissions-Policy"
                ] = "geolocation=(), microphone=(), camera=()"

            return response

        except Exception as e:
            logger.error(f"Error in security headers middleware: {e}")
            return Response(content="Internal Server Error", status_code=500)

    # リクエストID追加ミドルウェア
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """リクエストIDをヘッダーに追加"""
        import uuid

        request_id = str(uuid.uuid4())

        # リクエストオブジェクトにIDを追加
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response

    logger.info("Security middleware configured successfully")
