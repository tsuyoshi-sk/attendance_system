"""
エクスポートサービス

CSV、Excel、PDF形式でのデータエクスポート機能を提供
"""

import csv
import io
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import json

from backend.app.services.report_service import ReportService
from backend.app.utils import get_logger

logger = get_logger(__name__)


class ExportService:
    """エクスポートサービス"""

    def __init__(self, db: Session):
        self.db = db
        self.report_service = ReportService(db)

    async def export_daily_csv(
        self, from_date: date, to_date: date, employee_ids: Optional[List[str]] = None
    ) -> str:
        """
        日次レポートをCSV形式でエクスポート

        Args:
            from_date: 開始日
            to_date: 終了日
            employee_ids: 従業員IDリスト

        Returns:
            str: CSV文字列
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー
        writer.writerow(
            [
                "日付",
                "従業員コード",
                "従業員名",
                "出勤時刻",
                "退勤時刻",
                "労働時間",
                "残業時間",
                "深夜時間",
                "基本給",
                "残業代",
                "深夜代",
                "合計賃金",
            ]
        )

        # 期間内の各日について処理
        current_date = from_date
        while current_date <= to_date:
            daily_reports = await self.report_service.generate_daily_reports(
                target_date=current_date, employee_ids=employee_ids
            )

            for report in daily_reports:
                # 出退勤時刻を取得
                clock_in_time = ""
                clock_out_time = ""

                for punch in report.punch_records:
                    if punch.punch_type == "clock_in" and not clock_in_time:
                        clock_in_time = punch.timestamp.strftime("%H:%M")
                    elif punch.punch_type == "clock_out":
                        clock_out_time = punch.timestamp.strftime("%H:%M")

                writer.writerow(
                    [
                        report.date.strftime("%Y-%m-%d"),
                        report.employee_id,
                        report.employee_name,
                        clock_in_time,
                        clock_out_time,
                        f"{report.calculations.regular_hours:.1f}",
                        f"{report.calculations.overtime_hours:.1f}",
                        f"{report.calculations.night_hours:.1f}",
                        f"{report.calculations.basic_wage:,.0f}",
                        f"{report.calculations.overtime_wage:,.0f}",
                        f"{report.calculations.night_wage:,.0f}",
                        f"{report.calculations.total_wage:,.0f}",
                    ]
                )

            current_date += timedelta(days=1)

        return output.getvalue()

    async def export_monthly_csv(
        self, year: int, month: int, employee_ids: Optional[List[str]] = None
    ) -> str:
        """
        月次レポートをCSV形式でエクスポート

        Args:
            year: 年
            month: 月
            employee_ids: 従業員IDリスト

        Returns:
            str: CSV文字列
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー
        writer.writerow(
            [
                "年月",
                "従業員コード",
                "従業員名",
                "出勤日数",
                "労働時間",
                "残業時間",
                "深夜時間",
                "基本給",
                "残業代",
                "深夜代",
                "合計賃金",
            ]
        )

        # 月次レポートを生成
        monthly_reports = await self.report_service.generate_monthly_reports(
            year=year, month=month, employee_ids=employee_ids
        )

        for report in monthly_reports:
            writer.writerow(
                [
                    f"{report.year}-{report.month:02d}",
                    report.employee_id,
                    report.employee_name,
                    report.monthly_summary.work_days,
                    f"{report.monthly_summary.total_work_hours:.1f}",
                    f"{report.monthly_summary.overtime_hours:.1f}",
                    f"{report.monthly_summary.night_hours:.1f}",
                    f"{report.wage_calculation.basic_wage:,.0f}",
                    f"{report.wage_calculation.overtime_wage:,.0f}",
                    f"{report.wage_calculation.night_wage:,.0f}",
                    f"{report.wage_calculation.total_wage:,.0f}",
                ]
            )

        return output.getvalue()

    async def export_payroll_csv(self, year: int, month: int) -> str:
        """
        給与計算用CSVをエクスポート

        Args:
            year: 年
            month: 月

        Returns:
            str: CSV文字列
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー（給与システム連携用フォーマット）
        writer.writerow(
            [
                "従業員コード",
                "従業員名",
                "年",
                "月",
                "出勤日数",
                "総労働時間",
                "通常労働時間",
                "残業時間",
                "深夜時間",
                "休日労働時間",
                "基本給",
                "残業代",
                "深夜手当",
                "休日手当",
                "総支給額",
                "控除額",
                "差引支給額",
            ]
        )

        # 全従業員の月次レポートを生成
        monthly_reports = await self.report_service.generate_monthly_reports(
            year=year, month=month
        )

        for report in monthly_reports:
            writer.writerow(
                [
                    report.employee_id,
                    report.employee_name,
                    report.year,
                    report.month,
                    report.monthly_summary.work_days,
                    f"{report.monthly_summary.total_work_hours:.2f}",
                    f"{report.monthly_summary.regular_hours:.2f}",
                    f"{report.monthly_summary.overtime_hours:.2f}",
                    f"{report.monthly_summary.night_hours:.2f}",
                    f"{report.monthly_summary.holiday_hours:.2f}",
                    f"{report.wage_calculation.basic_wage:.0f}",
                    f"{report.wage_calculation.overtime_wage:.0f}",
                    f"{report.wage_calculation.night_wage:.0f}",
                    f"{report.wage_calculation.holiday_wage:.0f}",
                    f"{report.wage_calculation.total_wage:.0f}",
                    f"{report.wage_calculation.deductions:.0f}",
                    f"{report.wage_calculation.net_wage:.0f}",
                ]
            )

        return output.getvalue()

    async def export_payroll_json(self, year: int, month: int) -> Dict[str, Any]:
        """
        給与計算用JSONをエクスポート

        Args:
            year: 年
            month: 月

        Returns:
            Dict[str, Any]: 給与計算データ
        """
        monthly_reports = await self.report_service.generate_monthly_reports(
            year=year, month=month
        )

        payroll_data = {
            "year": year,
            "month": month,
            "generated_at": datetime.now().isoformat(),
            "employees": [],
        }

        for report in monthly_reports:
            employee_data = {
                "employee_code": report.employee_id,
                "employee_name": report.employee_name,
                "attendance": {
                    "work_days": report.monthly_summary.work_days,
                    "total_hours": report.monthly_summary.total_work_hours,
                    "regular_hours": report.monthly_summary.regular_hours,
                    "overtime_hours": report.monthly_summary.overtime_hours,
                    "night_hours": report.monthly_summary.night_hours,
                    "holiday_hours": report.monthly_summary.holiday_hours,
                },
                "wages": {
                    "basic": report.wage_calculation.basic_wage,
                    "overtime": report.wage_calculation.overtime_wage,
                    "night": report.wage_calculation.night_wage,
                    "holiday": report.wage_calculation.holiday_wage,
                    "total": report.wage_calculation.total_wage,
                    "deductions": report.wage_calculation.deductions,
                    "net": report.wage_calculation.net_wage,
                },
            }
            payroll_data["employees"].append(employee_data)

        return payroll_data

    async def export_attendance_summary_csv(self, year: int, month: int) -> str:
        """
        勤怠サマリーCSVをエクスポート（管理者向け）

        Args:
            year: 年
            month: 月

        Returns:
            str: CSV文字列
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー
        writer.writerow(
            [
                "従業員コード",
                "従業員名",
                "日付",
                "曜日",
                "出勤",
                "退勤",
                "休憩",
                "外出",
                "労働時間",
                "残業",
                "深夜",
                "遅刻",
                "早退",
                "備考",
            ]
        )

        # 月の開始日と終了日
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        # 曜日名
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]

        # 全従業員の日次データを出力
        current_date = first_day
        while current_date <= last_day:
            daily_reports = await self.report_service.generate_daily_reports(
                target_date=current_date
            )

            for report in daily_reports:
                # 出退勤時刻を取得
                clock_in = ""
                clock_out = ""
                breaks = []

                for punch in report.punch_records:
                    if punch.punch_type == "clock_in":
                        clock_in = punch.timestamp.strftime("%H:%M")
                    elif punch.punch_type == "clock_out":
                        clock_out = punch.timestamp.strftime("%H:%M")
                    elif punch.punch_type in ["break_start", "break_end"]:
                        breaks.append(
                            f"{punch.punch_type}: {punch.timestamp.strftime('%H:%M')}"
                        )

                # 備考
                notes = []
                if report.summary.overtime_minutes > 120:  # 2時間以上の残業
                    notes.append("長時間残業")
                if not clock_in:
                    notes.append("出勤なし")

                writer.writerow(
                    [
                        report.employee_id,
                        report.employee_name,
                        current_date.strftime("%Y-%m-%d"),
                        weekdays[current_date.weekday()],
                        clock_in,
                        clock_out,
                        f"{report.summary.break_minutes}分",
                        f"{report.summary.outside_minutes}分",
                        f"{report.summary.actual_work_minutes / 60:.1f}時間",
                        f"{report.summary.overtime_minutes / 60:.1f}時間"
                        if report.summary.overtime_minutes > 0
                        else "",
                        f"{report.summary.night_minutes / 60:.1f}時間"
                        if report.summary.night_minutes > 0
                        else "",
                        "",  # TODO: 遅刻時間
                        "",  # TODO: 早退時間
                        ", ".join(notes),
                    ]
                )

            current_date += timedelta(days=1)

        return output.getvalue()
