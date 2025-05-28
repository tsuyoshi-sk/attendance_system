#!/usr/bin/env python3
"""
データベース接続待機スクリプト

コンテナ起動時にデータベースが利用可能になるまで待機します。
"""

import os
import sys
import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_db(max_retries=30, retry_interval=2):
    """
    データベースが利用可能になるまで待機
    
    Args:
        max_retries: 最大リトライ回数
        retry_interval: リトライ間隔（秒）
    """
    database_url = os.getenv('DATABASE_URL', 'postgresql://attendance_user:attendance_pass@localhost:5432/attendance_db')
    
    logger.info(f"Waiting for database at {database_url.split('@')[1] if '@' in database_url else database_url}")
    
    engine = create_engine(database_url)
    
    for attempt in range(max_retries):
        try:
            # 接続テスト
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("Database is ready!")
            return True
        except OperationalError as e:
            if attempt < max_retries - 1:
                logger.info(f"Database not ready, waiting... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_interval)
            else:
                logger.error(f"Could not connect to database after {max_retries} attempts")
                logger.error(f"Error: {e}")
                return False
    
    return False

if __name__ == "__main__":
    if not wait_for_db():
        sys.exit(1)
    sys.exit(0)