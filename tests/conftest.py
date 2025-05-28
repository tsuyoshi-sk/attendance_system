"""
テスト設定

pytest用の共通設定とフィクスチャ
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# 標準インポートパスに修正
from attendance_system.app.main import app
from attendance_system.app.database import get_db, Base
from attendance_system.config.config import settings


# テスト用データベースエンジン
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_test_db() -> Generator[Session, None, None]:
    """テスト用データベースセッション"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def event_loop():
    """セッションスコープのイベントループ"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """データベースフィクスチャ"""
    # テーブルを作成
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # テーブルを削除
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """テストクライアントフィクスチャ"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_employee_data() -> dict:
    """サンプル従業員データ"""
    return {
        "name": "テスト太郎",
        "employee_code": "TEST001",
        "email": "test@example.com",
        "department_id": None,
        "is_active": True
    }


@pytest.fixture
def sample_card_data() -> dict:
    """サンプルカードデータ"""
    return {
        "card_id": "test_card_123"
    }


@pytest.fixture
def sample_punch_data() -> dict:
    """サンプル打刻データ"""
    return {
        "card_idm": "test_card_123",
        "punch_type": "in"
    }


@pytest.fixture
def auth_headers() -> dict:
    """認証ヘッダー（テスト用）"""
    return {
        "Authorization": "Bearer test-token"
    }


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """テスト環境設定"""
    # テスト用環境変数設定
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-64-characters-long")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-64-characters-long")
    monkeypatch.setenv("PASORI_MOCK_MODE", "True")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")


# マーカー設定
pytest_plugins = []


def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """テスト収集時の設定変更"""
    # スローテストのマーキング
    slow_marker = pytest.mark.slow
    for item in items:
        if "slow" in item.nodeid:
            item.add_marker(slow_marker)