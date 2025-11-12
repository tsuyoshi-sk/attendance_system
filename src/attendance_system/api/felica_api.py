from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ..database import get_db
from ..models import User, FeliCaRegistration, AttendanceRecord
from ..security.security_manager import SecurityManager

router = APIRouter(tags=["felica"])
logger = logging.getLogger(__name__)

@router.post("/api/felica-attendance")
async def felica_attendance_record(data: dict, db: Session = Depends(get_db)):
    """FeliCa IDMによる勤怠記録"""
    try:
        felica_idm = data["felica_idm"]
        timestamp_str = data["timestamp"]
        reader_id = data.get("reader_id", "unknown")
        
        # FeliCa登録からユーザー検索
        felica_reg = db.query(FeliCaRegistration).filter(
            FeliCaRegistration.felica_idm == felica_idm,
            FeliCaRegistration.is_active == True
        ).first()
        
        if not felica_reg:
            logger.warning(f"未登録のFeliCa IDM: {felica_idm}")
            raise HTTPException(status_code=404, detail="未登録のカードです")
        
        user = felica_reg.user
        if not user or not user.is_active:
            raise HTTPException(status_code=404, detail="無効なユーザーです")
        
        # 出勤/退勤判定
        today = datetime.now().date()
        last_record = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.timestamp >= today
        ).order_by(AttendanceRecord.timestamp.desc()).first()
        
        attendance_type = "check_out" if (last_record and last_record.type == "check_in") else "check_in"
        
        # 勤怠記録作成
        attendance = AttendanceRecord(
            user_id=user.id,
            timestamp=datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')),
            type=attendance_type,
            location=f"felica-{reader_id}",
            felica_idm=felica_idm
        )
        
        db.add(attendance)
        db.commit()
        
        logger.info(f"FeliCa勤怠記録: {user.name} - {attendance_type}")
        
        return {
            "success": True,
            "user_name": user.name,
            "employee_id": user.employee_id,
            "type": attendance_type,
            "timestamp": attendance.timestamp.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FeliCa勤怠記録エラー: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="勤怠記録に失敗しました")

@router.post("/api/admin/felica/register")
async def register_felica_card(data: dict, db: Session = Depends(get_db)):
    """FeliCaカード登録"""
    try:
        user_id = data["user_id"]
        felica_idm = data["felica_idm"]
        
        # ユーザー存在確認
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
        
        # 重複チェック
        existing = db.query(FeliCaRegistration).filter(
            FeliCaRegistration.felica_idm == felica_idm
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="このカードは既に登録されています")
        
        # 既存登録を無効化
        db.query(FeliCaRegistration).filter(
            FeliCaRegistration.user_id == user_id
        ).update({"is_active": False})
        
        # 新規登録
        registration = FeliCaRegistration(
            user_id=user_id,
            felica_idm=felica_idm,
            registered_at=datetime.utcnow(),
            is_active=True
        )
        
        db.add(registration)
        db.commit()
        
        logger.info(f"FeliCaカード登録完了: {user.name} - {felica_idm}")
        
        return {"success": True, "message": "カード登録完了"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FeliCaカード登録エラー: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="カード登録に失敗しました")