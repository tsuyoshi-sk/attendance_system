from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..models import User, SuicaRegistration, AttendanceRecord
from ..security.security_manager import SecurityManager, SecurityContext

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)

@router.get("/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    """管理者統計情報取得"""
    try:
        today = datetime.now().date()
        
        # 今日の出勤者数
        checked_in_count = db.query(AttendanceRecord).filter(
            AttendanceRecord.timestamp >= today,
            AttendanceRecord.type == "check_in"
        ).count()
        
        # 総勤怠記録数
        total_records = db.query(AttendanceRecord).count()
        
        # 総ユーザー数
        total_users = db.query(User).count()
        
        return {
            "checked_in_count": checked_in_count,
            "total_records": total_records,
            "total_users": total_users,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Stats retrieval error: {e}")
        raise HTTPException(status_code=500, detail="統計取得エラー")

@router.get("/users")
async def get_users(db: Session = Depends(get_db)):
    """ユーザー一覧取得"""
    try:
        users = db.query(User).all()
        result = []
        
        for user in users:
            # Suica登録状況確認
            suica_reg = db.query(SuicaRegistration).filter(
                SuicaRegistration.user_id == user.id,
                SuicaRegistration.is_active == True
            ).first()
            
            # 最終出勤記録
            last_attendance = db.query(AttendanceRecord).filter(
                AttendanceRecord.user_id == user.id
            ).order_by(AttendanceRecord.timestamp.desc()).first()
            
            result.append({
                "id": user.id,
                "name": user.name,
                "employee_id": user.employee_id,
                "department": user.department,
                "suica_registered": suica_reg is not None,
                "last_attendance": last_attendance.timestamp.isoformat() if last_attendance else None,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat()
            })
        
        return result
    except Exception as e:
        logger.error(f"Users retrieval error: {e}")
        raise HTTPException(status_code=500, detail="ユーザー取得エラー")

@router.post("/users")
async def create_user(user_data: dict, db: Session = Depends(get_db)):
    """新規ユーザー作成"""
    try:
        # 重複チェック
        existing = db.query(User).filter(User.employee_id == user_data["employee_id"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="社員IDが既に存在します")
        
        new_user = User(
            name=user_data["name"],
            employee_id=user_data["employee_id"],
            department=user_data.get("department"),
            is_active=True,
            created_at=datetime.now()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user created: {new_user.employee_id}")
        return {"id": new_user.id, "message": "ユーザー作成完了"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User creation error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="ユーザー作成エラー")

@router.post("/suica/register")
async def register_suica(registration_data: dict, db: Session = Depends(get_db)):
    """Suica IDM登録"""
    try:
        user_id = registration_data["user_id"]
        suica_idm = registration_data["suica_idm"]
        
        # ユーザー存在確認
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
        
        # IDMハッシュ化
        security_manager = SecurityManager()
        context = SecurityContext(user_id=str(user_id), timestamp=datetime.now())
        hashed_idm = security_manager.secure_nfc_idm(suica_idm, context)
        
        # 既存登録を無効化
        db.query(SuicaRegistration).filter(
            SuicaRegistration.user_id == user_id
        ).update({"is_active": False})
        
        # 新規登録
        registration = SuicaRegistration(
            user_id=user_id,
            suica_idm_hash=hashed_idm,
            registered_at=datetime.now(),
            is_active=True
        )
        
        db.add(registration)
        db.commit()
        
        logger.info(f"Suica registered for user {user.employee_id}")
        return {"message": "Suica登録完了"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Suica registration error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Suica登録エラー")

@router.get("/attendance")
async def get_attendance_records(limit: int = 50, db: Session = Depends(get_db)):
    """勤怠記録一覧取得"""
    try:
        records = db.query(AttendanceRecord).join(User).order_by(
            AttendanceRecord.timestamp.desc()
        ).limit(limit).all()
        
        result = []
        for record in records:
            result.append({
                "id": record.id,
                "timestamp": record.timestamp.isoformat(),
                "type": record.type,
                "location": record.location,
                "user_name": record.user.name if record.user else "不明",
                "employee_id": record.user.employee_id if record.user else None
            })
        
        return result
    except Exception as e:
        logger.error(f"Attendance records retrieval error: {e}")
        raise HTTPException(status_code=500, detail="勤怠記録取得エラー")