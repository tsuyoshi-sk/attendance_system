"""
データベース接続管理モジュール

SQLAlchemyを使用したデータベース接続とセッション管理を行います。
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import sys
import os

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.config import config


# データベースエンジンの作成
engine = create_engine(
    config.get_database_url(),
    echo=config.DATABASE_ECHO,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
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
    # 全てのモデルをインポート（Baseのメタデータに登録するため）
    from backend.app.models import employee, punch_record, summary
    
    Base.metadata.create_all(bind=engine)
    print("データベースの初期化が完了しました。")