"""
時間計算ユーティリティ

勤怠時間の計算、丸め処理、深夜時間の判定などを行う
"""

from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Tuple, Optional
from backend.app.models import PunchRecord, PunchType
from config.config import config


class TimeCalculator:
    """時間計算クラス"""

    def __init__(self):
        self.night_start = time(22, 0)  # 22:00
        self.night_end = time(5, 0)  # 05:00
        self.standard_work_hours = 8  # 標準労働時間

    def calculate_daily_hours(self, punches: List[PunchRecord]) -> Dict[str, int]:
        """
        日次の労働時間を計算

        Args:
            punches: 打刻記録リスト

        Returns:
            Dict[str, int]: 各種時間（分単位）
        """
        result = {
            "work_minutes": 0,
            "overtime_minutes": 0,
            "night_minutes": 0,
            "outside_minutes": 0,
            "break_minutes": 0,
            "actual_work_minutes": 0,
        }

        if not punches:
            return result

        # 出退勤時刻を特定
        clock_in = None
        clock_out = None
        breaks = []

        for punch in punches:
            if punch.punch_type == PunchType.IN.value and not clock_in:
                clock_in = punch
            elif punch.punch_type == PunchType.OUT.value:
                clock_out = punch
            elif punch.punch_type == PunchType.OUTSIDE.value:
                breaks.append({"start": punch, "end": None})
            elif punch.punch_type == PunchType.RETURN.value and breaks:
                for break_period in reversed(breaks):
                    if break_period["end"] is None:
                        break_period["end"] = punch
                        break

        if not clock_in:
            return result

        # 勤務終了時刻（退勤打刻がない場合は現在時刻）
        end_time = clock_out.punch_time if clock_out else datetime.now()

        # 総労働時間
        work_duration = end_time - clock_in.punch_time
        result["work_minutes"] = int(work_duration.total_seconds() / 60)

        # 休憩時間を計算
        for break_period in breaks:
            if break_period["start"] and break_period["end"]:
                break_duration = (
                    break_period["end"].punch_time - break_period["start"].punch_time
                )
                result["break_minutes"] += int(break_duration.total_seconds() / 60)
            elif break_period["start"] and not break_period["end"]:
                # 未完了の外出は現在時刻まで
                break_duration = datetime.now() - break_period["start"].punch_time
                result["outside_minutes"] += int(break_duration.total_seconds() / 60)

        # 実労働時間
        result["actual_work_minutes"] = result["work_minutes"] - result["break_minutes"]

        # 深夜労働時間を計算
        result["night_minutes"] = self._calculate_night_minutes(
            clock_in.punch_time, end_time, breaks
        )

        # 残業時間（8時間超過分）
        standard_minutes = self.standard_work_hours * 60
        if result["actual_work_minutes"] > standard_minutes:
            result["overtime_minutes"] = (
                result["actual_work_minutes"] - standard_minutes
            )

        # 日次丸め処理
        result["actual_work_minutes"] = self.round_daily_minutes(
            result["actual_work_minutes"]
        )
        result["overtime_minutes"] = self.round_daily_minutes(
            result["overtime_minutes"]
        )

        return result

    def _calculate_night_minutes(
        self, start: datetime, end: datetime, breaks: List[Dict[str, Any]]
    ) -> int:
        """
        深夜労働時間を計算

        Args:
            start: 開始時刻
            end: 終了時刻
            breaks: 休憩リスト

        Returns:
            int: 深夜労働時間（分）
        """
        night_minutes = 0
        current = start

        while current < end:
            next_day = current.date() + timedelta(days=1)

            # 当日の深夜時間帯（22:00-24:00）
            night_start_today = datetime.combine(current.date(), self.night_start)
            night_end_today = datetime.combine(next_day, time(0, 0))

            # 翌日の深夜時間帯（00:00-05:00）
            night_start_tomorrow = datetime.combine(next_day, time(0, 0))
            night_end_tomorrow = datetime.combine(next_day, self.night_end)

            # 当日の深夜労働
            if current < night_end_today:
                overlap_start = max(current, night_start_today)
                overlap_end = min(end, night_end_today)
                if overlap_start < overlap_end:
                    duration = overlap_end - overlap_start
                    night_minutes += int(duration.total_seconds() / 60)

            # 翌日早朝の深夜労働
            if end > night_start_tomorrow:
                overlap_start = max(current, night_start_tomorrow)
                overlap_end = min(end, night_end_tomorrow)
                if overlap_start < overlap_end:
                    duration = overlap_end - overlap_start
                    night_minutes += int(duration.total_seconds() / 60)

            current = night_end_tomorrow

        # 休憩時間を除外
        for break_period in breaks:
            if break_period["start"] and break_period["end"]:
                break_night = self._calculate_night_minutes(
                    break_period["start"].punch_time, break_period["end"].punch_time, []
                )
                night_minutes -= break_night

        return max(0, night_minutes)

    def round_daily_minutes(self, minutes: int) -> int:
        """
        日次時間を15分単位で四捨五入

        Args:
            minutes: 分数

        Returns:
            int: 丸めた分数
        """
        return round(minutes / 15) * 15

    def round_monthly_overtime(self, minutes: int) -> int:
        """
        月次残業時間を30分単位で丸め（30分未満切捨て、30分以上切上げ）

        Args:
            minutes: 分数

        Returns:
            int: 丸めた分数
        """
        hours = minutes // 60
        remainder = minutes % 60

        if remainder < 30:
            return hours * 60
        else:
            return (hours + 1) * 60

    def is_holiday(self, target_date: date) -> bool:
        """
        休日判定（簡易版：土日のみ）

        Args:
            target_date: 判定対象日

        Returns:
            bool: 休日の場合True
        """
        # TODO: 祝日カレンダーの実装
        return target_date.weekday() in [5, 6]  # 土日

    def calculate_scheduled_hours(self, target_date: date) -> int:
        """
        所定労働時間を計算

        Args:
            target_date: 対象日

        Returns:
            int: 所定労働時間（分）
        """
        if self.is_holiday(target_date):
            return 0

        # 通常は8時間
        return self.standard_work_hours * 60

    def calculate_late_minutes(
        self, scheduled_start: time, actual_start: datetime
    ) -> int:
        """
        遅刻時間を計算

        Args:
            scheduled_start: 始業時刻
            actual_start: 実際の出勤時刻

        Returns:
            int: 遅刻時間（分）
        """
        scheduled = datetime.combine(actual_start.date(), scheduled_start)
        if actual_start > scheduled:
            late_duration = actual_start - scheduled
            return int(late_duration.total_seconds() / 60)
        return 0

    def calculate_early_leave_minutes(
        self, scheduled_end: time, actual_end: datetime
    ) -> int:
        """
        早退時間を計算

        Args:
            scheduled_end: 終業時刻
            actual_end: 実際の退勤時刻

        Returns:
            int: 早退時間（分）
        """
        scheduled = datetime.combine(actual_end.date(), scheduled_end)
        if actual_end < scheduled:
            early_duration = scheduled - actual_end
            return int(early_duration.total_seconds() / 60)
        return 0
