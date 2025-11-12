"""
打刻サービス

打刻処理のビジネスロジックを実装します。
"""

import hashlib
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from config.config import config
from backend.app.models import Employee, PunchRecord, PunchType
from backend.app.utils.punch_helpers import (
    DISPLAY_NAMES,
    STATUS_MAP,
    VALID_TRANSITIONS,
)


class PunchService:
    """打刻処理サービス"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_punch(
        self,
        card_idm: Optional[str] = None,
        punch_type: PunchType = PunchType.IN,
        device_type: str = "pasori",
        note: Optional[str] = None,
        card_idm_hash: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        打刻を作成
        
        Args:
            card_idm: カードIDm
            punch_type: 打刻種別
            device_type: デバイス種別
            note: 備考
            card_idm: 生のカードIDm
            punch_type: 打刻種別
            device_type: デバイス種別
            note: 備考
            card_idm_hash: 事前にハッシュ化されたカードIDm
            timestamp: 打刻時刻を指定する場合
        
        Returns:
            Dict[str, Any]: 打刻結果
        
        Raises:
            ValueError: バリデーションエラー
        """
        if not card_idm and not card_idm_hash:
            raise ValueError("card_idm もしくは card_idm_hash を指定してください")
        
        # IDmのハッシュ化
        if card_idm_hash:
            idm_hash = card_idm_hash.lower()
        else:
            idm_hash = hashlib.sha256(
                f"{card_idm}{config.IDM_HASH_SECRET}".encode()
            ).hexdigest()
        
        # 従業員の検索
        employee = self.db.query(Employee).filter(
            Employee.card_idm_hash == idm_hash,
            Employee.is_active == True
        ).first()
        
        if not employee:
            raise ValueError("登録されていないカード、または無効な従業員です")
        
        # 最新の打刻状態を確認
        await self._validate_punch_sequence(employee.id, punch_type)
        
        # 打刻記録の作成
        punch_record = PunchRecord(
            employee_id=employee.id,
            punch_type=punch_type.value,
            punch_time=timestamp or datetime.now(),
            device_type=device_type,
            note=note
        )
        
        self.db.add(punch_record)
        self.db.commit()
        self.db.refresh(punch_record)
        
        return {
            "success": True,
            "message": f"{punch_record.punch_type_display}を記録しました",
            "punch": punch_record.to_dict(),
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "employee_code": employee.employee_code
            }
        }
    
    async def _validate_punch_sequence(self, employee_id: int, punch_type: PunchType) -> None:
        """
        打刻の順序を検証
        
        Args:
            employee_id: 従業員ID
            punch_type: 打刻種別
        
        Raises:
            ValueError: 不正な打刻順序の場合
        """
        # 本日の最新の打刻を取得
        today = date.today()
        latest_punch = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= datetime.combine(today, datetime.min.time())
            )
        ).order_by(desc(PunchRecord.punch_time)).first()
        
        if not latest_punch:
            # 本日初めての打刻の場合、出勤のみ許可
            if punch_type != PunchType.IN:
                raise ValueError("本日の最初の打刻は出勤である必要があります")
            return

        last_type = PunchType(latest_punch.punch_type)
        valid_next_types = VALID_TRANSITIONS.get(last_type, [])
        
        if punch_type not in valid_next_types:
            raise ValueError(
                f"現在の状態（{latest_punch.punch_type_display}）では"
                f"{self._get_punch_type_display(punch_type)}はできません"
            )
    
    def _get_punch_type_display(self, punch_type: PunchType) -> str:
        """打刻種別の表示名を取得"""
        return DISPLAY_NAMES.get(punch_type, punch_type.value)
    
    async def get_employee_status(self, employee_id: int) -> Dict[str, Any]:
        """
        従業員の現在の打刻状況を取得
        
        Args:
            employee_id: 従業員ID
        
        Returns:
            Dict[str, Any]: 打刻状況
        """
        # 従業員の存在確認
        employee = self.db.query(Employee).filter(
            Employee.id == employee_id
        ).first()
        
        if not employee:
            raise ValueError(f"従業員ID {employee_id} が見つかりません")
        
        # 本日の打刻記録を取得
        today = date.today()
        today_punches = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= datetime.combine(today, datetime.min.time())
            )
        ).order_by(PunchRecord.punch_time).all()
        
        # 最新の打刻
        latest_punch = today_punches[-1] if today_punches else None
        
        # 現在の状態を判定
        current_status = "未出勤"
        if latest_punch:
            current_status = STATUS_MAP.get(latest_punch.punch_type, "不明")
        
        return {
            "employee": employee.to_dict(),
            "current_status": current_status,
            "latest_punch": latest_punch.to_dict() if latest_punch else None,
            "today_punches": [p.to_dict() for p in today_punches],
            "punch_count": len(today_punches)
        }
    
    async def get_punch_history(
        self,
        employee_id: int,
        date: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        打刻履歴を取得
        
        Args:
            employee_id: 従業員ID
            date: 対象日（YYYY-MM-DD形式）
            limit: 取得件数上限
        
        Returns:
            Dict[str, Any]: 打刻履歴
        """
        # 従業員の存在確認
        employee = self.db.query(Employee).filter(
            Employee.id == employee_id
        ).first()
        
        if not employee:
            raise ValueError(f"従業員ID {employee_id} が見つかりません")
        
        # クエリ構築
        query = self.db.query(PunchRecord).filter(
            PunchRecord.employee_id == employee_id
        )
        
        # 日付フィルター
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
                query = query.filter(
                    and_(
                        PunchRecord.punch_time >= datetime.combine(target_date, datetime.min.time()),
                        PunchRecord.punch_time < datetime.combine(target_date + timedelta(days=1), datetime.min.time())
                    )
                )
            except ValueError:
                raise ValueError("日付は YYYY-MM-DD 形式で指定してください")
        
        # 履歴取得
        records = query.order_by(desc(PunchRecord.punch_time)).limit(limit).all()
        
        return {
            "employee": employee.to_dict(),
            "records": [r.to_dict() for r in records],
            "count": len(records),
            "filter": {
                "date": date,
                "limit": limit
            }
        }
