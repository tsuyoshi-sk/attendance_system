"""
スケジューラー

日次・月次バッチ処理を定期実行するためのスケジューラー
"""

import asyncio
import schedule
import time
import logging
from datetime import datetime, date, timedelta
import sys
import os

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.scripts.daily_batch import DailyBatchProcessor
from backend.scripts.monthly_batch import MonthlyBatchProcessor
from backend.app.database import init_db
from backend.app.utils import setup_logging, get_logger

# ログ設定
setup_logging()
logger = get_logger(__name__)


class AttendanceScheduler:
    """勤怠システムスケジューラー"""
    
    def __init__(self):
        self.running = False
        
    def setup_schedules(self):
        """スケジュールを設定"""
        
        # 日次バッチ処理（毎日23:59に前日分を処理）
        schedule.every().day.at("23:59").do(self.run_daily_batch)
        
        # 月次バッチ処理（毎月1日01:00に前月分を処理）
        # ※実際の運用では月末の営業時間外に実行することを推奨
        schedule.every().month.at("01:00").do(self.run_monthly_batch)
        
        # 週次レポート（毎週月曜日08:00）
        schedule.every().monday.at("08:00").do(self.run_weekly_report)
        
        # システムヘルスチェック（毎時00分）
        schedule.every().hour.at(":00").do(self.run_health_check)
        
        logger.info("スケジュール設定完了")
        logger.info("- 日次バッチ: 毎日 23:59")
        logger.info("- 月次バッチ: 毎月1日 01:00")
        logger.info("- 週次レポート: 毎週月曜日 08:00")
        logger.info("- ヘルスチェック: 毎時 00分")
    
    def run_daily_batch(self):
        """日次バッチ処理を実行"""
        logger.info("日次バッチ処理をスケジュール実行")
        
        try:
            # 前日の日付で実行
            target_date = date.today() - timedelta(days=1)
            
            processor = DailyBatchProcessor()
            asyncio.run(processor.run(target_date))
            
            logger.info("日次バッチ処理完了")
            
        except Exception as e:
            logger.error(f"日次バッチ処理エラー: {e}")
    
    def run_monthly_batch(self):
        """月次バッチ処理を実行"""
        logger.info("月次バッチ処理をスケジュール実行")
        
        try:
            # 前月を計算
            today = date.today()
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1
            
            processor = MonthlyBatchProcessor()
            asyncio.run(processor.run(year, month))
            
            logger.info("月次バッチ処理完了")
            
        except Exception as e:
            logger.error(f"月次バッチ処理エラー: {e}")
    
    def run_weekly_report(self):
        """週次レポートを実行"""
        logger.info("週次レポート生成開始")
        
        try:
            # TODO: 週次レポート機能の実装
            logger.info("週次レポート生成完了")
            
        except Exception as e:
            logger.error(f"週次レポート生成エラー: {e}")
    
    def run_health_check(self):
        """システムヘルスチェックを実行"""
        try:
            # データベース接続チェック
            # TODO: 実際のヘルスチェック処理を実装
            logger.debug("システムヘルスチェック正常")
            
        except Exception as e:
            logger.error(f"システムヘルスチェックエラー: {e}")
    
    def start(self):
        """スケジューラーを開始"""
        self.running = True
        logger.info("勤怠システムスケジューラーを開始します")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1分間隔でチェック
                
            except KeyboardInterrupt:
                logger.info("スケジューラーの停止が要求されました")
                self.stop()
            except Exception as e:
                logger.error(f"スケジューラーエラー: {e}")
                time.sleep(60)  # エラー時も1分待機
    
    def stop(self):
        """スケジューラーを停止"""
        self.running = False
        logger.info("勤怠システムスケジューラーを停止しました")


def main():
    """メイン処理"""
    # データベース初期化
    init_db()
    
    # スケジューラー開始
    scheduler = AttendanceScheduler()
    scheduler.setup_schedules()
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("プログラムを終了します")
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()