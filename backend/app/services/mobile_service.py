"""
モバイルアプリ用サービス

従業員向けモバイルアプリの機能を提供
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case

from backend.app.models.punch_record import PunchRecord, PunchType
from backend.app.models.employee import Employee
from backend.app.models.user import User


class MobileService:
    """モバイルアプリ向けサービスクラス"""

    @staticmethod
    def get_today_status(db: Session, user_id: int) -> Dict[str, Any]:
        """
        今日の勤怠ステータスを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID

        Returns:
            今日の勤怠状況
        """
        # ユーザーから従業員IDを取得
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.employee_id:
            return {
                "status": "no_employee",
                "today": date.today().isoformat(),
                "message": "従業員情報が見つかりません"
            }

        employee_id = user.employee_id
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        # 今日の打刻記録を取得
        punch_records = db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= today_start,
                PunchRecord.punch_time <= today_end
            )
        ).order_by(PunchRecord.punch_time).all()

        # ステータス判定
        status = "not_started"
        first_in = None
        last_out = None
        total_work_minutes = 0
        is_on_break = False

        if punch_records:
            # 最初の出勤時刻
            for record in punch_records:
                if record.punch_type == PunchType.IN.value:
                    first_in = record.punch_time.strftime("%H:%M")
                    break

            # 最後の打刻を確認
            last_punch = punch_records[-1]

            if last_punch.punch_type == PunchType.OUT.value:
                status = "off"
                last_out = last_punch.punch_time.strftime("%H:%M")
            elif last_punch.punch_type == PunchType.OUTSIDE.value:
                status = "break"
                is_on_break = True
            elif last_punch.punch_type == PunchType.IN.value or last_punch.punch_type == PunchType.RETURN.value:
                status = "working"

            # 労働時間を計算
            total_work_minutes = MobileService._calculate_work_time(punch_records)

        return {
            "status": status,
            "today": today.isoformat(),
            "first_in": first_in,
            "last_out": last_out,
            "total_work_minutes": total_work_minutes,
            "overtime_minutes": max(0, total_work_minutes - 480),  # 8時間を超える分を残業とする
            "is_on_break": is_on_break,
            "punch_count": len(punch_records)
        }

    @staticmethod
    def _calculate_work_time(punch_records: List[PunchRecord]) -> int:
        """
        打刻記録から労働時間を計算（分単位）

        Args:
            punch_records: 打刻記録のリスト

        Returns:
            労働時間（分）
        """
        total_minutes = 0
        work_start = None

        for record in punch_records:
            if record.punch_type in [PunchType.IN.value, PunchType.RETURN.value]:
                work_start = record.punch_time
            elif record.punch_type in [PunchType.OUT.value, PunchType.OUTSIDE.value]:
                if work_start:
                    diff = record.punch_time - work_start
                    total_minutes += int(diff.total_seconds() / 60)
                    work_start = None

        # まだ退勤していない場合は現在時刻までを計算
        if work_start:
            diff = datetime.now() - work_start
            total_minutes += int(diff.total_seconds() / 60)

        return total_minutes

    @staticmethod
    def get_monthly_summary(db: Session, user_id: int, year_month: str) -> Dict[str, Any]:
        """
        月次サマリーを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            year_month: 対象月（YYYY-MM形式）

        Returns:
            月次サマリー
        """
        # ユーザーから従業員IDを取得
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.employee_id:
            return {
                "year_month": year_month,
                "message": "従業員情報が見つかりません"
            }

        employee_id = user.employee_id

        # 対象月の開始日と終了日を計算
        year, month = map(int, year_month.split("-"))
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)

        # 月次の打刻記録を取得
        punch_records = db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= month_start,
                PunchRecord.punch_time <= month_end
            )
        ).order_by(PunchRecord.punch_time).all()

        # 日別にグループ化
        daily_records = {}
        for record in punch_records:
            day = record.punch_time.date()
            if day not in daily_records:
                daily_records[day] = []
            daily_records[day].append(record)

        # サマリー計算
        total_work_days = len(daily_records)
        total_work_minutes = 0
        total_overtime_minutes = 0

        for day, records in daily_records.items():
            work_minutes = MobileService._calculate_work_time(records)
            total_work_minutes += work_minutes
            if work_minutes > 480:  # 8時間を超える分
                total_overtime_minutes += (work_minutes - 480)

        return {
            "year_month": year_month,
            "total_work_days": total_work_days,
            "total_work_hours": round(total_work_minutes / 60, 1),
            "total_overtime_hours": round(total_overtime_minutes / 60, 1),
            "average_work_hours": round(total_work_minutes / 60 / max(total_work_days, 1), 1)
        }

    @staticmethod
    def get_daily_timeline(db: Session, user_id: int, target_date: str) -> Dict[str, Any]:
        """
        特定日のタイムラインを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            target_date: 対象日（YYYY-MM-DD形式）

        Returns:
            日次タイムライン
        """
        # ユーザーから従業員IDを取得
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.employee_id:
            return {
                "date": target_date,
                "message": "従業員情報が見つかりません",
                "records": []
            }

        employee_id = user.employee_id

        # 対象日の開始と終了
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
        day_start = datetime.combine(target, datetime.min.time())
        day_end = datetime.combine(target, datetime.max.time())

        # 打刻記録を取得
        punch_records = db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= day_start,
                PunchRecord.punch_time <= day_end
            )
        ).order_by(PunchRecord.punch_time).all()

        # タイムライン形式に変換
        timeline = []
        for record in punch_records:
            timeline.append({
                "id": record.id,
                "punch_type": record.punch_type,
                "punch_type_display": record.punch_type_display,
                "punch_time": record.punch_time.strftime("%H:%M:%S"),
                "location_name": record.location_name,
                "latitude": record.latitude,
                "longitude": record.longitude,
                "device_type": record.device_type,
                "note": record.note
            })

        # 労働時間を計算
        work_minutes = MobileService._calculate_work_time(punch_records)

        return {
            "date": target_date,
            "total_work_hours": round(work_minutes / 60, 1),
            "overtime_hours": round(max(0, work_minutes - 480) / 60, 1),
            "records": timeline
        }

    @staticmethod
    def create_punch(
        db: Session,
        user_id: int,
        punch_type: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_name: Optional[str] = None,
        device_type: str = "mobile",
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        打刻を作成

        Args:
            db: データベースセッション
            user_id: ユーザーID
            punch_type: 打刻種別
            latitude: 緯度
            longitude: 経度
            location_name: 場所名
            device_type: デバイスタイプ
            note: 備考

        Returns:
            作成結果
        """
        # ユーザーから従業員IDを取得
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.employee_id:
            raise ValueError("従業員情報が見つかりません")

        employee_id = user.employee_id

        # 打刻レコードを作成
        punch_record = PunchRecord(
            employee_id=employee_id,
            punch_type=punch_type,
            punch_time=datetime.now(),
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            device_type=device_type,
            note=note
        )

        db.add(punch_record)
        db.commit()
        db.refresh(punch_record)

        return {
            "success": True,
            "punch_id": punch_record.id,
            "punch_type": punch_record.punch_type,
            "punch_time": punch_record.punch_time.isoformat(),
            "message": f"{punch_record.punch_type_display}を記録しました"
        }
