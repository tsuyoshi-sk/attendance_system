"""
テスト用の共通設定
"""

import asyncio
import os
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.models import *  # すべてのモデルをインポート

# テスト環境の設定
os.environ["TESTING"] = "true"
os.environ["RATE_LIMIT_ENABLED"] = "false"


class TestDatabase:
    """テスト用データベース"""

    def __init__(self):
        # インメモリSQLiteを使用
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            bind=self.engine,
        )

        # テーブル作成
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """テスト用セッションを取得"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def session_scope(self):
        """with文で使えるコンテキストマネージャ"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def cleanup(self):
        """データベースクリーンアップ"""
        Base.metadata.drop_all(bind=self.engine)


@pytest.fixture(scope="session")
def event_loop():
    """asyncio event loop fixture for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db():
    """テスト用データベース"""
    db = TestDatabase()
    yield db
    db.cleanup()


@pytest.fixture
def db_session(test_db):
    """テスト用DBセッション"""
    with test_db.session_scope() as session:
        yield session


@pytest.fixture
def client(test_db):
    """共通のテストクライアント（dependency_overrides設定済み）"""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.database import get_db

    def override_get_db():
        db = test_db.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # クリーンアップ
    app.dependency_overrides.clear()


@pytest.fixture
def test_admin_user(test_db):
    """共通の管理者ユーザー"""
    from backend.app.services.auth_service import AuthService
    from backend.app.models import User, UserRole

    db = test_db.SessionLocal()
    try:
        auth_service = AuthService(db)
        user = User(
            username="test_admin",
            password_hash=auth_service.get_password_hash("test123"),
            role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture
def auth_headers(client, test_admin_user):
    """認証ヘッダー"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test_admin", "password": "test123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
