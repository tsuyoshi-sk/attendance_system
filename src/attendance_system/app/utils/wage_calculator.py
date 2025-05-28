"""
賃金計算ユーティリティ

基本給、残業代、深夜手当などの賃金計算を行う
"""

from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any, Optional
from datetime import date

from backend.app.models import Employee, WageType
from config.config import config


class WageCalculator:
    """賃金計算クラス"""

    def __init__(self):
        self.overtime_rate_normal = Decimal("1.25")  # 通常残業割増率（125%）
        self.overtime_rate_heavy = Decimal("1.50")  # 法定超残業割増率（150%）
        self.night_rate = Decimal("1.25")  # 深夜労働割増率（125%）
        self.holiday_rate = Decimal("1.35")  # 休日労働割増率（135%）
        self.overtime_threshold = 60  # 月60時間超で割増率変更
        self.standard_monthly_hours = 160  # 月間標準労働時間

    def calculate_daily_wage(
        self,
        employee: Employee,
        work_minutes: int,
        overtime_minutes: int = 0,
        night_minutes: int = 0,
        holiday_minutes: int = 0,
    ) -> Dict[str, float]:
        """
        日次賃金を計算

        Args:
            employee: 従業員
            work_minutes: 労働時間（分）
            overtime_minutes: 残業時間（分）
            night_minutes: 深夜労働時間（分）
            holiday_minutes: 休日労働時間（分）

        Returns:
            Dict[str, float]: 賃金計算結果
        """
        # 時給を計算
        hourly_rate = self._calculate_hourly_rate(employee)

        # 通常労働時間（残業を除く）
        regular_minutes = work_minutes - overtime_minutes
        regular_hours = Decimal(regular_minutes) / 60

        # 各種時間を時間単位に変換
        overtime_hours = Decimal(overtime_minutes) / 60
        night_hours = Decimal(night_minutes) / 60
        holiday_hours = Decimal(holiday_minutes) / 60

        # 基本給
        basic_wage = hourly_rate * regular_hours

        # 残業代
        overtime_wage = hourly_rate * overtime_hours * self.overtime_rate_normal

        # 深夜手当
        night_wage = hourly_rate * night_hours * (self.night_rate - 1)

        # 休日手当
        holiday_wage = hourly_rate * holiday_hours * self.holiday_rate

        # 合計
        total_wage = basic_wage + overtime_wage + night_wage + holiday_wage

        return {
            "regular_hours": float(regular_hours),
            "overtime_hours": float(overtime_hours),
            "night_hours": float(night_hours),
            "basic_wage": float(
                basic_wage.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            ),
            "overtime_wage": float(
                overtime_wage.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            ),
            "night_wage": float(
                night_wage.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            ),
            "total_wage": float(
                total_wage.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            ),
        }

    def calculate_monthly_wage(
        self,
        employee: Employee,
        total_work_hours: float,
        total_overtime_hours: float,
        total_night_hours: float,
        total_holiday_hours: float,
        monthly_overtime_minutes: int = 0,
    ) -> Dict[str, float]:
        """
        月次賃金を計算

        Args:
            employee: 従業員
            total_work_hours: 総労働時間
            total_overtime_hours: 総残業時間
            total_night_hours: 総深夜労働時間
            total_holiday_hours: 総休日労働時間
            monthly_overtime_minutes: 月間残業時間（分）※60時間超判定用

        Returns:
            Dict[str, float]: 賃金計算結果
        """
        if employee.wage_type == WageType.MONTHLY:
            # 月給制の場合
            basic_wage = Decimal(str(employee.monthly_salary))
            hourly_rate = basic_wage / self.standard_monthly_hours
        else:
            # 時給制の場合
            hourly_rate = self._calculate_hourly_rate(employee)
            regular_hours = Decimal(str(total_work_hours - total_overtime_hours))
            basic_wage = hourly_rate * regular_hours

        # 残業代（60時間超は割増率変更）
        overtime_wage = self._calculate_overtime_with_threshold(
            hourly_rate, total_overtime_hours, monthly_overtime_minutes
        )

        # 深夜手当
        night_wage = (
            hourly_rate * Decimal(str(total_night_hours)) * (self.night_rate - 1)
        )

        # 休日手当
        holiday_wage = (
            hourly_rate * Decimal(str(total_holiday_hours)) * self.holiday_rate
        )

        # 総支給額
        total_wage = basic_wage + overtime_wage + night_wage + holiday_wage

        # 控除（簡易版）
        deductions = self._calculate_deductions(total_wage)

        # 手取り額
        net_wage = total_wage - deductions

        return {
            "basic_wage": float(basic_wage.quantize(Decimal("1"), rounding=ROUND_DOWN)),
            "overtime_wage": float(
                overtime_wage.quantize(Decimal("1"), rounding=ROUND_DOWN)
            ),
            "night_wage": float(night_wage.quantize(Decimal("1"), rounding=ROUND_DOWN)),
            "holiday_wage": float(
                holiday_wage.quantize(Decimal("1"), rounding=ROUND_DOWN)
            ),
            "total_wage": float(total_wage.quantize(Decimal("1"), rounding=ROUND_DOWN)),
            "deductions": float(deductions.quantize(Decimal("1"), rounding=ROUND_DOWN)),
            "net_wage": float(net_wage.quantize(Decimal("1"), rounding=ROUND_DOWN)),
        }

    def _calculate_hourly_rate(self, employee: Employee) -> Decimal:
        """
        時給を計算

        Args:
            employee: 従業員

        Returns:
            Decimal: 時給
        """
        if employee.wage_type == WageType.HOURLY:
            return Decimal(str(employee.hourly_rate))
        elif employee.wage_type == WageType.MONTHLY:
            # 月給を標準労働時間で割って時給換算
            return Decimal(str(employee.monthly_salary)) / self.standard_monthly_hours
        else:
            raise ValueError(f"未対応の賃金タイプ: {employee.wage_type}")

    def _calculate_overtime_with_threshold(
        self,
        hourly_rate: Decimal,
        total_overtime_hours: float,
        monthly_overtime_minutes: int,
    ) -> Decimal:
        """
        60時間超の割増率を考慮した残業代計算

        Args:
            hourly_rate: 時給
            total_overtime_hours: 総残業時間
            monthly_overtime_minutes: 月間残業時間（分）

        Returns:
            Decimal: 残業代
        """
        overtime_wage = Decimal("0")

        if monthly_overtime_minutes <= self.overtime_threshold * 60:
            # 60時間以内は通常の割増率
            overtime_wage = (
                hourly_rate
                * Decimal(str(total_overtime_hours))
                * self.overtime_rate_normal
            )
        else:
            # 60時間を超える場合
            normal_hours = Decimal(str(self.overtime_threshold))
            heavy_hours = Decimal(str(total_overtime_hours)) - normal_hours

            # 60時間までは1.25倍
            overtime_wage += hourly_rate * normal_hours * self.overtime_rate_normal

            # 60時間超は1.5倍
            if heavy_hours > 0:
                overtime_wage += hourly_rate * heavy_hours * self.overtime_rate_heavy

        return overtime_wage

    def _calculate_deductions(self, total_wage: Decimal) -> Decimal:
        """
        控除額を計算（簡易版）

        Args:
            total_wage: 総支給額

        Returns:
            Decimal: 控除額
        """
        # TODO: 実際の社会保険料、税金計算の実装
        # 簡易版として総支給額の20%を控除
        return total_wage * Decimal("0.20")

    def calculate_payroll_entry(
        self, employee: Employee, year: int, month: int, summary_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        給与計算用エントリーを生成

        Args:
            employee: 従業員
            year: 年
            month: 月
            summary_data: 月次集計データ

        Returns:
            Dict[str, Any]: 給与計算エントリー
        """
        return {
            "employee_code": employee.employee_code,
            "employee_name": employee.name,
            "year": year,
            "month": month,
            "wage_type": employee.wage_type.value,
            "work_days": summary_data.get("work_days", 0),
            "total_work_hours": summary_data.get("total_work_hours", 0),
            "overtime_hours": summary_data.get("overtime_hours", 0),
            "night_hours": summary_data.get("night_hours", 0),
            "holiday_hours": summary_data.get("holiday_hours", 0),
            "basic_wage": summary_data.get("basic_wage", 0),
            "overtime_wage": summary_data.get("overtime_wage", 0),
            "night_wage": summary_data.get("night_wage", 0),
            "holiday_wage": summary_data.get("holiday_wage", 0),
            "total_wage": summary_data.get("total_wage", 0),
            "deductions": summary_data.get("deductions", 0),
            "net_wage": summary_data.get("net_wage", 0),
        }
