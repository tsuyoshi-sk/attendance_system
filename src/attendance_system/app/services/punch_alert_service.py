"""
打刻アラートサービス

打刻漏れや異常をリアルタイムで検知し、通知を送信します。
"""

import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging
import json

from backend.app.models.punch_record import PunchRecord, PunchType
from backend.app.models.employee import Employee
from backend.app.services.notification_service import NotificationService
from backend.app.services.punch_anomaly_service import PunchAnomalyDetector

logger = logging.getLogger(__name__)


class PunchAlertService:
    """打刻アラートサービス"""

    ALERT_RULES = {
        "MISSING_IN": {
            "delay_minutes": 30,
            "severity": "HIGH",
            "channels": ["slack", "email"],
            "message_template": "{employee_name}さんの出勤打刻がありません（予定時刻から{delay}分経過）",
        },
        "MISSING_OUT": {
            "delay_minutes": 60,
            "severity": "MEDIUM",
            "channels": ["slack"],
            "message_template": "{employee_name}さんの退勤打刻がありません（予定時刻から{delay}分経過）",
        },
        "MISSING_RETURN": {
            "delay_minutes": 120,
            "severity": "LOW",
            "channels": ["slack"],
            "message_template": "{employee_name}さんが外出から{delay}分戻っていません",
        },
        "ANOMALY_DETECTED": {
            "severity": "VARIABLE",  # 異常の種類による
            "channels": ["slack", "system"],
            "message_template": "{employee_name}さんの打刻に異常を検知: {anomaly_type}",
        },
        "DEVICE_ERROR": {
            "severity": "CRITICAL",
            "channels": ["slack", "email", "system"],
            "message_template": "打刻デバイスエラー: {device_id} - {error_message}",
        },
        "CONSECUTIVE_MISSING": {
            "threshold_days": 2,
            "severity": "HIGH",
            "channels": ["slack", "email"],
            "message_template": "{employee_name}さんが{days}日連続で打刻していません",
        },
    }

    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService()
        self.anomaly_detector = PunchAnomalyDetector(db)
        self._monitoring_task = None
        self._alert_cache: Dict[str, datetime] = {}  # 重複アラート防止用
        self._monitored_employees: Set[int] = set()  # 監視対象従業員

    async def start_monitoring(self):
        """監視を開始"""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._continuous_monitoring())
            logger.info("Punch alert monitoring started")

    async def stop_monitoring(self):
        """監視を停止"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Punch alert monitoring stopped")

    async def _continuous_monitoring(self):
        """継続的な監視ループ"""
        while True:
            try:
                await self.monitor_missing_punches()
                await asyncio.sleep(300)  # 5分間隔でチェック
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {str(e)}")
                await asyncio.sleep(60)  # エラー時は1分後に再試行

    async def monitor_missing_punches(self):
        """打刻漏れ監視"""
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute

        # 勤務中の従業員を取得
        active_employees = (
            self.db.query(Employee).filter(Employee.is_active == True).all()
        )

        for employee in active_employees:
            # 出勤チェック（平日9:30以降）
            if self._is_weekday() and current_hour >= 9 and current_minute >= 30:
                await self._check_missing_in(employee, current_time)

            # 退勤チェック（平日19:00以降）
            if self._is_weekday() and current_hour >= 19:
                await self._check_missing_out(employee, current_time)

            # 外出戻りチェック
            await self._check_missing_return(employee, current_time)

            # 連続欠勤チェック
            await self._check_consecutive_missing(employee, current_time)

    async def _check_missing_in(self, employee: Employee, current_time: datetime):
        """出勤打刻漏れチェック"""
        work_date = current_time.date()

        # 本日の出勤打刻を確認
        in_punch = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee.id,
                    PunchRecord.punch_type == PunchType.IN,
                    func.date(PunchRecord.punch_time) == work_date,
                )
            )
            .first()
        )

        if not in_punch:
            # 出勤予定時刻を取得（デフォルト9:00）
            scheduled_in_time = datetime.combine(work_date, time(9, 0))
            delay_minutes = int((current_time - scheduled_in_time).total_seconds() / 60)

            if delay_minutes >= self.ALERT_RULES["MISSING_IN"]["delay_minutes"]:
                alert_key = f"missing_in_{employee.id}_{work_date}"

                if not self._is_alert_sent(alert_key):
                    await self._send_alert(
                        alert_type="MISSING_IN",
                        employee=employee,
                        context={
                            "delay": delay_minutes,
                            "scheduled_time": scheduled_in_time.isoformat(),
                        },
                    )
                    self._mark_alert_sent(alert_key)

    async def _check_missing_out(self, employee: Employee, current_time: datetime):
        """退勤打刻漏れチェック"""
        work_date = current_time.date()

        # 本日の出勤打刻があるか確認
        in_punch = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee.id,
                    PunchRecord.punch_type == PunchType.IN,
                    func.date(PunchRecord.punch_time) == work_date,
                )
            )
            .first()
        )

        if not in_punch:
            return  # 出勤していない場合はスキップ

        # 退勤打刻を確認
        out_punch = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee.id,
                    PunchRecord.punch_type == PunchType.OUT,
                    func.date(PunchRecord.punch_time) == work_date,
                )
            )
            .first()
        )

        if not out_punch:
            # 退勤予定時刻を取得（デフォルト18:00）
            scheduled_out_time = datetime.combine(work_date, time(18, 0))
            delay_minutes = int(
                (current_time - scheduled_out_time).total_seconds() / 60
            )

            if delay_minutes >= self.ALERT_RULES["MISSING_OUT"]["delay_minutes"]:
                alert_key = f"missing_out_{employee.id}_{work_date}"

                if not self._is_alert_sent(alert_key):
                    await self._send_alert(
                        alert_type="MISSING_OUT",
                        employee=employee,
                        context={
                            "delay": delay_minutes,
                            "in_time": in_punch.punch_time.isoformat(),
                            "scheduled_time": scheduled_out_time.isoformat(),
                        },
                    )
                    self._mark_alert_sent(alert_key)

    async def _check_missing_return(self, employee: Employee, current_time: datetime):
        """戻り打刻漏れチェック"""
        # 本日の外出打刻を取得
        today_outside = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee.id,
                    PunchRecord.punch_type == PunchType.OUTSIDE,
                    func.date(PunchRecord.punch_time) == current_time.date(),
                )
            )
            .order_by(PunchRecord.punch_time.desc())
            .all()
        )

        for outside_punch in today_outside:
            # 対応する戻り打刻があるか確認
            return_punch = (
                self.db.query(PunchRecord)
                .filter(
                    and_(
                        PunchRecord.employee_id == employee.id,
                        PunchRecord.punch_type == PunchType.RETURN,
                        PunchRecord.punch_time > outside_punch.punch_time,
                        func.date(PunchRecord.punch_time) == current_time.date(),
                    )
                )
                .first()
            )

            if not return_punch:
                delay_minutes = int(
                    (current_time - outside_punch.punch_time).total_seconds() / 60
                )

                if delay_minutes >= self.ALERT_RULES["MISSING_RETURN"]["delay_minutes"]:
                    alert_key = f"missing_return_{employee.id}_{outside_punch.id}"

                    if not self._is_alert_sent(alert_key):
                        await self._send_alert(
                            alert_type="MISSING_RETURN",
                            employee=employee,
                            context={
                                "delay": delay_minutes,
                                "outside_time": outside_punch.punch_time.isoformat(),
                            },
                        )
                        self._mark_alert_sent(alert_key)

    async def _check_consecutive_missing(
        self, employee: Employee, current_time: datetime
    ):
        """連続欠勤チェック"""
        threshold_days = self.ALERT_RULES["CONSECUTIVE_MISSING"]["threshold_days"]

        # 過去数日間の出勤記録を確認
        missing_days = 0
        for i in range(threshold_days):
            check_date = current_time.date() - timedelta(days=i)

            if not self._is_weekday(check_date):
                continue

            punch_exists = (
                self.db.query(PunchRecord)
                .filter(
                    and_(
                        PunchRecord.employee_id == employee.id,
                        PunchRecord.punch_type == PunchType.IN,
                        func.date(PunchRecord.punch_time) == check_date,
                    )
                )
                .first()
            )

            if not punch_exists:
                missing_days += 1

        if missing_days >= threshold_days:
            alert_key = f"consecutive_missing_{employee.id}_{current_time.date()}"

            if not self._is_alert_sent(alert_key):
                await self._send_alert(
                    alert_type="CONSECUTIVE_MISSING",
                    employee=employee,
                    context={"days": missing_days},
                )
                self._mark_alert_sent(alert_key)

    async def send_real_time_alert(self, alert_data: Dict[str, any]):
        """
        リアルタイムアラート送信

        Args:
            alert_data: アラートデータ
        """
        alert_type = alert_data.get("type", "UNKNOWN")
        severity = alert_data.get("severity", "MEDIUM")

        # 重要度に応じて通知チャネルを選択
        channels = []
        if severity == "CRITICAL":
            channels = ["slack", "email", "system"]
        elif severity == "HIGH":
            channels = ["slack", "email"]
        elif severity == "MEDIUM":
            channels = ["slack"]
        else:
            channels = ["system"]

        # 各チャネルに通知
        for channel in channels:
            try:
                if channel == "slack":
                    await self.notification_service.send_slack_notification(
                        message=alert_data.get("message", "Alert"), channel="#alerts"
                    )
                elif channel == "email":
                    # Email通知の実装
                    pass
                elif channel == "system":
                    logger.warning(f"System alert: {json.dumps(alert_data)}")
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {str(e)}")

    async def generate_daily_missing_report(self) -> Dict[str, any]:
        """
        日次打刻漏れレポート生成

        Returns:
            レポートデータ
        """
        today = datetime.now().date()
        report_data = {
            "date": today.isoformat(),
            "missing_in": [],
            "missing_out": [],
            "missing_return": [],
            "anomalies": [],
            "summary": {},
        }

        # 全アクティブ従業員をチェック
        active_employees = (
            self.db.query(Employee).filter(Employee.is_active == True).all()
        )

        for employee in active_employees:
            # 出勤打刻確認
            in_punch = (
                self.db.query(PunchRecord)
                .filter(
                    and_(
                        PunchRecord.employee_id == employee.id,
                        PunchRecord.punch_type == PunchType.IN,
                        func.date(PunchRecord.punch_time) == today,
                    )
                )
                .first()
            )

            if not in_punch:
                report_data["missing_in"].append(
                    {
                        "employee_id": employee.id,
                        "employee_name": employee.name,
                        "department": employee.department,
                    }
                )
            else:
                # 退勤打刻確認
                out_punch = (
                    self.db.query(PunchRecord)
                    .filter(
                        and_(
                            PunchRecord.employee_id == employee.id,
                            PunchRecord.punch_type == PunchType.OUT,
                            func.date(PunchRecord.punch_time) == today,
                        )
                    )
                    .first()
                )

                if not out_punch:
                    report_data["missing_out"].append(
                        {
                            "employee_id": employee.id,
                            "employee_name": employee.name,
                            "in_time": in_punch.punch_time.isoformat(),
                        }
                    )

            # 外出・戻りのペアチェック
            outside_punches = (
                self.db.query(PunchRecord)
                .filter(
                    and_(
                        PunchRecord.employee_id == employee.id,
                        PunchRecord.punch_type == PunchType.OUTSIDE,
                        func.date(PunchRecord.punch_time) == today,
                    )
                )
                .all()
            )

            for outside in outside_punches:
                return_punch = (
                    self.db.query(PunchRecord)
                    .filter(
                        and_(
                            PunchRecord.employee_id == employee.id,
                            PunchRecord.punch_type == PunchType.RETURN,
                            PunchRecord.punch_time > outside.punch_time,
                            func.date(PunchRecord.punch_time) == today,
                        )
                    )
                    .first()
                )

                if not return_punch:
                    report_data["missing_return"].append(
                        {
                            "employee_id": employee.id,
                            "employee_name": employee.name,
                            "outside_time": outside.punch_time.isoformat(),
                        }
                    )

        # サマリー作成
        report_data["summary"] = {
            "total_employees": len(active_employees),
            "missing_in_count": len(report_data["missing_in"]),
            "missing_out_count": len(report_data["missing_out"]),
            "missing_return_count": len(report_data["missing_return"]),
            "completion_rate": (
                1 - (len(report_data["missing_in"]) / len(active_employees))
            )
            if active_employees
            else 0,
        }

        # 管理者に送信
        if report_data["missing_in"] or report_data["missing_out"]:
            await self._send_daily_report_notification(report_data)

        return report_data

    async def _send_alert(
        self, alert_type: str, employee: Employee, context: Dict[str, any]
    ):
        """アラート送信"""
        rule = self.ALERT_RULES.get(alert_type, {})

        # メッセージ作成
        message = rule.get("message_template", "").format(
            employee_name=employee.name, **context
        )

        alert_data = {
            "type": alert_type,
            "severity": rule.get("severity", "MEDIUM"),
            "employee_id": employee.id,
            "employee_name": employee.name,
            "message": message,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }

        # 通知送信
        await self.send_real_time_alert(alert_data)

        # ログ記録
        logger.info(f"Alert sent: {alert_type} for employee {employee.id}")

    async def _send_daily_report_notification(self, report_data: Dict[str, any]):
        """日次レポート通知送信"""
        summary = report_data["summary"]

        message = f"""
