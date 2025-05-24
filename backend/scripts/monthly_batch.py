#!/usr/bin/env python3
"""
月次バッチ処理スクリプト

毎月定時に実行し、月次集計処理を行います。
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
        logging.FileHandler(f'logs/monthly_batch_{date.today().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger(__name__)


async def process_monthly_summary(year: int = None, month: int = None):
    """
    月次集計処理を実行
    
    Args:
        year: 処理対象年
        month: 処理対象月
    """
    if year is None or month is None:
        # 前月を対象とする
        today = date.today()
        if today.month == 1:
            year = today.year - 1
            month = 12
        else:
            year = today.year
            month = today.month - 1
    
    logger.info(f"月次集計処理を開始します: {year}年{month}月")
    
    db: Session = SessionLocal()
    try:
        service = ReportService(db)
        
        # 月次レポートCSV生成
        csv_data = await service.export_monthly_report_csv(year, month)
        
        # CSVファイル保存
        filename = f"exports/monthly_report_{year}{month:02d}.csv"
        with open(filename, 'w', encoding='utf-8-sig') as f:
            f.write(csv_data)
        
        logger.info(f"月次レポートを保存しました: {filename}")
        
        # 統計情報取得
        statistics = await service.get_monthly_statistics(year, month)
        logger.info(f"月次統計: {statistics}")
        
        # TODO: MonthlySummaryテーブルに保存
        # TODO: Slack通知を送信
        # TODO: メール送信
        
    except Exception as e:
        logger.error(f"月次集計処理でエラーが発生しました: {e}", exc_info=True)
        raise
    finally:
        db.close()


def main():
    """メイン処理"""
    import asyncio
    
    logger.info("月次バッチ処理を開始します")
    
    try:
        # 前月の集計を実行
        asyncio.run(process_monthly_summary())
        
        logger.info("月次バッチ処理が正常に完了しました")
        
    except Exception as e:
        logger.error(f"バッチ処理が異常終了しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()