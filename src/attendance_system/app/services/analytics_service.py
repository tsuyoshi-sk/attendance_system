"""
分析サービス

ダッシュボード、統計分析、アラート生成などの分析機能を提供
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import statistics

from backend.app.models import (
    Employee,
    PunchRecord,
    DailySummary,
    MonthlySummary,
    PunchType,
)
from backend.app.schemas.report import (
    DashboardResponse,
    DashboardSummary,
    DashboardAlert,
    StatisticsResponse,
    AttendanceStats,
    OvertimeAnalysis,
    TrendAnalysis,
    ChartDataResponse,
)
from backend.app.services.report_service import ReportService
from backend.app.utils import get_logger
from config.config import config

logger = get_logger(__name__)


class AnalyticsService:
    """分析サービス"""

    def __init__(self, db: Session):
        self.db = db
        self.report_service = ReportService(db)

        # アラート条件
        self.alert_conditions = {
            "overtime_monthly": 45,  # 月間残業45時間でアラート
            "overtime_daily": 3,  # 日次残業3時間でアラート
            "late_arrival": "09:30",  # 9:30以降出勤でアラート
            "early_departure": "17:30",  # 17:30以前退勤でアラート
            "continuous_overtime": 5,  # 5日連続残業でアラート
        }

    async def get_dashboard_data(self) -> DashboardResponse:
        """
        ダッシュボードデータを取得

        Returns:
            DashboardResponse: ダッシュボードデータ
        """
        today = date.today()

        # 本日のサマリー
        today_summary = await self._get_today_summary()

        # 今月のサマリー
        this_month_summary = await self._get_this_month_summary()

        # アラート
        alerts = await self.get_current_alerts()

        return DashboardResponse(
            today_summary=today_summary, this_month=this_month_summary, alerts=alerts
        )

    async def _get_today_summary(self) -> DashboardSummary:
        """本日のサマリーを取得"""
        today = date.today()

        # 全アクティブ従業員数
        total_employees = (
            self.db.query(Employee).filter(Employee.is_active == True).count()
        )

        # 本日出勤済み従業員数
        present_employees = (
            self.db.query(func.count(func.distinct(PunchRecord.employee_id)))
            .filter(
                and_(
                    PunchRecord.punch_time
                    >= datetime.combine(today, datetime.min.time()),
                    PunchRecord.punch_time
                    < datetime.combine(today + timedelta(days=1), datetime.min.time()),
                    PunchRecord.punch_type == PunchType.IN.value,
                )
            )
            .scalar()
            or 0
        )

        # 本日の総労働時間を計算
        daily_reports = await self.report_service.generate_daily_reports(today)
        total_work_hours = sum(
            report.summary.actual_work_minutes / 60.0 for report in daily_reports
        )

        # 平均労働時間
        average_work_hours = (
            total_work_hours / present_employees if present_employees > 0 else 0
        )

        return DashboardSummary(
            total_employees=total_employees,
            present_employees=present_employees,
            total_work_hours=total_work_hours,
            average_work_hours=average_work_hours,
        )

    async def _get_this_month_summary(self) -> Dict[str, Any]:
        """今月のサマリーを取得"""
        today = date.today()
        first_day = date(today.year, today.month, 1)

        # 営業日数（簡易版：土日を除く）
        work_days = 0
        current = first_day
        while current <= today:
            if current.weekday() < 5:  # 月〜金
                work_days += 1
            current += timedelta(days=1)

        # 今月の統計を集計
        monthly_stats = (
            self.db.query(
                func.count(func.distinct(PunchRecord.employee_id)).label(
                    "unique_employees"
                ),
                func.count(func.distinct(func.date(PunchRecord.punch_time))).label(
                    "unique_days"
                ),
            )
            .filter(
                and_(
                    PunchRecord.punch_time
                    >= datetime.combine(first_day, datetime.min.time()),
                    PunchRecord.punch_time
                    <= datetime.combine(today + timedelta(days=1), datetime.min.time()),
                    PunchRecord.punch_type == PunchType.IN.value,
                )
            )
            .first()
        )

        # 月間の総労働時間と残業時間を計算
        total_work_hours = 0
        total_overtime_hours = 0

        # 各日の集計
        current = first_day
        while current <= today:
            daily_reports = await self.report_service.generate_daily_reports(current)
            for report in daily_reports:
                total_work_hours += report.summary.actual_work_minutes / 60.0
                total_overtime_hours += report.summary.overtime_minutes / 60.0
            current += timedelta(days=1)

        # 出勤率
        total_employees = (
            self.db.query(Employee).filter(Employee.is_active == True).count()
        )
        attendance_rate = (
            (monthly_stats.unique_employees / (total_employees * work_days) * 100)
            if work_days > 0
            else 0
        )

        return {
            "total_work_days": work_days,
            "total_work_hours": total_work_hours,
            "total_overtime_hours": total_overtime_hours,
            "attendance_rate": attendance_rate,
            "unique_employees": monthly_stats.unique_employees,
            "unique_days": monthly_stats.unique_days,
        }

    async def get_statistics(
        self,
        period: str = "month",
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> StatisticsResponse:
        """
        統計データを取得

        Args:
            period: 期間（day, week, month, year）
            year: 年
            month: 月

        Returns:
            StatisticsResponse: 統計データ
        """
        # 期間の開始日と終了日を決定
        if period == "day":
            start_date = date.today()
            end_date = date.today()
        elif period == "week":
            today = date.today()
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif period == "month":
            if not year or not month:
                today = date.today()
                year, month = today.year, today.month
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
        else:  # year
            if not year:
                year = date.today().year
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)

        # 勤怠統計
        attendance_stats = await self._calculate_attendance_stats(start_date, end_date)

        # 残業分析
        overtime_analysis = await self._calculate_overtime_analysis(
            start_date, end_date
        )

        # トレンド分析
        trend_analysis = await self._calculate_trend_analysis(start_date, end_date)

        return StatisticsResponse(
            attendance_stats=attendance_stats,
            overtime_analysis=overtime_analysis,
            trend_analysis=trend_analysis,
        )

    async def _calculate_attendance_stats(
        self, start_date: date, end_date: date
    ) -> AttendanceStats:
        """勤怠統計を計算"""
        work_hours_list = []

        # 各従業員の期間内労働時間を集計
        employees = self.db.query(Employee).filter(Employee.is_active == True).all()

        for employee in employees:
            total_hours = 0
            current = start_date
            while current <= end_date:
                daily_reports = await self.report_service.generate_daily_reports(
                    current, [employee.employee_code]
                )
                if daily_reports:
                    total_hours += daily_reports[0].summary.actual_work_minutes / 60.0
                current += timedelta(days=1)

            if total_hours > 0:
                work_hours_list.append(total_hours)

        if not work_hours_list:
            return AttendanceStats(
                average_work_hours=0,
                max_work_hours=0,
                min_work_hours=0,
                standard_deviation=0,
            )

        return AttendanceStats(
            average_work_hours=statistics.mean(work_hours_list),
            max_work_hours=max(work_hours_list),
            min_work_hours=min(work_hours_list),
            standard_deviation=statistics.stdev(work_hours_list)
            if len(work_hours_list) > 1
            else 0,
        )

    async def _calculate_overtime_analysis(
        self, start_date: date, end_date: date
    ) -> OvertimeAnalysis:
        """残業分析を計算"""
        overtime_by_employee = {}

        # 各従業員の残業時間を集計
        employees = self.db.query(Employee).filter(Employee.is_active == True).all()

        for employee in employees:
            total_overtime = 0
            current = start_date
            while current <= end_date:
                daily_reports = await self.report_service.generate_daily_reports(
                    current, [employee.employee_code]
                )
                if daily_reports:
                    total_overtime += daily_reports[0].summary.overtime_minutes / 60.0
                current += timedelta(days=1)

            overtime_by_employee[employee.employee_code] = total_overtime

        # 残業時間分布
        distribution = {"0-10h": 0, "10-20h": 0, "20-30h": 0, "30h+": 0}

        for overtime in overtime_by_employee.values():
            if overtime <= 10:
                distribution["0-10h"] += 1
            elif overtime <= 20:
                distribution["10-20h"] += 1
            elif overtime <= 30:
                distribution["20-30h"] += 1
            else:
                distribution["30h+"] += 1

        total_overtime = sum(overtime_by_employee.values())
        employee_count = len([v for v in overtime_by_employee.values() if v > 0])

        return OvertimeAnalysis(
            total_overtime_hours=total_overtime,
            average_overtime_per_employee=total_overtime / employee_count
            if employee_count > 0
            else 0,
            overtime_distribution=distribution,
        )

    async def _calculate_trend_analysis(
        self, start_date: date, end_date: date
    ) -> TrendAnalysis:
        """トレンド分析を計算"""
        # 簡易版：前期間との比較
        period_days = (end_date - start_date).days + 1
        prev_start = start_date - timedelta(days=period_days)
        prev_end = start_date - timedelta(days=1)

        # 現期間の統計
        current_stats = await self._calculate_attendance_stats(start_date, end_date)
        current_overtime = await self._calculate_overtime_analysis(start_date, end_date)

        # 前期間の統計
        prev_stats = await self._calculate_attendance_stats(prev_start, prev_end)
        prev_overtime = await self._calculate_overtime_analysis(prev_start, prev_end)

        # トレンド判定
        work_hours_trend = "stable"
        if current_stats.average_work_hours > prev_stats.average_work_hours * 1.05:
            work_hours_trend = "increasing"
        elif current_stats.average_work_hours < prev_stats.average_work_hours * 0.95:
            work_hours_trend = "decreasing"

        overtime_trend = "stable"
        if (
            current_overtime.total_overtime_hours
            > prev_overtime.total_overtime_hours * 1.05
        ):
            overtime_trend = "increasing"
        elif (
            current_overtime.total_overtime_hours
            < prev_overtime.total_overtime_hours * 0.95
        ):
            overtime_trend = "decreasing"

        # 出勤率トレンド（簡易版）
        attendance_trend = "stable"

        return TrendAnalysis(
            work_hours_trend=work_hours_trend,
            overtime_trend=overtime_trend,
            attendance_trend=attendance_trend,
        )

    async def get_work_hours_trend(
        self, months: int = 6, employee_id: Optional[str] = None
    ) -> ChartDataResponse:
        """
        労働時間トレンドチャートデータを取得

        Args:
            months: 過去何ヶ月分
            employee_id: 従業員ID

        Returns:
            ChartDataResponse: チャートデータ
        """
        labels = []
        work_hours_data = []
        overtime_hours_data = []

        # 過去X月分のデータを集計
        today = date.today()
        for i in range(months - 1, -1, -1):
            # 対象月を計算
            target_date = today - timedelta(days=i * 30)
            year = target_date.year
            month = target_date.month

            # 月次レポートを生成
            employee_ids = [employee_id] if employee_id else None
            monthly_reports = await self.report_service.generate_monthly_reports(
                year, month, employee_ids
            )

            # 集計
            total_work_hours = sum(
                r.monthly_summary.total_work_hours for r in monthly_reports
            )
            total_overtime_hours = sum(
                r.monthly_summary.overtime_hours for r in monthly_reports
            )

            # 従業員数で平均化
            employee_count = len(monthly_reports) if monthly_reports else 1

            labels.append(f"{year}-{month:02d}")
            work_hours_data.append(total_work_hours / employee_count)
            overtime_hours_data.append(total_overtime_hours / employee_count)

        return ChartDataResponse(
            chart_type="line",
            data={
                "labels": labels,
                "datasets": [
                    {"label": "労働時間", "data": work_hours_data},
                    {"label": "残業時間", "data": overtime_hours_data},
                ],
            },
        )

    async def get_overtime_distribution(
        self, year: int, month: int
    ) -> ChartDataResponse:
        """
        残業時間分布チャートデータを取得

        Args:
            year: 年
            month: 月

        Returns:
            ChartDataResponse: チャートデータ
        """
        # 月次レポートを生成
        monthly_reports = await self.report_service.generate_monthly_reports(
            year, month
        )

        # 残業時間でグループ化
        distribution = {
            "0-10時間": 0,
            "10-20時間": 0,
            "20-30時間": 0,
            "30-40時間": 0,
            "40時間以上": 0,
        }

        for report in monthly_reports:
            overtime = report.monthly_summary.overtime_hours
            if overtime <= 10:
                distribution["0-10時間"] += 1
            elif overtime <= 20:
                distribution["10-20時間"] += 1
            elif overtime <= 30:
                distribution["20-30時間"] += 1
            elif overtime <= 40:
                distribution["30-40時間"] += 1
            else:
                distribution["40時間以上"] += 1

        return ChartDataResponse(
            chart_type="bar",
            data={
                "labels": list(distribution.keys()),
                "datasets": [{"label": "人数", "data": list(distribution.values())}],
            },
        )

    async def get_attendance_rate_trend(self, months: int = 6) -> ChartDataResponse:
        """
        出勤率トレンドチャートデータを取得

        Args:
            months: 過去何ヶ月分

        Returns:
            ChartDataResponse: チャートデータ
        """
        labels = []
        attendance_rates = []

        today = date.today()
        total_employees = (
            self.db.query(Employee).filter(Employee.is_active == True).count()
        )

        for i in range(months - 1, -1, -1):
            # 対象月を計算
            target_date = today - timedelta(days=i * 30)
            year = target_date.year
            month = target_date.month

            # 月の営業日数を計算
            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)

            work_days = 0
            current = first_day
            while current <= last_day:
                if current.weekday() < 5:  # 月〜金
                    work_days += 1
                current += timedelta(days=1)

            # 出勤者数を集計
            attendance_count = (
                self.db.query(func.count(func.distinct(PunchRecord.employee_id)))
                .filter(
                    and_(
                        PunchRecord.punch_time
                        >= datetime.combine(first_day, datetime.min.time()),
                        PunchRecord.punch_time
                        < datetime.combine(
                            last_day + timedelta(days=1), datetime.min.time()
                        ),
                        PunchRecord.punch_type == PunchType.IN.value,
                    )
                )
                .scalar()
                or 0
            )

            # 出勤率を計算
            expected_attendance = total_employees * work_days
            rate = (
                (attendance_count / expected_attendance * 100)
                if expected_attendance > 0
                else 0
            )

            labels.append(f"{year}-{month:02d}")
            attendance_rates.append(rate)

        return ChartDataResponse(
            chart_type="line",
            data={
                "labels": labels,
                "datasets": [{"label": "出勤率 (%)", "data": attendance_rates}],
            },
        )

    async def get_current_alerts(self) -> List[DashboardAlert]:
        """
        現在のアラートを取得

        Returns:
            List[DashboardAlert]: アラートリスト
        """
        alerts = []
        today = date.today()

        # 月間残業時間チェック
        monthly_reports = await self.report_service.generate_monthly_reports(
            today.year, today.month
        )

        for report in monthly_reports:
            # 月間残業時間アラート
            if (
                report.monthly_summary.overtime_hours
                >= self.alert_conditions["overtime_monthly"]
            ):
                alerts.append(
                    DashboardAlert(
                        type="overtime_alert",
                        employee_id=report.employee_id,
                        message=f"{report.employee_name}の月間残業時間が{report.monthly_summary.overtime_hours:.1f}時間です",
                        severity="warning"
                        if report.monthly_summary.overtime_hours < 60
                        else "error",
                    )
                )

            # 連続残業チェック
            consecutive_overtime = await self._check_consecutive_overtime(
                report.employee_id, self.alert_conditions["continuous_overtime"]
            )
            if consecutive_overtime:
                alerts.append(
                    DashboardAlert(
                        type="consecutive_overtime",
                        employee_id=report.employee_id,
                        message=f"{report.employee_name}が{consecutive_overtime}日連続で残業しています",
                        severity="warning",
                    )
                )

        # 本日の異常チェック
        daily_reports = await self.report_service.generate_daily_reports(today)

        for report in daily_reports:
            # 長時間残業アラート
            if (
                report.summary.overtime_minutes
                >= self.alert_conditions["overtime_daily"] * 60
            ):
                alerts.append(
                    DashboardAlert(
                        type="daily_overtime",
                        employee_id=report.employee_id,
                        message=f"{report.employee_name}の本日の残業が{report.summary.overtime_minutes / 60:.1f}時間です",
                        severity="warning",
                    )
                )

        return alerts

    async def _check_consecutive_overtime(
        self, employee_code: str, threshold_days: int
    ) -> Optional[int]:
        """
        連続残業日数をチェック

        Args:
            employee_code: 従業員コード
            threshold_days: 閾値日数

        Returns:
            Optional[int]: 連続残業日数（閾値以上の場合）
        """
        consecutive_days = 0
        current_date = date.today()

        for i in range(threshold_days + 2):  # 余裕を持ってチェック
            check_date = current_date - timedelta(days=i)
            daily_reports = await self.report_service.generate_daily_reports(
                check_date, [employee_code]
            )

            if daily_reports and daily_reports[0].summary.overtime_minutes > 0:
                consecutive_days += 1
            else:
                # 残業なしの日があれば連続記録リセット
                if consecutive_days >= threshold_days:
                    return consecutive_days
                consecutive_days = 0

        return consecutive_days if consecutive_days >= threshold_days else None

    async def get_realtime_summary(self) -> Dict[str, Any]:
        """
        リアルタイム勤怠状況サマリーを取得

        Returns:
            Dict[str, Any]: リアルタイムサマリー
        """
        now = datetime.now()
        today = now.date()

        # 現在勤務中の従業員
        working_employees = []

        # 全従業員の状態を確認
        employees = self.db.query(Employee).filter(Employee.is_active == True).all()

        for employee in employees:
            # 最新の打刻を取得
            latest_punch = (
                self.db.query(PunchRecord)
                .filter(
                    and_(
                        PunchRecord.employee_id == employee.id,
                        PunchRecord.punch_time
                        >= datetime.combine(today, datetime.min.time()),
                    )
                )
                .order_by(PunchRecord.punch_time.desc())
                .first()
            )

            if latest_punch:
                status = "unknown"
                if latest_punch.punch_type == PunchType.IN.value:
                    status = "working"
                elif latest_punch.punch_type == PunchType.OUTSIDE.value:
                    status = "break"
                elif latest_punch.punch_type == PunchType.RETURN.value:
                    status = "working"
                elif latest_punch.punch_type == PunchType.OUT.value:
                    status = "finished"

                if status in ["working", "break"]:
                    working_employees.append(
                        {
                            "employee_code": employee.employee_code,
                            "employee_name": employee.name,
                            "status": status,
                            "since": latest_punch.punch_time.isoformat(),
                        }
                    )

        return {
            "timestamp": now.isoformat(),
            "working_count": len(
                [e for e in working_employees if e["status"] == "working"]
            ),
            "break_count": len(
                [e for e in working_employees if e["status"] == "break"]
            ),
            "working_employees": working_employees,
        }
