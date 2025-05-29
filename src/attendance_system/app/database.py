"""
データベース接続管理モジュール

SQLAlchemyを使用したデータベース接続とセッション管理を行います。
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from config.config import config

logger = logging.getLogger(__name__)


def get_database_url():
    """データベースURLの安全な取得"""
    db_url = config.get_database_url()

    # SQLiteの場合、ディレクトリ確保
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

    return db_url


# データベースエンジンの作成
engine = create_engine(
    get_database_url(),
    echo=config.DATABASE_ECHO,
    connect_args={"check_same_thread": False}
    if "sqlite" in config.DATABASE_URL
    else {},
)

# セッションファクトリの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラスの作成
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    データベースセッションを取得する依存性注入関数

    Yields:
        Session: データベースセッション
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    データベースを初期化（テーブル作成）
    """
    # データベースディレクトリの確保
    db_url = get_database_url()
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

    # 全てのモデルをインポート（Baseのメタデータに登録するため）
    from backend.app.models import employee, punch_record, summary

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialization completed")


async def reset_connection_pool():
    """接続プールをリセット（エラー回復用）"""
    try:
        engine.dispose()
        logger.info("Database connection pool reset")
    except Exception as e:
        logger.error(f"Failed to reset connection pool: {e}")
        raise