📊 本日の打刻状況レポート（{report_data['date']}）

・総従業員数: {summary['total_employees']}名
・出勤打刻漏れ: {summary['missing_in_count']}名
・退勤打刻漏れ: {summary['missing_out_count']}名
・戻り打刻漏れ: {summary['missing_return_count']}名
・完了率: {summary['completion_rate']:.1%}

詳細はシステムで確認してください。
        """

        await self.notification_service.send_slack_notification(
            message=message.strip(), channel="#attendance-reports"
        )

    def _is_weekday(self, date: Optional[datetime.date] = None) -> bool:
        """平日かどうかを判定"""
        if date is None:
            date = datetime.now().date()
        return date.weekday() < 5  # 月曜日(0)～金曜日(4)

    def _is_alert_sent(self, alert_key: str) -> bool:
        """アラートが送信済みかチェック"""
        if alert_key in self._alert_cache:
            # 24時間以内に送信済みの場合はTrue
            if datetime.now() - self._alert_cache[alert_key] < timedelta(hours=24):
                return True
        return False

    def _mark_alert_sent(self, alert_key: str):
        """アラート送信済みマーク"""
        self._alert_cache[alert_key] = datetime.now()

        # 古いキャッシュをクリーンアップ
        cutoff_time = datetime.now() - timedelta(hours=48)
        self._alert_cache = {
            k: v for k, v in self._alert_cache.items() if v > cutoff_time
        }
