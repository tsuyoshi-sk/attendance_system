"""
認証ミドルウェア

JWT認証とレート制限を提供するミドルウェア
"""

import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from jose import jwt, JWTError
import logging

from backend.app.database import SessionLocal
from backend.app.services.auth_service import AuthService
from config.config import config

logger = logging.getLogger(__name__)

# レート制限の設定
limiter = Limiter(key_func=get_remote_address)


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT認証ミドルウェア"""
    
    # 認証をスキップするパス
    SKIP_PATHS = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/info",
        "/api/v1/auth/login",
        "/api/v1/auth/init-admin",
        "/api/v1/punch",  # 打刻APIはカードIDmで認証するため除外
    ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        リクエストを処理
        
        Args:
            request: リクエスト
            call_next: 次のミドルウェア/エンドポイント
            
        Returns:
            Response: レスポンス
        """
        # 認証スキップパスの確認
        if self._should_skip_auth(request):
            return await call_next(request)
        
        # Authorizationヘッダーの取得
        authorization = request.headers.get("Authorization")
        if not authorization:
            return self._unauthorized_response("認証情報がありません")
        
        # トークンの抽出
        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            return self._unauthorized_response("無効な認証スキーム")
        
        if not token:
            return self._unauthorized_response("トークンがありません")
        
        # トークンの検証
        try:
            # JWTデコード
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
            
            # 有効期限チェック
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                return self._unauthorized_response("トークンの有効期限が切れています")
            
            # リクエストにユーザー情報を追加
            request.state.user_id = payload.get("sub")
            request.state.username = payload.get("username")
            request.state.role = payload.get("role")
            request.state.permissions = payload.get("permissions", [])
            
        except JWTError as e:
            logger.warning(f"JWT検証エラー: {str(e)}")
            return self._unauthorized_response("無効なトークンです")
        except Exception as e:
            logger.error(f"認証エラー: {str(e)}")
            return self._unauthorized_response("認証処理中にエラーが発生しました")
        
        # 次の処理へ
        return await call_next(request)
    
    def _should_skip_auth(self, request: Request) -> bool:
        """
        認証をスキップするかどうかを判定
        
        Args:
            request: リクエスト
            
        Returns:
            bool: スキップする場合True
        """
        path = request.url.path
        
        # 完全一致
        if path in self.SKIP_PATHS:
            return True
        
        # プレフィックス一致
        skip_prefixes = ["/docs", "/redoc", "/static"]
        for prefix in skip_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _unauthorized_response(self, detail: str) -> JSONResponse:
        """
        認証エラーレスポンスを生成
        
        Args:
            detail: エラー詳細
            
        Returns:
            JSONResponse: エラーレスポンス
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "message": detail,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """レート制限ミドルウェア"""
    
    # エンドポイント別のレート制限設定
    RATE_LIMITS = {
        "/api/v1/auth/login": "5/minute",  # ログイン: 1分間に5回まで
        "/api/v1/punch": "10/minute",  # 打刻: 1分間に10回まで
        "/api/v1/admin": "100/minute",  # 管理API: 1分間に100回まで
        "default": "300/minute",  # デフォルト: 1分間に300回まで
    }
    
    def __init__(self, app):
        super().__init__(app)
        self.limiters = {}
        
        # エンドポイント別のリミッターを作成
        for path, limit in self.RATE_LIMITS.items():
            self.limiters[path] = Limiter(
                key_func=self._get_identifier,
                default_limits=[limit]
            )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        リクエストを処理
        
        Args:
            request: リクエスト
            call_next: 次のミドルウェア/エンドポイント
            
        Returns:
            Response: レスポンス
        """
        # 適用するレート制限を決定
        limiter = self._get_limiter(request)
        
        try:
            # レート制限チェック
            limiter.check(request)
            
        except RateLimitExceeded as e:
            # レート制限超過
            logger.warning(
                f"レート制限超過: {self._get_identifier(request)} - {request.url.path}"
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "message": "リクエストが多すぎます。しばらく待ってから再試行してください。",
                        "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                        "retry_after": 60,  # 秒
                    }
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(e.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                }
            )
        
        # 次の処理へ
        response = await call_next(request)
        
        # レート制限情報をヘッダーに追加
        # TODO: 残りリクエスト数などの情報を追加
        
        return response
    
    def _get_limiter(self, request: Request):
        """
        リクエストに対応するリミッターを取得
        
        Args:
            request: リクエスト
            
        Returns:
            Limiter: レート制限オブジェクト
        """
        path = request.url.path
        
        # エンドポイント別の制限を確認
        for endpoint_path, limiter in self.limiters.items():
            if endpoint_path != "default" and path.startswith(endpoint_path):
                return limiter
        
        # デフォルト制限を返す
        return self.limiters.get("default")
    
    def _get_identifier(self, request: Request) -> str:
        """
        レート制限の識別子を取得
        
        Args:
            request: リクエスト
            
        Returns:
            str: 識別子（IPアドレスまたはユーザーID）
        """
        # 認証済みユーザーの場合はユーザーIDを使用
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # 未認証の場合はIPアドレスを使用
        return get_remote_address(request)