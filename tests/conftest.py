"""
テスト用の共通設定
"""

import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.models import *  # すべてのモデルをインポート


class TestDatabase:
    """テスト用データベース"""
    
    def __init__(self):
        # インメモリSQLiteを使用
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # テーブル作成
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """テスト用セッションを取得"""
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
    """イベントループのフィクスチャ"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db():
    """テスト用データベースフィクスチャ"""
    db = TestDatabase()
    yield db
    db.cleanup()