"""
勤怠ドメインサービス

勤務時間計算、残業計算などのビジネスロジック
"""

from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PunchData:
    """打刻データ"""

    employee_id: int
    punch_type: str
    timestamp: datetime


@dataclass
class WorkSession:
    """勤務セッション"""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    break_start: Optional[datetime] = None
    break_end: Optional[datetime] = None


@dataclass
class WorkSummary:
    """勤務サマリー"""

    work_time: timedelta
    break_time: timedelta
    overtime_normal: timedelta
    overtime_late: timedelta
    night_time: timedelta
    is_complete: bool


class AttendanceService:
    """勤怠計算ドメインサービス"""

    def __init__(self):
        # 基本設定（設定ファイルから取得すべき）
        self.business_start = time(9, 0)
        self.business_end = time(18, 0)
        self.break_start = time(12, 0)
        self.break_end = time(13, 0)
        self.night_start = time(22, 0)
        self.night_end = time(5, 0)

        # 残業時間の境界
        self.overtime_threshold = timedelta(hours=8)
        self.late_overtime_threshold = timedelta(hours=10)

        # 丸め設定
        self.daily_round_minutes = 15
        self.monthly_round_minutes = 30

    def calculate_work_hours(self, punches: List[PunchData]) -> WorkSummary:
        """勤務時間計算のメインロジック"""

        # 打刻データから勤務セッションを構築
        session = self._build_work_session(punches)

        if not session.start_time or not session.end_time:
            return WorkSummary(
                work_time=timedelta(0),
                break_time=timedelta(0),
                overtime_normal=timedelta(0),
                overtime_late=timedelta(0),
                night_time=timedelta(0),
                is_complete=False,
            )

        # 総勤務時間計算
        total_time = session.end_time - session.start_time

        # 休憩時間計算
        break_time = self._calculate_break_time(session)

        # 実勤務時間
        work_time = total_time - break_time

        # 深夜時間計算
        night_time = self._calculate_night_time(session)

        # 残業時間計算
        overtime_normal, overtime_late = self._calculate_overtime(work_time)

        # 時間の丸め処理
        work_time = self._round_time(work_time, self.daily_round_minutes)
        overtime_normal = self._round_time(overtime_normal, self.daily_round_minutes)
        overtime_late = self._round_time(overtime_late, self.daily_round_minutes)

        return WorkSummary(
            work_time=work_time,
            break_time=break_time,
            overtime_normal=overtime_normal,
            overtime_late=overtime_late,
            night_time=night_time,
            is_complete=True,
        )

    def _build_work_session(self, punches: List[PunchData]) -> WorkSession:
        """打刻データから勤務セッションを構築"""
        session = WorkSession()

        # 打刻を時系列順にソート
        sorted_punches = sorted(punches, key=lambda p: p.timestamp)

        for punch in sorted_punches:
            if punch.punch_type == "in":
                session.start_time = punch.timestamp
            elif punch.punch_type == "out":
                session.end_time = punch.timestamp
            elif punch.punch_type == "out_break":
                session.break_start = punch.timestamp
            elif punch.punch_type == "in_break":
                session.break_end = punch.timestamp

        return session

    def _calculate_break_time(self, session: WorkSession) -> timedelta:
        """休憩時間計算"""
        if session.break_start and session.break_end:
            return session.break_end - session.break_start

        # 明示的な休憩打刻がない場合、標準休憩時間を適用
        if session.start_time and session.end_time:
            work_hours = (session.end_time - session.start_time).total_seconds() / 3600
            if work_hours >= 6:  # 6時間以上勤務の場合は1時間休憩
                return timedelta(hours=1)

        return timedelta(0)

    def _calculate_night_time(self, session: WorkSession) -> timedelta:
        """深夜時間計算（22:00-5:00）"""
        if not session.start_time or not session.end_time:
            return timedelta(0)

        night_time = timedelta(0)
        current = session.start_time

        while current < session.end_time:
            # 1時間単位で処理
            next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(
                hours=1
            )
            segment_end = min(next_hour, session.end_time)

            # この時間帯が深夜時間かチェック
            hour = current.hour
            if hour >= 22 or hour < 5:
                night_time += segment_end - current

            current = segment_end

        return night_time

    def _calculate_overtime(self, work_time: timedelta) -> Tuple[timedelta, timedelta]:
        """残業時間計算"""
        if work_time <= self.overtime_threshold:
            return timedelta(0), timedelta(0)

        total_overtime = work_time - self.overtime_threshold

        if total_overtime <= timedelta(hours=2):  # 2時間まで通常残業
            return total_overtime, timedelta(0)
        else:
            return timedelta(hours=2), total_overtime - timedelta(hours=2)

    def _round_time(self, time_delta: timedelta, round_minutes: int) -> timedelta:
        """時間の丸め処理"""
        total_minutes = int(time_delta.total_seconds() / 60)
        rounded_minutes = (
            (total_minutes + round_minutes // 2) // round_minutes
        ) * round_minutes
        return timedelta(minutes=rounded_minutes)

    def calculate_monthly_summary(self, daily_summaries: List[WorkSummary]) -> Dict:
        """月次サマリー計算"""
        total_work_time = sum(
            (summary.work_time for summary in daily_summaries), timedelta(0)
        )

        total_overtime_normal = sum(
            (summary.overtime_normal for summary in daily_summaries), timedelta(0)
        )

        total_overtime_late = sum(
            (summary.overtime_late for summary in daily_summaries), timedelta(0)
        )

        total_night_time = sum(
            (summary.night_time for summary in daily_summaries), timedelta(0)
        )

        # 月次丸め処理
        total_work_time = self._round_time(total_work_time, self.monthly_round_minutes)

        return {
            "total_work_time": total_work_time,
            "total_overtime_normal": total_overtime_normal,
            "total_overtime_late": total_overtime_late,
            "total_night_time": total_night_time,
            "work_days": len([s for s in daily_summaries if s.is_complete]),
            "average_daily_hours": total_work_time / max(len(daily_summaries), 1),
        }
