"""
認証サービス

ユーザー認証、トークン管理、パスワード管理などの認証機能を提供
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from jose import JWTError, jwt
import logging
import uuid

from backend.app.models import User, Employee, UserRole
from backend.app.schemas.auth import UserLogin, PasswordChange, TokenPayload
from config.config import config

logger = logging.getLogger(__name__)

# パスワードハッシュ化の設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """認証サービスクラス"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        ユーザー認証
        
        Args:
            username: ユーザー名
            password: パスワード
            
        Returns:
            User: 認証成功時のユーザー情報、失敗時はNone
        """
        user = self.db.query(User).filter(
            User.username == username,
            User.is_active == True
        ).first()
        
        if not user:
            logger.warning(f"認証失敗: ユーザー '{username}' が見つかりません")
            return None
        
        if not self.verify_password(password, user.password_hash):
            logger.warning(f"認証失敗: パスワードが一致しません (user: {username})")
            return None
        
        # 最終ログイン時刻を更新
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"認証成功: {username}")
        return user
    
    def create_user(
        self,
        username: str,
        password: str,
        role: UserRole = UserRole.EMPLOYEE,
        employee_id: Optional[int] = None
    ) -> User:
        """
        新規ユーザーを作成
        
        Args:
            username: ユーザー名
            password: パスワード
            role: ユーザーロール
            employee_id: 従業員ID（従業員アカウントの場合）
            
        Returns:
            User: 作成されたユーザー
            
        Raises:
            ValueError: バリデーションエラー
        """
        # ユーザー名の重複チェック
        existing = self.db.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError(f"ユーザー名 '{username}' は既に使用されています")
        
        # 従業員との関連をチェック
        if employee_id:
            employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                raise ValueError(f"従業員ID {employee_id} が見つかりません")
            
            # 既にユーザーアカウントがあるかチェック
            existing_user = self.db.query(User).filter(User.employee_id == employee_id).first()
            if existing_user:
                raise ValueError(f"従業員ID {employee_id} には既にユーザーアカウントが存在します")
        
        # パスワードをハッシュ化
        password_hash = self.get_password_hash(password)
        
        # ユーザーを作成
        try:
            user = User(
                username=username,
                password_hash=password_hash,
                role=role,
                employee_id=employee_id
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"ユーザーを作成しました: {username} (role: {role.value})")
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"ユーザー作成エラー: {str(e)}")
            raise ValueError("ユーザーの作成に失敗しました")
    
    def change_password(self, user_id: int, password_data: PasswordChange) -> bool:
        """
        パスワードを変更
        
        Args:
            user_id: ユーザーID
            password_data: パスワード変更データ
            
        Returns:
            bool: 変更成功フラグ
            
        Raises:
            ValueError: エラー
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("ユーザーが見つかりません")
        
        # 現在のパスワードを確認
        if not self.verify_password(password_data.current_password, user.password_hash):
            raise ValueError("現在のパスワードが正しくありません")
        
        # 新しいパスワードをハッシュ化
        new_password_hash = self.get_password_hash(password_data.new_password)
        
        # パスワードを更新
        user.password_hash = new_password_hash
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"パスワードを変更しました: user_id={user_id}")
        return True
    
    def create_access_token(self, user: User) -> str:
        """
        アクセストークンを生成

        Args:
            user: ユーザー情報

        Returns:
            str: JWTトークン
        """
        # トークンの有効期限
        expire = datetime.utcnow() + timedelta(minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        # トークンペイロード
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),  # セッション固定攻撃対策: ユニークなトークンID
            "permissions": user.get_permissions()
        }

        # トークンを生成
        token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
        return token
    
    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """
        トークンを検証
        
        Args:
            token: JWTトークン
            
        Returns:
            TokenPayload: トークンペイロード、無効な場合はNone
        """
        try:
            payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
            return TokenPayload(**payload)
        except JWTError as e:
            logger.warning(f"トークン検証エラー: {str(e)}")
            return None
    
    def get_current_user(self, token: str) -> Optional[User]:
        """
        トークンから現在のユーザーを取得
        
        Args:
            token: JWTトークン
            
        Returns:
            User: ユーザー情報、無効な場合はNone
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user = self.db.query(User).filter(
            User.id == int(payload.sub),
            User.is_active == True
        ).first()
        
        return user
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        パスワードを検証
        
        Args:
            plain_password: 平文パスワード
            hashed_password: ハッシュ化されたパスワード
            
        Returns:
            bool: 一致するかどうか
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """
        パスワードをハッシュ化
        
        Args:
            password: 平文パスワード
            
        Returns:
            str: ハッシュ化されたパスワード
        """
        return pwd_context.hash(password)
    
    def create_initial_admin(self) -> Optional[User]:
        """
        初期管理者アカウントを作成
        
        Returns:
            User: 作成された管理者ユーザー
        """
        # 既に管理者が存在するかチェック
        admin_exists = self.db.query(User).filter(User.role == UserRole.ADMIN).first()
        if admin_exists:
            logger.info("管理者アカウントは既に存在します")
            return None
        
        try:
            # デフォルト管理者を作成
            admin = self.create_user(
                username="admin",
                password="admin123!",  # 初期パスワード（本番環境では変更必須）
                role=UserRole.ADMIN
            )
            
            logger.warning("初期管理者アカウントを作成しました。パスワードを変更してください！")
            return admin
            
        except Exception as e:
            logger.error(f"初期管理者作成エラー: {str(e)}")
            return None
