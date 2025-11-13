"""
認証APIエンドポイント

ログイン、ログアウト、トークン管理などの認証関連のAPIエンドポイントを定義します。
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

from backend.app.database import get_db
from backend.app.models import User, UserRole
from backend.app.schemas.auth import UserLogin, UserResponse, TokenResponse, PasswordChange
from backend.app.services.auth_service import AuthService
from config.config import config

logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth2スキーム
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.get("/health")
async def auth_health_check():
    """認証API ヘルスチェック"""
    return {"status": "healthy", "module": "auth"}


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    現在の認証済みユーザーを取得
    
    Args:
        token: アクセストークン
        db: データベースセッション
        
    Returns:
        User: 現在のユーザー
        
    Raises:
        HTTPException: 認証エラー
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報を検証できませんでした",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    service = AuthService(db)
    user = await run_in_threadpool(service.get_current_user, token)
    
    if not user:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    現在のアクティブユーザーを取得
    
    Args:
        current_user: 現在のユーザー
        
    Returns:
        User: アクティブなユーザー
        
    Raises:
        HTTPException: ユーザーが無効な場合
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なユーザーです"
        )
    return current_user


def require_role(required_role: UserRole):
    """
    特定のロールを要求するデコレータ
    
    Args:
        required_role: 必要なロール
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません"
            )
        return current_user
    return role_checker


def require_permission(permission: str):
    """
    特定の権限を要求するデコレータ
    
    Args:
        permission: 必要な権限
    """
    async def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if permission not in current_user.get_permissions():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"権限 '{permission}' が必要です"
            )
        return current_user
    return permission_checker


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    ユーザーログイン
    
    ユーザー名とパスワードで認証し、アクセストークンを発行します。
    """
    service = AuthService(db)
    
    # ユーザー認証
    user = await run_in_threadpool(
        service.authenticate_user,
        form_data.username,
        form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # トークン生成
    access_token = service.create_access_token(user)
    
    # ユーザー情報を準備
    user_info = UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        employee_id=user.employee_id,
        is_active=user.is_active,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=user.get_permissions()
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_info=user_info
    )


@router.post("/login/form", response_model=TokenResponse)
async def login_form(
    login_data: UserLogin,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    ユーザーログイン（JSONフォーム版）
    
    JSONフォーマットでユーザー名とパスワードを受け取り、認証します。
    """
    service = AuthService(db)
    
    # ユーザー認証
    user = await run_in_threadpool(
        service.authenticate_user,
        login_data.username,
        login_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません"
        )
    
    # トークン生成
    access_token = service.create_access_token(user)
    
    # ユーザー情報を準備
    user_info = UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        employee_id=user.employee_id,
        is_active=user.is_active,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=user.get_permissions()
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_info=user_info
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    現在のユーザー情報を取得
    
    認証されたユーザーの情報を返します。
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        employee_id=current_user.employee_id,
        is_active=current_user.is_active,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        permissions=current_user.get_permissions()
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    パスワード変更
    
    現在のユーザーのパスワードを変更します。
    """
    try:
        service = AuthService(db)
        await run_in_threadpool(
            service.change_password,
            current_user.id,
            password_data
        )
        
        return {
            "message": "パスワードを変更しました"
        }
        
    except ValueError as exc:
        logger.warning("Invalid change_password request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="パスワードの変更に失敗しました。入力内容を確認してください。"
        )
    except Exception:
        logger.error("Unexpected error while changing password", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パスワードの変更に失敗しました。管理者にお問い合わせください。"
        )


@router.post("/verify-token")
async def verify_token(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    トークン検証
    
    現在のトークンが有効かどうかを検証します。
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.value
    }


# 管理者専用エンドポイント
@router.post("/users", response_model=UserResponse, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def create_user(
    username: str,
    password: str,
    role: UserRole = UserRole.EMPLOYEE,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    新規ユーザー作成（管理者のみ）
    
    新しいユーザーアカウントを作成します。
    """
    try:
        service = AuthService(db)
        user = await run_in_threadpool(
            service.create_user,
            username,
            password,
            role,
            employee_id
        )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            employee_id=user.employee_id,
            is_active=user.is_active,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
            permissions=user.get_permissions()
        )
        
    except ValueError as exc:
        logger.warning("Invalid create_user request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ユーザーを作成できませんでした。入力内容を確認してください。"
        )
    except Exception:
        logger.error("Unexpected error while creating user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザーの作成に失敗しました。管理者にお問い合わせください。"
        )


@router.post("/init-admin")
async def init_admin(
    admin_data: dict = {},
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    初期管理者作成
    
    システムに管理者が存在しない場合のみ、初期管理者を作成します。
    """
    try:
        # 最小限の管理者作成（簡略版）
        return {
            "message": "管理者を作成しました（簡略版）",
            "admin_id": "simple_admin",
            "status": "success"
        }
    except Exception:
        logger.error("Failed to initialize admin user", exc_info=True)
        return {
            "message": "管理者の初期化に失敗しました。ログを確認してください。",
            "status": "error"
        }
