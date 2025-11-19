"""
認証・認可依存関数

FastAPIのDependsで使用する認証・認可チェック関数
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ..models.user import User
from config.config import settings

logger = logging.getLogger(__name__)

# HTTPBearer認証スキーム
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    現在のユーザーを取得
    
    Args:
        credentials: JWT認証情報
        db: データベースセッション
        
    Returns:
        認証されたユーザー
        
    Raises:
        HTTPException: 認証失敗時
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # JWTトークンをデコード
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # ユーザー名（sub）を取得
        username: str = payload.get("sub")
        if username is None:
            logger.warning("JWT payload missing 'sub' field")
            raise credentials_exception
            
        # トークン有効期限チェック
        from datetime import datetime
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.now():
            logger.warning(f"JWT token expired for user: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="トークンの有効期限が切れています",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception
    
    # データベースからユーザーを取得
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        logger.warning(f"User not found in database: {username}")
        raise credentials_exception
    
    # ユーザーがアクティブかチェック
    if not user.is_active:
        logger.warning(f"Inactive user attempted login: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="アカウントが無効化されています"
        )
    
    logger.info(f"User authenticated successfully: {username}")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    現在のアクティブユーザーを取得
    
    Args:
        current_user: 現在のユーザー
        
    Returns:
        アクティブなユーザー
        
    Raises:
        HTTPException: ユーザーが非アクティブの場合
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非アクティブなユーザーです"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    管理者権限を要求
    
    Args:
        current_user: 現在のユーザー
        
    Returns:
        管理者ユーザー
        
    Raises:
        HTTPException: 管理者権限がない場合
    """
    if not current_user.is_admin:
        logger.warning(f"Non-admin user attempted admin action: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です"
        )
    
    logger.info(f"Admin access granted: {current_user.username}")
    return current_user


async def require_manager(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    マネージャー権限を要求
    
    Args:
        current_user: 現在のユーザー
        
    Returns:
        マネージャー以上のユーザー
        
    Raises:
        HTTPException: マネージャー権限がない場合
    """
    if not (current_user.is_admin or current_user.is_manager):
        logger.warning(f"Non-manager user attempted manager action: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="マネージャー権限が必要です"
        )
    
    logger.info(f"Manager access granted: {current_user.username}")
    return current_user


async def require_employee_access(
    employee_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """
    従業員情報へのアクセス権限をチェック
    
    Args:
        employee_id: 従業員ID
        current_user: 現在のユーザー
        db: データベースセッション
        
    Returns:
        アクセス権限のあるユーザー
        
    Raises:
        HTTPException: アクセス権限がない場合
    """
    # 管理者とマネージャーは全従業員にアクセス可能
    if current_user.is_admin or current_user.is_manager:
        return current_user
    
    # 一般ユーザーは自分の従業員データのみアクセス可能
    if current_user.employee_id == employee_id:
        return current_user
    
    logger.warning(
        f"User {current_user.username} attempted unauthorized access to employee {employee_id}"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="この従業員情報にアクセスする権限がありません"
    )


def create_access_token(data: dict) -> str:
    """
    アクセストークンを作成
    
    Args:
        data: トークンに含めるデータ
        
    Returns:
        JWTトークン
    """
    from datetime import datetime, timedelta
    
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    パスワード検証
    
    Args:
        plain_password: 平文パスワード
        hashed_password: ハッシュ化パスワード
        
    Returns:
        パスワードが一致するかどうか
    """
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    パスワードをハッシュ化
    
    Args:
        password: 平文パスワード
        
    Returns:
        ハッシュ化されたパスワード
    """
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)