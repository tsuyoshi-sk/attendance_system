"""
テスト管理者ユーザー作成スクリプト

開発用の管理者アカウント (username: test_admin / password: test123) を
データベースに作成します。既に存在する場合は何もしません。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Tuple


# プロジェクトルートを Python パスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.app.database import SessionLocal  # noqa: E402
from backend.app.models import User, UserRole  # noqa: E402
from backend.app.services.auth_service import AuthService  # noqa: E402


USERNAME = "test_admin"
PASSWORD = "test123"


def ensure_test_admin() -> Tuple[User, bool]:
    """
    テスト管理者ユーザーを作成（存在すれば再利用）

    Returns:
        (user, created): ユーザーオブジェクトと新規作成フラグ
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == USERNAME).first()
        if user:
            return user, False

        service = AuthService(db)
        user = service.create_user(
            username=USERNAME,
            password=PASSWORD,
            role=UserRole.ADMIN
        )
        return user, True
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        user, created = ensure_test_admin()
        if created:
            logging.info(
                "Created admin user '%s' (id=%s)",
                user.username,
                getattr(user, "id", "?"),
            )
            print(f"Admin user '{user.username}' was created (id={user.id}).")
        else:
            logging.info(
                "Admin user '%s' already exists (id=%s)",
                user.username,
                getattr(user, "id", "?"),
            )
            print(f"Admin user '{user.username}' already exists (id={user.id}).")
    except Exception:
        logging.exception("Failed to ensure test admin user")
        raise


if __name__ == "__main__":
    main()
