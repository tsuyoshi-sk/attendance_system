"""
月次バッチ処理

毎月1日に実行される月次レポート生成、給与計算データ作成、通知処理
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
import sys
import os
from typing import List, Dict, Any
import json

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.database import SessionLocal, init_db
from backend.app.models import Employee, MonthlySummary
from backend.app.services.report_service import ReportService
from backend.app.services.export_service import ExportService
from backend.app.services.notification_service import NotificationService
from backend.app.utils import setup_logging, get_logger
from config.config import config

# ログ設定
setup_logging()
logger = get_logger(__name__)


class MonthlyBatchProcessor:
    """月次バッチ処理クラス"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.report_service = ReportService(self.db)
        self.export_service = ExportService(self.db)
        self.notification_service = NotificationService()
    
    async def run(self, year: int = None, month: int = None):
        """
        月次バッチ処理を実行
        
        Args:
            year: 処理対象年（省略時は前月）
            month: 処理対象月（省略時は前月）
        """
        # 対象年月の決定
        if not year or not month:
            today = date.today()
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1
        
        logger.info(f"月次バッチ処理開始: {year}年{month}月")
        
        try:
            # 1. 月次レポート生成
            await self._generate_monthly_reports(year, month)
            
            # 2. 月次集計データの保存
            await self._save_monthly_summaries(year, month)
            
            # 3. CSV自動出力
            await self._export_monthly_csv(year, month)
            
            # 4. 給与システム連携データ作成
            await self._generate_payroll_data(year, month)
            
            # 5. 月次アラート通知
            await self._send_monthly_alerts(year, month)
            
            # 6. 完了通知
            await self._send_completion_notification(year, month)
            
            logger.info(f"月次バッチ処理完了: {year}年{month}月")
            
        except Exception as e:
            logger.error(f"月次バッチ処理エラー: {e}")
            await self._send_error_notification(year, month, str(e))
            raise
        finally:
            self.db.close()
    
    async def _generate_monthly_reports(self, year: int, month: int):
        """月次レポートを生成"""
        logger.info("月次レポート生成開始")
        
        try:
            reports = await self.report_service.generate_monthly_reports(year, month)
            logger.info(f"生成されたレポート数: {len(reports)}")
            
            # レポートの検証
            for report in reports:
                # 月間残業時間チェック
                if report.monthly_summary.overtime_hours > 45:
                    logger.warning(
                        f"月間残業時間超過: {report.employee_name} - "
                        f"{report.monthly_summary.overtime_hours:.1f}時間"
                    )
                
                # 出勤日数チェック
                expected_workdays = self._get_expected_workdays(year, month)
                if report.monthly_summary.work_days < expected_workdays * 0.8:
                    logger.warning(
                        f"出勤日数不足: {report.employee_name} - "
                        f"{report.monthly_summary.work_days}日/{expected_workdays}日"
                    )
            
        except Exception as e:
            logger.error(f"月次レポート生成エラー: {e}")
            raise
    
    async def _save_monthly_summaries(self, year: int, month: int):
        """月次集計データをデータベースに保存"""
        logger.info("月次集計データ保存開始")
        
        try:
            # 既存の集計データを削除（再実行対応）
            self.db.query(MonthlySummary).filter(
                MonthlySummary.year == year,
                MonthlySummary.month == month
            ).delete()
            
            # 新しい集計データを生成
            reports = await self.report_service.generate_monthly_reports(year, month)
            
            for report in reports:
                # 従業員IDを取得
                employee = self.db.query(Employee).filter(
                    Employee.employee_code == report.employee_id
                ).first()
                
                if not employee:
                    logger.warning(f"従業員が見つかりません: {report.employee_id}")
                    continue
                
                # 月次集計を作成
                summary = MonthlySummary(
                    employee_id=employee.id,
                    year=year,
                    month=month,
                    work_days=report.monthly_summary.work_days,
                    total_work_minutes=int(report.monthly_summary.total_work_hours * 60),
                    total_overtime_minutes=int(report.monthly_summary.overtime_hours * 60),
                    total_night_minutes=int(report.monthly_summary.night_hours * 60),
                    total_holiday_minutes=int(report.monthly_summary.holiday_hours * 60),
                    total_late_minutes=0,  # TODO: 遅刻時間の集計
                    total_early_leave_minutes=0,  # TODO: 早退時間の集計
                    basic_wage=int(report.wage_calculation.basic_wage),
                    overtime_wage=int(report.wage_calculation.overtime_wage),
                    night_wage=int(report.wage_calculation.night_wage),
                    holiday_wage=int(report.wage_calculation.holiday_wage),
                    deductions=int(report.wage_calculation.deductions),
                    net_wage=int(report.wage_calculation.net_wage)
                )
                
                self.db.add(summary)
            
            self.db.commit()
            logger.info("月次集計データ保存完了")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"月次集計データ保存エラー: {e}")
            raise
    
    async def _export_monthly_csv(self, year: int, month: int):
        """月次CSVを自動出力"""
        logger.info("月次CSV出力開始")
        
        try:
            # 出力ディレクトリの作成
            output_dir = f"output/monthly_reports/{year}/{month:02d}"
            os.makedirs(output_dir, exist_ok=True)
            
            # 月次レポートCSV
            monthly_csv = await self.export_service.export_monthly_csv(year, month)
            with open(f"{output_dir}/monthly_report_{year}_{month:02d}.csv", "w", encoding="utf-8-sig") as f:
                f.write(monthly_csv)
            
            # 給与計算用CSV
            payroll_csv = await self.export_service.export_payroll_csv(year, month)
            with open(f"{output_dir}/payroll_{year}_{month:02d}.csv", "w", encoding="utf-8-sig") as f:
                f.write(payroll_csv)
            
            # 勤怠サマリーCSV
            summary_csv = await self.export_service.export_attendance_summary_csv(year, month)
            with open(f"{output_dir}/attendance_summary_{year}_{month:02d}.csv", "w", encoding="utf-8-sig") as f:
                f.write(summary_csv)
            
            logger.info(f"CSV出力完了: {output_dir}")
            
        except Exception as e:
            logger.error(f"CSV出力エラー: {e}")
            # CSV出力の失敗は処理を止めない
    
    async def _generate_payroll_data(self, year: int, month: int):
        """給与システム連携データを作成"""
        logger.info("給与システム連携データ作成開始")
        
        try:
            # 給与計算用JSONデータ
            payroll_data = await self.export_service.export_payroll_json(year, month)
            
            # 出力
            output_dir = f"output/payroll_data/{year}"
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = f"{output_dir}/payroll_{year}_{month:02d}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(payroll_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"給与システム連携データ作成完了: {output_file}")
            
            # 給与システムへの自動アップロード（実装例）
            # await self._upload_to_payroll_system(payroll_data)
            
        except Exception as e:
            logger.error(f"給与システム連携データ作成エラー: {e}")
            # 連携データ作成の失敗は処理を止めない
    
    async def _send_monthly_alerts(self, year: int, month: int):
        """月次アラートを送信"""
        logger.info("月次アラート送信開始")
        
        try:
            reports = await self.report_service.generate_monthly_reports(year, month)
            alerts = []
            
            for report in reports:
                # 月間残業時間アラート
                if report.monthly_summary.overtime_hours >= 45:
                    severity = "warning" if report.monthly_summary.overtime_hours < 60 else "error"
                    alerts.append({
                        "type": "monthly_overtime",
                        "employee": report.employee_name,
                        "message": f"月間残業時間: {report.monthly_summary.overtime_hours:.1f}時間",
                        "severity": severity
                    })
                
                # 出勤日数不足アラート
                expected_workdays = self._get_expected_workdays(year, month)
                if report.monthly_summary.work_days < expected_workdays * 0.8:
                    alerts.append({
                        "type": "low_attendance",
                        "employee": report.employee_name,
                        "message": f"出勤日数: {report.monthly_summary.work_days}日/{expected_workdays}日",
                        "severity": "warning"
                    })
                
                # 賃金異常アラート
                if report.wage_calculation.total_wage < 100000:  # 10万円未満
                    alerts.append({
                        "type": "low_wage",
                        "employee": report.employee_name,
                        "message": f"総支給額: {report.wage_calculation.total_wage:,}円",
                        "severity": "info"
                    })
            
            # Slack通知
            if alerts:
                await self.notification_service.send_monthly_alerts(year, month, alerts)
                logger.info(f"送信されたアラート数: {len(alerts)}")
            
        except Exception as e:
            logger.error(f"アラート送信エラー: {e}")
            # アラート送信の失敗は処理を止めない
    
    async def _send_completion_notification(self, year: int, month: int):
        """完了通知を送信"""
        try:
            # サマリー情報の作成
            reports = await self.report_service.generate_monthly_reports(year, month)
            
            total_employees = len(reports)
            total_work_hours = sum(r.monthly_summary.total_work_hours for r in reports)
            total_overtime_hours = sum(r.monthly_summary.overtime_hours for r in reports)
            total_wages = sum(r.wage_calculation.total_wage for r in reports)
            
            message = f"月次バッチ処理が完了しました\n"
            message += f"対象月: {year}年{month}月\n"
            message += f"処理人数: {total_employees}名\n"
            message += f"総労働時間: {total_work_hours:,.1f}時間\n"
            message += f"総残業時間: {total_overtime_hours:,.1f}時間\n"
            message += f"総支給額: {total_wages:,}円"
            
            await self.notification_service.send_admin_notification(
                "月次バッチ完了",
                message
            )
        except Exception as e:
            logger.error(f"完了通知送信エラー: {e}")
    
    async def _send_error_notification(self, year: int, month: int, error_message: str):
        """エラー通知を送信"""
        try:
            message = f"月次バッチ処理でエラーが発生しました\n"
            message += f"対象月: {year}年{month}月\n"
            message += f"エラー: {error_message}"
            
            await self.notification_service.send_admin_notification(
                "月次バッチエラー",
                message,
                severity="error"
            )
        except Exception as e:
            logger.error(f"エラー通知送信エラー: {e}")
    
    def _get_expected_workdays(self, year: int, month: int) -> int:
        """月の営業日数を計算（簡易版）"""
        # 月の最初と最後の日を取得
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        # 営業日をカウント
        workdays = 0
        current = first_day
        while current <= last_day:
            if current.weekday() < 5:  # 月〜金
                workdays += 1
            current += timedelta(days=1)
        
        return workdays


async def main():
    """メイン処理"""
    # データベース初期化
    init_db()
    
    # コマンドライン引数から年月を取得
    year = None
    month = None
    
    if len(sys.argv) >= 3:
        try:
            year = int(sys.argv[1])
            month = int(sys.argv[2])
            
            if month < 1 or month > 12:
                raise ValueError("月は1〜12の範囲で指定してください")
                
        except ValueError as e:
            logger.error(f"引数エラー: {e}")
            logger.error("使用方法: python monthly_batch.py [年] [月]")
            sys.exit(1)
    
    # バッチ処理実行
    processor = MonthlyBatchProcessor()
    await processor.run(year, month)


if __name__ == "__main__":
    asyncio.run(main())