"""
非同期データベース接続管理モジュール

SQLAlchemyの非同期機能を使用したデータベース接続とセッション管理を行います。
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import sys
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.config import settings

logger = logging.getLogger(__name__)


def get_async_database_url() -> str:
    """非同期用データベースURLの取得"""
    db_url = settings.DATABASE_URL
    
    # SQLiteの場合、aiosqliteドライバーを使用
    if db_url.startswith("sqlite:///"):
        # sqlite:/// を sqlite+aiosqlite:/// に変換
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        
        # ディレクトリ確保
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
    
    # PostgreSQLの場合、asyncpgドライバーを使用
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    return db_url


# 非同期エンジンの作成
async_engine: AsyncEngine = create_async_engine(
    get_async_database_url(),
    echo=settings.DATABASE_ECHO,
    pool_size=settings.MIN_CONNECTIONS_COUNT,
    max_overflow=settings.MAX_CONNECTIONS_COUNT - settings.MIN_CONNECTIONS_COUNT,
    pool_pre_ping=True,  # 接続の健全性チェック
    pool_recycle=3600,   # 1時間で接続をリサイクル
    poolclass=NullPool if "sqlite" in settings.DATABASE_URL else QueuePool,
)

# 非同期セッションファクトリの作成
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ベースクラスの作成（同期版と共有）
from backend.app.database import Base


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    非同期データベースセッションを取得する依存性注入関数
    
    Yields:
        AsyncSession: 非同期データベースセッション
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    非同期データベースセッションのコンテキストマネージャー
    
    使用例:
        async with get_async_db_context() as db:
            result = await db.execute(select(User))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_async_db() -> None:
    """
    非同期データベースを初期化（テーブル作成）
    """
    # データベースディレクトリの確保
    db_url = get_async_database_url()
    if "sqlite" in db_url:
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
    
    # 全てのモデルをインポート（Baseのメタデータに登録するため）
    from backend.app.models import employee, punch_record, summary, user, employee_card
    
    # 非同期でテーブル作成
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Async database initialization completed")


async def close_async_db() -> None:
    """
    非同期データベース接続を閉じる
    """
    await async_engine.dispose()
    logger.info("Async database connections closed")


async def reset_async_connection_pool() -> None:
    """
    非同期接続プールをリセット（エラー回復用）
    """
    try:
        await async_engine.dispose()
        logger.info("Async database connection pool reset")
    except Exception as e:
        logger.error(f"Failed to reset async connection pool: {e}")
        raise


class DatabaseTransaction:
    """
    トランザクション管理クラス
    
    使用例:
        async with DatabaseTransaction() as transaction:
            async with transaction.session() as db:
                # データベース操作
                await db.execute(...)
    """
    
    def __init__(self):
        self._session = None
    
    async def __aenter__(self):
        self._session = AsyncSessionLocal()
        await self._session.begin()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self._session.rollback()
        else:
            await self._session.commit()
        await self._session.close()
        return False
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """セッションを取得"""
        yield self._session