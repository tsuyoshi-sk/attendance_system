"""
打刻サービス（非同期版）

打刻処理のビジネスロジックを非同期で実装します。
"""

import logging
import hashlib
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, func
from sqlalchemy.orm import selectinload

from config.config import settings
from backend.app.models import Employee, PunchRecord, PunchType, EmployeeCard
from backend.app.database_async import DatabaseTransaction
from backend.app.services.cache_service import cache_service, cached, invalidate_cache

logger = logging.getLogger(__name__)


class AsyncPunchService:
    """非同期打刻処理サービス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @invalidate_cache("punch_status:*")  # 打刻作成時にステータスキャッシュを無効化
    async def create_punch(
        self,
        card_idm: str,
        punch_type: PunchType,
        device_type: str = "pasori",
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        打刻を作成（トランザクション管理付き）

        Args:
            card_idm: カードIDm
            punch_type: 打刻種別
            device_type: デバイス種別
            note: 備考

        Returns:
            Dict[str, Any]: 打刻結果

        Raises:
            ValueError: バリデーションエラー
        """
        async with DatabaseTransaction() as transaction:
            async with transaction.session() as session:
                # IDmのハッシュ化
                idm_hash = hashlib.sha256(
                    f"{card_idm}{settings.IDM_HASH_SECRET}".encode()
                ).hexdigest()

                # キャッシュから従業員情報を取得
                cache_key = f"employee_by_card:{idm_hash}"
                employee_data = await cache_service.get(cache_key)

                if employee_data:
                    # キャッシュから取得した場合
                    employee_id = employee_data["id"]
                    employee_name = employee_data["name"]
                    employee_code = employee_data["employee_code"]
                else:
                    # 従業員の検索（カード情報も同時に取得）
                    stmt = (
                        select(Employee)
                        .options(selectinload(Employee.cards))
                        .join(EmployeeCard)
                        .where(
                            EmployeeCard.card_idm_hash == idm_hash,
                            EmployeeCard.is_active == True,
                            Employee.is_active == True,
                        )
                    )
                    result = await session.execute(stmt)
                    employee = result.scalar_one_or_none()

                    if not employee:
                        raise ValueError("登録されていないカード、または無効な従業員です")

                    employee_id = employee.id
                    employee_name = employee.name
                    employee_code = employee.employee_code

                    # キャッシュに保存（5分間）
                    await cache_service.set(
                        cache_key,
                        {
                            "id": employee_id,
                            "name": employee_name,
                            "employee_code": employee_code,
                            "is_active": employee.is_active,
                        },
                        ttl=300,
                    )

                # 最新の打刻状態を確認
                await self._validate_punch_sequence(session, employee_id, punch_type)

                # 打刻記録の作成
                punch_record = PunchRecord(
                    employee_id=employee_id,
                    punch_type=punch_type.value,
                    punch_time=datetime.now(),
                    device_type=device_type,
                    note=note,
                )

                session.add(punch_record)
                await session.flush()  # IDを取得するためflush

                # employeeオブジェクトが必要な場合のみ作成
                if not employee_data:
                    punch_record.employee = employee

                logger.info(
                    f"Punch created: employee_id={employee_id}, type={punch_type.value}"
                )

                # キャッシュを無効化（従業員のステータスが変わったため）
                await cache_service.delete(f"punch_status:{employee_id}")

                return {
                    "success": True,
                    "message": f"{self._get_punch_type_display(punch_type)}を記録しました",
                    "punch": {
                        "id": punch_record.id,
                        "employee_id": employee_id,
                        "employee_name": employee_name,
                        "punch_type": punch_record.punch_type,
                        "punch_type_display": self._get_punch_type_display(punch_type),
                        "punch_time": punch_record.punch_time.isoformat(),
                        "device_type": punch_record.device_type,
                        "note": punch_record.note,
                        "created_at": punch_record.created_at.isoformat(),
                    },
                    "employee": {
                        "id": employee_id,
                        "name": employee_name,
                        "employee_code": employee_code,
                    },
                }

    async def _validate_punch_sequence(
        self, session: AsyncSession, employee_id: int, punch_type: PunchType
    ) -> None:
        """
        打刻の順序を検証

        Args:
            session: データベースセッション
            employee_id: 従業員ID
            punch_type: 打刻種別

        Raises:
            ValueError: 不正な打刻順序の場合
        """
        # 本日の最新の打刻を取得
        today = date.today()
        stmt = (
            select(PunchRecord)
            .where(
                and_(
                    PunchRecord.employee_id == employee_id,
                    func.date(PunchRecord.punch_time) == today,
                )
            )
            .order_by(desc(PunchRecord.punch_time))
            .limit(1)
        )

        result = await session.execute(stmt)
        latest_punch = result.scalar_one_or_none()

        if latest_punch:
            latest_type = PunchType(latest_punch.punch_type)

            # 打刻順序の検証
            if latest_type == PunchType.IN and punch_type == PunchType.IN:
                raise ValueError("既に出勤済みです")
            elif latest_type == PunchType.OUT and punch_type in [
                PunchType.OUT,
                PunchType.OUTSIDE,
                PunchType.RETURN,
            ]:
                raise ValueError("既に退勤済みです")
            elif latest_type == PunchType.OUTSIDE and punch_type == PunchType.OUTSIDE:
                raise ValueError("既に外出中です")
            elif (
                latest_type in [PunchType.IN, PunchType.RETURN]
                and punch_type == PunchType.RETURN
            ):
                raise ValueError("外出していません")

    @cached("punch_status", ttl=60)  # 1分間キャッシュ
    async def get_punch_status(self, employee_id: int) -> Dict[str, Any]:
        """
        従業員の現在の打刻状況を取得

        Args:
            employee_id: 従業員ID

        Returns:
            Dict[str, Any]: 打刻状況
        """
        # 従業員の存在確認
        stmt = select(Employee).where(Employee.id == employee_id)
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()

        if not employee:
            raise ValueError("従業員が見つかりません")

        # 本日の打刻記録を取得
        today = date.today()
        stmt = (
            select(PunchRecord)
            .where(
                and_(
                    PunchRecord.employee_id == employee_id,
                    func.date(PunchRecord.punch_time) == today,
                )
            )
            .order_by(PunchRecord.punch_time)
        )

        result = await self.db.execute(stmt)
        today_punches = result.scalars().all()

        # 最新の打刻を取得
        latest_punch = today_punches[-1] if today_punches else None

        # 労働時間の計算
        work_time = await self._calculate_work_time(today_punches)

        return {
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "employee_code": employee.employee_code,
            },
            "current_status": self._get_current_status(latest_punch),
            "today_punches": [await self._punch_to_dict(p) for p in today_punches],
            "work_time": work_time,
            "can_punch": await self._get_available_punch_types(latest_punch),
        }

    async def get_punch_history(
        self,
        employee_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        打刻履歴を取得

        Args:
            employee_id: 従業員ID（指定しない場合は全従業員）
            start_date: 開始日
            end_date: 終了日
            limit: 取得件数上限

        Returns:
            List[Dict[str, Any]]: 打刻履歴
        """
        stmt = select(PunchRecord).options(selectinload(PunchRecord.employee))

        # フィルタ条件
        conditions = []
        if employee_id:
            conditions.append(PunchRecord.employee_id == employee_id)
        if start_date:
            conditions.append(func.date(PunchRecord.punch_time) >= start_date)
        if end_date:
            conditions.append(func.date(PunchRecord.punch_time) <= end_date)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(desc(PunchRecord.punch_time)).limit(limit)

        result = await self.db.execute(stmt)
        punches = result.scalars().all()

        return [await self._punch_to_dict(p) for p in punches]

    def _get_punch_type_display(self, punch_type: PunchType) -> str:
        """打刻種別の表示名を取得"""
        display_names = {
            PunchType.IN: "出勤",
            PunchType.OUT: "退勤",
            PunchType.OUTSIDE: "外出",
            PunchType.RETURN: "戻り",
        }
        return display_names.get(punch_type, punch_type.value)

    def _get_current_status(self, latest_punch: Optional[PunchRecord]) -> str:
        """現在の状態を取得"""
        if not latest_punch:
            return "未出勤"

        punch_type = PunchType(latest_punch.punch_type)
        status_map = {
            PunchType.IN: "勤務中",
            PunchType.OUT: "退勤済",
            PunchType.OUTSIDE: "外出中",
            PunchType.RETURN: "勤務中",
        }
        return status_map.get(punch_type, "不明")

    async def _get_available_punch_types(
        self, latest_punch: Optional[PunchRecord]
    ) -> List[str]:
        """利用可能な打刻種別を取得"""
        if not latest_punch:
            return [PunchType.IN.value]

        punch_type = PunchType(latest_punch.punch_type)

        if punch_type == PunchType.IN:
            return [PunchType.OUT.value, PunchType.OUTSIDE.value]
        elif punch_type == PunchType.OUTSIDE:
            return [PunchType.RETURN.value]
        elif punch_type == PunchType.RETURN:
            return [PunchType.OUT.value, PunchType.OUTSIDE.value]
        else:  # OUT
            return []

    async def _calculate_work_time(self, punches: List[PunchRecord]) -> Dict[str, Any]:
        """労働時間を計算"""
        if not punches:
            return {"total_minutes": 0, "total_hours": "0:00", "details": []}

        total_minutes = 0
        details = []
        in_time = None

        for punch in punches:
            punch_type = PunchType(punch.punch_type)

            if punch_type == PunchType.IN:
                in_time = punch.punch_time
            elif punch_type == PunchType.OUT and in_time:
                work_minutes = int((punch.punch_time - in_time).total_seconds() / 60)
                total_minutes += work_minutes
                details.append(
                    {
                        "start": in_time.isoformat(),
                        "end": punch.punch_time.isoformat(),
                        "minutes": work_minutes,
                    }
                )
                in_time = None
            elif punch_type == PunchType.RETURN and in_time:
                # 外出から戻った場合、外出時間を引く
                pass

        # 現在も勤務中の場合
        if in_time:
            work_minutes = int((datetime.now() - in_time).total_seconds() / 60)
            total_minutes += work_minutes
            details.append(
                {
                    "start": in_time.isoformat(),
                    "end": None,
                    "minutes": work_minutes,
                    "ongoing": True,
                }
            )

        hours = total_minutes // 60
        minutes = total_minutes % 60

        return {
            "total_minutes": total_minutes,
            "total_hours": f"{hours}:{minutes:02d}",
            "details": details,
        }

    async def _punch_to_dict(self, punch: PunchRecord) -> Dict[str, Any]:
        """打刻記録を辞書形式に変換"""
        return {
            "id": punch.id,
            "employee_id": punch.employee_id,
            "employee_name": punch.employee.name if punch.employee else None,
            "punch_type": punch.punch_type,
            "punch_type_display": self._get_punch_type_display(
                PunchType(punch.punch_type)
            ),
            "punch_time": punch.punch_time.isoformat(),
            "device_type": punch.device_type,
            "note": punch.note,
            "created_at": punch.created_at.isoformat(),
        }
