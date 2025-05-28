"""
認証ミドルウェア

JWTトークンベースの認証を処理します。
"""

import logging
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import jwt
from datetime import datetime

from config.config import settings
from backend.app.utils.unified_logging import log_security_event

logger = logging.getLogger(__name__)

# 認証が不要なパス
EXEMPT_PATHS = [
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
]


class JWTBearer(HTTPBearer):
    """JWT Bearer認証スキーム"""
    
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[str]:
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme."
                )
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid token or expired token."
                )
            return credentials.credentials
        return None
    
    def verify_jwt(self, token: str) -> bool:
        """JWTトークンを検証"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # 有効期限チェック
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                return False
            
            return True
        except jwt.InvalidTokenError:
            return False


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """認証ミドルウェア"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # 認証不要なパスをチェック
        path = request.url.path
        if any(path.startswith(exempt) for exempt in EXEMPT_PATHS):
            return await call_next(request)
        
        # 開発環境で認証無効化オプションがある場合
        if settings.DEBUG and getattr(settings, 'DISABLE_AUTH', False):
            return await call_next(request)
        
        # Authorizationヘッダーの取得
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            log_security_event(
                event_type="auth_missing",
                success=False,
                ip_address=request.client.host if request.client else None,
                details={"path": path}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # トークンの抽出と検証
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # 有効期限チェック
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise jwt.ExpiredSignatureError("Token has expired")
            
            # リクエストにユーザー情報を追加
            request.state.user_id = payload.get("sub")
            request.state.user_role = payload.get("role", "user")
            request.state.token_payload = payload
            
            log_security_event(
                event_type="auth_success",
                success=True,
                user_id=request.state.user_id,
                ip_address=request.client.host if request.client else None,
                details={"path": path}
            )
            
        except jwt.ExpiredSignatureError:
            log_security_event(
                event_type="auth_expired",
                success=False,
                ip_address=request.client.host if request.client else None,
                details={"path": path}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            log_security_event(
                event_type="auth_invalid",
                success=False,
                ip_address=request.client.host if request.client else None,
                details={"path": path, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # リクエストを処理
        response = await call_next(request)
        return response


def get_current_user(request: Request) -> Tuple[Optional[str], Optional[str]]:
    """現在のユーザー情報を取得"""
    user_id = getattr(request.state, 'user_id', None)
    user_role = getattr(request.state, 'user_role', None)
    return user_id, user_role


def require_role(required_role: str):
    """特定のロールを要求するデコレーター"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user_id, user_role = get_current_user(request)
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # ロール階層: admin > manager > user
            role_hierarchy = {"user": 1, "manager": 2, "admin": 3}
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
                log_security_event(
                    event_type="authorization_failed",
                    success=False,
                    user_id=user_id,
                    details={
                        "required_role": required_role,
                        "user_role": user_role
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required role: {required_role}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# JWT Bearer インスタンス
jwt_bearer = JWTBearer()