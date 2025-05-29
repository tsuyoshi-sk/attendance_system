"""
打刻ユースケース

打刻に関するビジネスロジックを調整
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..domain.entities.employee import Employee
from ..domain.services.attendance_service import AttendanceService, PunchData


logger = logging.getLogger(__name__)


class PunchUseCase:
    """打刻ユースケース"""
    
    def __init__(self, employee_repo, punch_repo, attendance_service: AttendanceService):
        self.employee_repo = employee_repo
        self.punch_repo = punch_repo
        self.attendance_service = attendance_service
    
    async def execute_punch(
        self,
        card_id: str,
        punch_type: str,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        打刻実行のメインロジック
        
        Args:
            card_id: カードID
            punch_type: 打刻タイプ
            timestamp: 打刻時刻（Noneの場合は現在時刻）
            
        Returns:
            打刻結果
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            # 1. カードから従業員を特定
            employee = await self._find_employee_by_card(card_id)
            if not employee:
                return {
                    "success": False,
                    "error": "登録されていないカードです",
                    "error_code": "CARD_NOT_FOUND"
                }
            
            # 2. 従業員の打刻可能性チェック
            if not employee.can_punch():
                return {
                    "success": False,
                    "error": "この従業員は打刻できません",
                    "error_code": "EMPLOYEE_INACTIVE"
                }
            
            # 3. 打刻タイプの妥当性チェック
            validation_result = await self._validate_punch_type(
                employee.id, punch_type, timestamp
            )
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "error_code": validation_result["error_code"]
                }
            
            # 4. 打刻記録の作成
            punch_record = await self._create_punch_record(
                employee.id, punch_type, timestamp
            )
            
            # 5. 当日の勤務状況を計算
            daily_summary = await self._calculate_daily_status(
                employee.id, timestamp.date()
            )
            
            logger.info(
                f"打刻成功: 従業員ID={employee.id}, タイプ={punch_type}, 時刻={timestamp}"
            )
            
            return {
                "success": True,
                "employee_name": employee.name,
                "employee_code": employee.employee_code,
                "punch_type": punch_type,
                "timestamp": timestamp.isoformat(),
                "daily_status": daily_summary,
                "message": self._get_punch_message(punch_type, employee.name)
            }
            
        except Exception as e:
            logger.error(f"打刻処理エラー: {e}", exc_info=True)
            return {
                "success": False,
                "error": "システムエラーが発生しました",
                "error_code": "SYSTEM_ERROR"
            }
    
    async def _find_employee_by_card(self, card_id: str) -> Optional[Employee]:
        """カードIDから従業員を検索"""
        # ハッシュ化されたカードIDで検索
        from ..app.utils.security import hash_card_id
        hashed_card_id = hash_card_id(card_id)
        return await self.employee_repo.find_by_card_id(hashed_card_id)
    
    async def _validate_punch_type(
        self, employee_id: int, punch_type: str, timestamp: datetime
    ) -> Dict[str, Any]:
        """打刻タイプの妥当性チェック"""
        
        # 当日の最新打刻を取得
        latest_punch = await self.punch_repo.get_latest_punch_today(
            employee_id, timestamp.date()
        )
        
        # 打刻ルールチェック
        if punch_type == "in":
            if latest_punch and latest_punch.punch_type in ["in", "in_break"]:
                return {
                    "valid": False,
                    "error": "既に出勤済みです",
                    "error_code": "ALREADY_IN"
                }
        
        elif punch_type == "out":
            if not latest_punch or latest_punch.punch_type not in ["in", "in_break"]:
                return {
                    "valid": False,
                    "error": "出勤打刻が必要です",
                    "error_code": "NOT_IN"
                }
        
        elif punch_type == "out_break":
            if not latest_punch or latest_punch.punch_type != "in":
                return {
                    "valid": False,
                    "error": "出勤中でないため外出できません",
                    "error_code": "NOT_IN"
                }
        
        elif punch_type == "in_break":
            if not latest_punch or latest_punch.punch_type != "out_break":
                return {
                    "valid": False,
                    "error": "外出打刻が必要です",
                    "error_code": "NOT_OUT_BREAK"
                }
        
        return {"valid": True}
    
    async def _create_punch_record(
        self, employee_id: int, punch_type: str, timestamp: datetime
    ):
        """打刻記録を作成"""
        return await self.punch_repo.create({
            "employee_id": employee_id,
            "punch_type": punch_type,
            "timestamp": timestamp,
            "created_at": datetime.now()
        })
    
    async def _calculate_daily_status(
        self, employee_id: int, target_date
    ) -> Dict[str, Any]:
        """当日の勤務状況を計算"""
        
        # 当日の全打刻を取得
        punches = await self.punch_repo.get_punches_by_date(employee_id, target_date)
        
        # PunchDataに変換
        punch_data_list = [
            PunchData(
                employee_id=punch.employee_id,
                punch_type=punch.punch_type,
                timestamp=punch.timestamp
            )
            for punch in punches
        ]
        
        # 勤務時間計算
        summary = self.attendance_service.calculate_work_hours(punch_data_list)
        
        return {
            "work_time_minutes": int(summary.work_time.total_seconds() / 60),
            "break_time_minutes": int(summary.break_time.total_seconds() / 60),
            "overtime_minutes": int(summary.overtime_normal.total_seconds() / 60),
            "status": "進行中" if not summary.is_complete else "完了",
            "punch_count": len(punches)
        }
    
    def _get_punch_message(self, punch_type: str, employee_name: str) -> str:
        """打刻メッセージを生成"""
        messages = {
            "in": f"{employee_name}さん、おはようございます！",
            "out": f"{employee_name}さん、お疲れ様でした！",
            "out_break": f"{employee_name}さん、いってらっしゃい！",
            "in_break": f"{employee_name}さん、おかえりなさい！"
        }
        return messages.get(punch_type, f"{employee_name}さん、打刻完了！")