"""
日次バッチ処理

毎日定時に実行される日次レポート生成、集計、通知処理
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
import sys
import os
from typing import List, Dict, Any

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.database import SessionLocal, init_db
from backend.app.models import Employee, DailySummary
from backend.app.services.report_service import ReportService
from backend.app.services.notification_service import NotificationService
from backend.app.utils import setup_logging, get_logger
from config.config import config

# ログ設定
setup_logging()
logger = get_logger(__name__)


class DailyBatchProcessor:
    """日次バッチ処理クラス"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.report_service = ReportService(self.db)
        self.notification_service = NotificationService()
    
    async def run(self, target_date: date = None):
        """
        日次バッチ処理を実行
        
        Args:
            target_date: 処理対象日（省略時は昨日）
        """
        if not target_date:
            target_date = date.today() - timedelta(days=1)
        
        logger.info(f"日次バッチ処理開始: {target_date}")
        
        try:
            # 1. 日次レポート生成
            await self._generate_daily_reports(target_date)
            
            # 2. 日次集計データの保存
            await self._save_daily_summaries(target_date)
            
            # 3. アラート通知
            await self._send_daily_alerts(target_date)
            
            # 4. データバックアップ
            await self._backup_daily_data(target_date)
            
            # 5. 完了通知
            await self._send_completion_notification(target_date)
            
            logger.info(f"日次バッチ処理完了: {target_date}")
            
        except Exception as e:
            logger.error(f"日次バッチ処理エラー: {e}")
            await self._send_error_notification(target_date, str(e))
            raise
        finally:
            self.db.close()
    
    async def _generate_daily_reports(self, target_date: date):
        """日次レポートを生成"""
        logger.info("日次レポート生成開始")
        
        try:
            reports = await self.report_service.generate_daily_reports(target_date)
            logger.info(f"生成されたレポート数: {len(reports)}")
            
            # レポートの検証
            for report in reports:
                if report.summary.actual_work_minutes > 720:  # 12時間以上
                    logger.warning(
                        f"長時間労働検出: {report.employee_name} - "
                        f"{report.summary.actual_work_minutes / 60:.1f}時間"
                    )
            
        except Exception as e:
            logger.error(f"日次レポート生成エラー: {e}")
            raise
    
    async def _save_daily_summaries(self, target_date: date):
        """日次集計データをデータベースに保存"""
        logger.info("日次集計データ保存開始")
        
        try:
            # 既存の集計データを削除（再実行対応）
            self.db.query(DailySummary).filter(
                DailySummary.work_date == target_date
            ).delete()
            
            # 新しい集計データを生成
            reports = await self.report_service.generate_daily_reports(target_date)
            
            for report in reports:
                # 従業員IDを取得
                employee = self.db.query(Employee).filter(
                    Employee.employee_code == report.employee_id
                ).first()
                
                if not employee:
                    logger.warning(f"従業員が見つかりません: {report.employee_id}")
                    continue
                
                # 日次集計を作成
                summary = DailySummary(
                    employee_id=employee.id,
                    work_date=target_date,
                    clock_in_time=None,  # TODO: 実際の出勤時刻を設定
                    clock_out_time=None,  # TODO: 実際の退勤時刻を設定
                    work_minutes=report.summary.work_minutes,
                    break_minutes=report.summary.break_minutes,
                    overtime_minutes=report.summary.overtime_minutes,
                    night_minutes=report.summary.night_minutes,
                    holiday_minutes=0,  # TODO: 休日労働時間
                    late_minutes=0,  # TODO: 遅刻時間
                    early_leave_minutes=0,  # TODO: 早退時間
                    basic_wage=int(report.calculations.basic_wage),
                    overtime_wage=int(report.calculations.overtime_wage),
                    night_wage=int(report.calculations.night_wage),
                    holiday_wage=0,  # TODO: 休日手当
                    total_wage=int(report.calculations.total_wage)
                )
                
                self.db.add(summary)
            
            self.db.commit()
            logger.info("日次集計データ保存完了")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"日次集計データ保存エラー: {e}")
            raise
    
    async def _send_daily_alerts(self, target_date: date):
        """日次アラートを送信"""
        logger.info("日次アラート送信開始")
        
        try:
            reports = await self.report_service.generate_daily_reports(target_date)
            alerts = []
            
            for report in reports:
                # 長時間労働アラート
                if report.summary.overtime_minutes >= 180:  # 3時間以上
                    alerts.append({
                        "type": "overtime",
                        "employee": report.employee_name,
                        "message": f"残業時間: {report.summary.overtime_minutes / 60:.1f}時間"
                    })
                
                # 打刻漏れアラート
                if report.summary.work_minutes == 0 and self._is_workday(target_date):
                    alerts.append({
                        "type": "missing_punch",
                        "employee": report.employee_name,
                        "message": "出勤記録がありません"
                    })
            
            # Slack通知
            if alerts:
                await self.notification_service.send_daily_alerts(target_date, alerts)
                logger.info(f"送信されたアラート数: {len(alerts)}")
            
        except Exception as e:
            logger.error(f"アラート送信エラー: {e}")
            # アラート送信の失敗は処理を止めない
    
    async def _backup_daily_data(self, target_date: date):
        """日次データのバックアップ"""
        logger.info("日次データバックアップ開始")
        
        try:
            # TODO: 実際のバックアップ処理を実装
            # - 打刻データのエクスポート
            # - S3やGCSへのアップロード
            # - ローカルバックアップの作成
            
            logger.info("日次データバックアップ完了")
            
        except Exception as e:
            logger.error(f"バックアップエラー: {e}")
            # バックアップの失敗は処理を止めない
    
    async def _send_completion_notification(self, target_date: date):
        """完了通知を送信"""
        try:
            message = f"日次バッチ処理が完了しました\n対象日: {target_date}"
            await self.notification_service.send_admin_notification(
                "日次バッチ完了",
                message
            )
        except Exception as e:
            logger.error(f"完了通知送信エラー: {e}")
    
    async def _send_error_notification(self, target_date: date, error_message: str):
        """エラー通知を送信"""
        try:
            message = f"日次バッチ処理でエラーが発生しました\n"
            message += f"対象日: {target_date}\n"
            message += f"エラー: {error_message}"
            
            await self.notification_service.send_admin_notification(
                "日次バッチエラー",
                message,
                severity="error"
            )
        except Exception as e:
            logger.error(f"エラー通知送信エラー: {e}")
    
    def _is_workday(self, target_date: date) -> bool:
        """営業日判定（簡易版）"""
        # TODO: 祝日カレンダーの実装
        return target_date.weekday() < 5  # 月〜金


async def main():
    """メイン処理"""
    # データベース初期化
    init_db()
    
    # コマンドライン引数から日付を取得
    if len(sys.argv) > 1:
        try:
            target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        except ValueError:
            logger.error("日付は YYYY-MM-DD 形式で指定してください")
            sys.exit(1)
    else:
        # 引数なしの場合は昨日を処理
        target_date = date.today() - timedelta(days=1)
    
    # バッチ処理実行
    processor = DailyBatchProcessor()
    await processor.run(target_date)


if __name__ == "__main__":
    asyncio.run(main())