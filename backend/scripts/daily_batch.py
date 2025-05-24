#!/usr/bin/env python3
"""
日次バッチ処理スクリプト

毎日定時に実行し、日次集計処理を行います。
"""

import sys
import os
import logging
from datetime import date, datetime, timedelta

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from config.config import config
from backend.app.database import SessionLocal
from backend.app.services.report_service import ReportService


# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/daily_batch_{date.today().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger(__name__)


async def process_daily_summary(target_date: date = None):
    """
    日次集計処理を実行
    
    Args:
        target_date: 処理対象日（デフォルト：前日）
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    
    logger.info(f"日次集計処理を開始します: {target_date}")
    
    db: Session = SessionLocal()
    try:
        service = ReportService(db)
        summaries = await service.generate_daily_summary(target_date)
        
        logger.info(f"集計完了: {len(summaries)}名分の勤怠を処理しました")
        
        # TODO: 集計結果をDailySummaryテーブルに保存
        # TODO: Slack通知を送信
        
    except Exception as e:
        logger.error(f"日次集計処理でエラーが発生しました: {e}", exc_info=True)
        raise
    finally:
        db.close()


def main():
    """メイン処理"""
    import asyncio
    
    logger.info("日次バッチ処理を開始します")
    
    try:
        # 前日の集計を実行
        asyncio.run(process_daily_summary())
        
        logger.info("日次バッチ処理が正常に完了しました")
        
    except Exception as e:
        logger.error(f"バッチ処理が異常終了しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()