"""
レポートサービス

勤怠レポートの生成とエクスポート機能を実装します。
"""

import csv
import io
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from decimal import Decimal

from backend.app.models import Employee, PunchRecord, DailySummary, MonthlySummary, PunchType, WageType
from backend.app.schemas.report import (
    DailyReportResponse, MonthlyReportResponse,
    PunchRecordResponse, DailySummaryData, DailyCalculations,
    MonthlySummaryData, MonthlyWageCalculation
)
from backend.app.utils.time_calculator import TimeCalculator
from backend.app.utils.wage_calculator import WageCalculator
from config.config import config


class ReportService:
    """レポート生成サービス"""
    
    def __init__(self, db: Session):
        self.db = db
        self.time_calculator = TimeCalculator()
        self.wage_calculator = WageCalculator()
    
    async def generate_daily_reports(
        self,
        target_date: date,
        employee_ids: Optional[List[str]] = None
    ) -> List[DailyReportResponse]:
        """
        日次レポートを生成
        
        Args:
            target_date: 対象日
            employee_ids: 従業員IDリスト（省略時は全員）
        
        Returns:
            List[DailyReportResponse]: 日次レポートリスト
        """
        query = self.db.query(Employee).filter(Employee.is_active == True)
        if employee_ids:
            query = query.filter(Employee.employee_code.in_(employee_ids))
        employees = query.all()
        
        reports = []
        for employee in employees:
            report = await self._generate_employee_daily_report(employee, target_date)
            reports.append(report)
        
        return reports
    
    async def _generate_employee_daily_report(
        self,
        employee: Employee,
        target_date: date
    ) -> DailyReportResponse:
        """
        従業員の日次レポートを生成
        
        Args:
            employee: 従業員
            target_date: 対象日
        
        Returns:
            DailyReportResponse: 日次レポート
        """
        # 打刻記録を取得
        punches = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == employee.id,
                PunchRecord.punch_time >= datetime.combine(target_date, datetime.min.time()),
                PunchRecord.punch_time < datetime.combine(target_date + timedelta(days=1), datetime.min.time())
            )
        ).order_by(PunchRecord.punch_time).all()
        
        # 打刻記録をレスポンス形式に変換
        punch_records = [
            PunchRecordResponse(
                punch_type=punch.punch_type,
                timestamp=punch.punch_time,
                processed=True
            )
            for punch in punches
        ]
        
        # 時間計算
        time_summary = self.time_calculator.calculate_daily_hours(punches)
        
        # 賃金計算
        wage_calculation = self.wage_calculator.calculate_daily_wage(
            employee=employee,
            work_minutes=time_summary["actual_work_minutes"],
            overtime_minutes=time_summary["overtime_minutes"],
            night_minutes=time_summary["night_minutes"]
        )
        
        # 集計データ
        summary = DailySummaryData(
            work_minutes=time_summary["work_minutes"],
            overtime_minutes=time_summary["overtime_minutes"],
            night_minutes=time_summary["night_minutes"],
            outside_minutes=time_summary["outside_minutes"],
            break_minutes=time_summary["break_minutes"],
            actual_work_minutes=time_summary["actual_work_minutes"]
        )
        
        # 計算結果
        calculations = DailyCalculations(
            regular_hours=wage_calculation["regular_hours"],
            overtime_hours=wage_calculation["overtime_hours"],
            night_hours=wage_calculation["night_hours"],
            basic_wage=wage_calculation["basic_wage"],
            overtime_wage=wage_calculation["overtime_wage"],
            night_wage=wage_calculation["night_wage"],
            total_wage=wage_calculation["total_wage"]
        )
        
        return DailyReportResponse(
            date=target_date,
            employee_id=employee.employee_code,
            employee_name=employee.name,
            punch_records=punch_records,
            summary=summary,
            calculations=calculations
        )
    
    async def generate_monthly_reports(
        self,
        year: int,
        month: int,
        employee_ids: Optional[List[str]] = None
    ) -> List[MonthlyReportResponse]:
        """
        月次レポートを生成
        
        Args:
            year: 年
            month: 月
            employee_ids: 従業員IDリスト（省略時は全員）
        
        Returns:
            List[MonthlyReportResponse]: 月次レポートリスト
        """
        query = self.db.query(Employee).filter(Employee.is_active == True)
        if employee_ids:
            query = query.filter(Employee.employee_code.in_(employee_ids))
        employees = query.all()
        
        reports = []
        for employee in employees:
            report = await self._generate_employee_monthly_report(employee, year, month)
            reports.append(report)
        
        return reports
    
    async def _generate_employee_monthly_report(
        self,
        employee: Employee,
        year: int,
        month: int
    ) -> MonthlyReportResponse:
        """
        従業員の月次レポートを生成
        
        Args:
            employee: 従業員
            year: 年
            month: 月
        
        Returns:
            MonthlyReportResponse: 月次レポート
        """
        # 月の開始日と終了日
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        # 日次レポートを集計
        daily_reports = []
        total_work_minutes = 0
        total_overtime_minutes = 0
        total_night_minutes = 0
        total_basic_wage = 0
        total_overtime_wage = 0
        total_night_wage = 0
        work_days = 0
        
        current_date = first_day
        while current_date <= last_day:
            daily_report = await self._generate_employee_daily_report(employee, current_date)
            daily_reports.append(daily_report)
            
            if daily_report.summary.actual_work_minutes > 0:
                work_days += 1
                total_work_minutes += daily_report.summary.actual_work_minutes
                total_overtime_minutes += daily_report.summary.overtime_minutes
                total_night_minutes += daily_report.summary.night_minutes
                total_basic_wage += daily_report.calculations.basic_wage
                total_overtime_wage += daily_report.calculations.overtime_wage
                total_night_wage += daily_report.calculations.night_wage
            
            current_date += timedelta(days=1)
        
        # 月次集計データ
        monthly_summary = MonthlySummaryData(
            work_days=work_days,
            total_work_hours=total_work_minutes / 60.0,
            regular_hours=(total_work_minutes - total_overtime_minutes) / 60.0,
            overtime_hours=self.time_calculator.round_monthly_overtime(total_overtime_minutes) / 60.0,
            night_hours=total_night_minutes / 60.0,
            holiday_hours=0.0  # TODO: 休日労働時間の計算
        )
        
        # 月次賃金計算
        wage_calculation = MonthlyWageCalculation(
            basic_wage=total_basic_wage,
            overtime_wage=total_overtime_wage,
            night_wage=total_night_wage,
            holiday_wage=0.0,  # TODO: 休日手当の計算
            total_wage=total_basic_wage + total_overtime_wage + total_night_wage,
            deductions=0.0,  # TODO: 控除額の計算
            net_wage=total_basic_wage + total_overtime_wage + total_night_wage
        )
        
        return MonthlyReportResponse(
            year=year,
            month=month,
            employee_id=employee.employee_code,
            employee_name=employee.name,
            monthly_summary=monthly_summary,
            wage_calculation=wage_calculation,
            daily_breakdown=daily_reports
        )
    
    async def generate_daily_summary(
        self,
        target_date: date,
        employee_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        日次勤怠集計を生成
        
        Args:
            target_date: 対象日
            employee_id: 従業員ID（指定時は該当従業員のみ）
        
        Returns:
            List[Dict[str, Any]]: 集計結果リスト
        """
        # 対象従業員を取得
        query = self.db.query(Employee).filter(Employee.is_active == True)
        if employee_id:
            query = query.filter(Employee.id == employee_id)
        employees = query.all()
        
        summaries = []
        for employee in employees:
            summary = await self._calculate_daily_summary(employee.id, target_date)
            summaries.append(summary)
        
        return summaries
    
    async def _calculate_daily_summary(
        self,
        employee_id: int,
        target_date: date
    ) -> Dict[str, Any]:
        """
        個人の日次集計を計算
        
        Args:
            employee_id: 従業員ID
            target_date: 対象日
        
        Returns:
            Dict[str, Any]: 集計結果
        """
        # 対象日の打刻記録を取得
        punches = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= datetime.combine(target_date, datetime.min.time()),
                PunchRecord.punch_time < datetime.combine(target_date + timedelta(days=1), datetime.min.time())
            )
        ).order_by(PunchRecord.punch_time).all()
        
        # 基本情報
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        summary = {
            "employee_id": employee_id,
            "employee_name": employee.name,
            "employee_code": employee.employee_code,
            "work_date": target_date.isoformat(),
            "clock_in_time": None,
            "clock_out_time": None,
            "break_minutes": 0,
            "work_minutes": 0,
            "actual_work_minutes": 0,
            "overtime_minutes": 0,
            "status": "欠勤"
        }
        
        if not punches:
            return summary
        
        # 出退勤時刻の特定
        clock_in = None
        clock_out = None
        breaks = []
        
        for punch in punches:
            if punch.punch_type == PunchType.CLOCK_IN.value and not clock_in:
                clock_in = punch
            elif punch.punch_type == PunchType.CLOCK_OUT.value:
                clock_out = punch
            elif punch.punch_type == PunchType.BREAK_START.value:
                breaks.append({"start": punch, "end": None})
            elif punch.punch_type == PunchType.BREAK_END.value and breaks:
                # 最後の未完了の外出に対応する戻り
                for break_period in reversed(breaks):
                    if break_period["end"] is None:
                        break_period["end"] = punch
                        break
        
        # 出勤時刻・退勤時刻
        if clock_in:
            summary["clock_in_time"] = clock_in.punch_time.time().isoformat()
            summary["status"] = "勤務中"
        
        if clock_out:
            summary["clock_out_time"] = clock_out.punch_time.time().isoformat()
            summary["status"] = "退勤済"
        
        # 勤務時間計算
        if clock_in and clock_out:
            work_duration = clock_out.punch_time - clock_in.punch_time
            summary["work_minutes"] = int(work_duration.total_seconds() / 60)
            
            # 休憩時間計算
            break_minutes = 0
            for break_period in breaks:
                if break_period["start"] and break_period["end"]:
                    break_duration = break_period["end"].punch_time - break_period["start"].punch_time
                    break_minutes += int(break_duration.total_seconds() / 60)
            
            summary["break_minutes"] = break_minutes
            summary["actual_work_minutes"] = summary["work_minutes"] - break_minutes
            
            # 残業時間計算（簡易版：8時間超過分）
            standard_minutes = 8 * 60  # 8時間
            if summary["actual_work_minutes"] > standard_minutes:
                summary["overtime_minutes"] = summary["actual_work_minutes"] - standard_minutes
        
        return summary
    
    async def export_monthly_report_csv(
        self,
        year: int,
        month: int,
        employee_id: Optional[int] = None
    ) -> str:
        """
        月次レポートをCSV形式でエクスポート
        
        Args:
            year: 年
            month: 月
            employee_id: 従業員ID（指定時は該当従業員のみ）
        
        Returns:
            str: CSV文字列
        """
        # 対象期間の日付リストを作成
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        # CSVバッファ
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            "従業員コード", "従業員名", "日付", "曜日",
            "出勤時刻", "退勤時刻", "休憩時間(分)", "実労働時間(分)",
            "残業時間(分)", "勤怠状況"
        ])
        
        # 対象従業員を取得
        query = self.db.query(Employee).filter(Employee.is_active == True)
        if employee_id:
            query = query.filter(Employee.id == employee_id)
        employees = query.all()
        
        # 各従業員の日次データを出力
        for employee in employees:
            current_date = first_day
            while current_date <= last_day:
                summary = await self._calculate_daily_summary(employee.id, current_date)
                
                # 曜日を日本語で
                weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                weekday = weekdays[current_date.weekday()]
                
                writer.writerow([
                    employee.employee_code,
                    employee.name,
                    current_date.strftime("%Y-%m-%d"),
                    weekday,
                    summary["clock_in_time"] or "",
                    summary["clock_out_time"] or "",
                    summary["break_minutes"],
                    summary["actual_work_minutes"],
                    summary["overtime_minutes"],
                    summary["status"]
                ])
                
                current_date += timedelta(days=1)
        
        return output.getvalue()
    
    async def get_monthly_statistics(
        self,
        year: int,
        month: int,
        employee_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        月次統計情報を取得
        
        Args:
            year: 年
            month: 月
            employee_id: 従業員ID
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        # 対象期間
        first_day = datetime(year, month, 1)
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        # 基本クエリ
        query = self.db.query(
            PunchRecord.employee_id,
            func.count(func.distinct(func.date(PunchRecord.punch_time))).label("work_days")
        ).filter(
            and_(
                PunchRecord.punch_time >= first_day,
                PunchRecord.punch_time < next_month,
                PunchRecord.punch_type == PunchType.CLOCK_IN.value
            )
        )
        
        if employee_id:
            query = query.filter(PunchRecord.employee_id == employee_id)
        
        # グループ化して集計
        results = query.group_by(PunchRecord.employee_id).all()
        
        statistics = {
            "year": year,
            "month": month,
            "period": f"{year}年{month}月",
            "employees": []
        }
        
        for result in results:
            employee = self.db.query(Employee).filter(
                Employee.id == result.employee_id
            ).first()
            
            statistics["employees"].append({
                "employee_id": result.employee_id,
                "employee_name": employee.name,
                "employee_code": employee.employee_code,
                "work_days": result.work_days
            })
        
        return statistics