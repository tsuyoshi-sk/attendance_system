"""
リアルタイム打刻監視API

WebSocket経由でリアルタイムの打刻状況を配信します。
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

from backend.app.database import get_db
from backend.app.models.punch_record import PunchRecord, PunchType
from backend.app.models.employee import Employee
from backend.app.services.punch_anomaly_service import PunchAnomalyDetector
from backend.app.services.punch_alert_service import PunchAlertService
from hardware.device_monitor import device_monitor
from hardware.multi_reader_manager import multi_reader_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket接続管理"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """接続を受け入れ"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """接続を切断"""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """全クライアントにブロードキャスト"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = set()
        
        # 各接続に送信
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending to websocket: {str(e)}")
                disconnected.add(connection)
        
        # 切断された接続を削除
        async with self._lock:
            self.active_connections -= disconnected


manager = ConnectionManager()


@router.websocket("/ws/punch-monitor")
async def punch_monitor_websocket(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    リアルタイム打刻監視WebSocket
    
    配信データ:
    - リアルタイム打刻情報
    - デバイス状態
    - アラート通知
    - パフォーマンスメトリクス
    """
    await manager.connect(websocket)
    
    try:
        # 初期データを送信
        initial_data = await get_current_status(db)
        await websocket.send_json({
            "type": "initial",
            "data": initial_data
        })
        
        # 定期更新タスクを開始
        update_task = asyncio.create_task(
            periodic_updates(websocket, db)
        )
        
        # クライアントからのメッセージを待機
        while True:
            data = await websocket.receive_text()
            
            # クライアントからのリクエストを処理
            try:
                request = json.loads(data)
                response = await handle_client_request(request, db)
                await websocket.send_json(response)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling client request: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Internal server error"
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await manager.disconnect(websocket)
        # クリーンアップ
        if 'update_task' in locals():
            update_task.cancel()


async def periodic_updates(websocket: WebSocket, db: Session):
    """定期的な更新を送信"""
    while True:
        try:
            # リアルタイムデータを収集
            real_time_data = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "active_punches": await get_active_punches(db),
                    "device_status": await get_device_status(),
                    "recent_alerts": await get_recent_alerts(db),
                    "performance_metrics": await get_performance_metrics(db)
                }
            }
            
            # 個別接続に送信
            await websocket.send_json(real_time_data)
            
            # 異常検知があればブロードキャスト
            anomalies = await check_real_time_anomalies(db)
            if anomalies:
                await manager.broadcast({
                    "type": "anomaly",
                    "timestamp": datetime.now().isoformat(),
                    "anomalies": anomalies
                })
            
            await asyncio.sleep(5)  # 5秒間隔
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic updates: {str(e)}")
            await asyncio.sleep(10)  # エラー時は長めの待機


async def handle_client_request(request: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """クライアントリクエストを処理"""
    request_type = request.get("type")
    
    if request_type == "ping":
        return {"type": "pong", "timestamp": datetime.now().isoformat()}
    
    elif request_type == "get_employee_status":
        employee_id = request.get("employee_id")
        if employee_id:
            status = await get_employee_punch_status(db, employee_id)
            return {"type": "employee_status", "data": status}
    
    elif request_type == "get_department_summary":
        department = request.get("department")
        summary = await get_department_summary(db, department)
        return {"type": "department_summary", "data": summary}
    
    elif request_type == "subscribe":
        # 特定のイベントをサブスクライブ
        events = request.get("events", [])
        return {"type": "subscribed", "events": events}
    
    else:
        return {"type": "error", "message": f"Unknown request type: {request_type}"}


async def get_current_status(db: Session) -> Dict[str, Any]:
    """現在の状態を取得"""
    return {
        "timestamp": datetime.now().isoformat(),
        "summary": await get_system_summary(db),
        "active_employees": await get_active_employee_count(db),
        "device_health": await get_device_health_summary(),
        "recent_punches": await get_recent_punches(db, limit=10)
    }


async def get_active_punches(db: Session) -> List[Dict[str, Any]]:
    """アクティブな打刻を取得（最近5分間）"""
    five_minutes_ago = datetime.now() - timedelta(minutes=5)
    
    recent_punches = db.query(PunchRecord).join(Employee).filter(
        PunchRecord.punch_time >= five_minutes_ago
    ).order_by(PunchRecord.punch_time.desc()).limit(20).all()
    
    return [
        {
            "id": p.id,
            "employee_id": p.employee_id,
            "employee_name": p.employee.name if p.employee else "Unknown",
            "punch_type": p.punch_type,
            "punch_time": p.punch_time.isoformat(),
            "device_type": p.device_type
        }
        for p in recent_punches
    ]


async def get_device_status() -> Dict[str, Any]:
    """デバイス状態を取得"""
    # マルチリーダーマネージャーから状態を取得
    multi_reader_status = await multi_reader_manager.get_reader_status()
    
    # デバイスモニターから状態を取得
    monitor_summary = await device_monitor.get_monitoring_summary()
    
    return {
        "readers": multi_reader_status,
        "monitoring": monitor_summary,
        "timestamp": datetime.now().isoformat()
    }


async def get_recent_alerts(db: Session) -> List[Dict[str, Any]]:
    """最近のアラートを取得"""
    # 実際のアラートサービスから取得
    # ここではサンプルデータを返す
    return [
        {
            "id": 1,
            "type": "MISSING_OUT",
            "employee_id": 123,
            "message": "退勤打刻がありません",
            "severity": "MEDIUM",
            "created_at": datetime.now().isoformat()
        }
    ]


async def get_performance_metrics(db: Session) -> Dict[str, Any]:
    """パフォーマンスメトリクスを取得"""
    # 直近1時間の統計
    one_hour_ago = datetime.now() - timedelta(hours=1)
    
    total_punches = db.query(func.count(PunchRecord.id)).filter(
        PunchRecord.punch_time >= one_hour_ago
    ).scalar()
    
    # タイプ別集計
    type_counts = db.query(
        PunchRecord.punch_type,
        func.count(PunchRecord.id)
    ).filter(
        PunchRecord.punch_time >= one_hour_ago
    ).group_by(PunchRecord.punch_type).all()
    
    return {
        "total_punches_hour": total_punches,
        "punches_by_type": dict(type_counts),
        "avg_response_time": 0.15,  # サンプル値
        "error_rate": 0.02,  # サンプル値
        "cache_hit_rate": 0.85  # サンプル値
    }


async def check_real_time_anomalies(db: Session) -> List[Dict[str, Any]]:
    """リアルタイム異常をチェック"""
    anomaly_detector = PunchAnomalyDetector(db)
    
    # 最新の打刻をチェック
    latest_punches = db.query(PunchRecord).filter(
        PunchRecord.punch_time >= datetime.now() - timedelta(minutes=1)
    ).all()
    
    anomalies = []
    for punch in latest_punches:
        detected = await anomaly_detector.detect_anomalies(punch, check_historical=False)
        if detected:
            anomalies.extend([
                {
                    "punch_id": punch.id,
                    "employee_id": punch.employee_id,
                    **anomaly
                }
                for anomaly in detected
            ])
    
    return anomalies


async def get_employee_punch_status(db: Session, employee_id: int) -> Dict[str, Any]:
    """従業員の打刻状態を取得"""
    today = datetime.now().date()
    
    # 本日の打刻記録
    today_punches = db.query(PunchRecord).filter(
        and_(
            PunchRecord.employee_id == employee_id,
            func.date(PunchRecord.punch_time) == today
        )
    ).order_by(PunchRecord.punch_time).all()
    
    # 現在の状態を判定
    status = "not_in"
    last_punch = None
    
    if today_punches:
        last_punch = today_punches[-1]
        if last_punch.punch_type == PunchType.IN:
            status = "in_office"
        elif last_punch.punch_type == PunchType.OUT:
            status = "left"
        elif last_punch.punch_type == PunchType.OUTSIDE:
            status = "outside"
        elif last_punch.punch_type == PunchType.RETURN:
            status = "in_office"
    
    return {
        "employee_id": employee_id,
        "status": status,
        "last_punch": {
            "type": last_punch.punch_type,
            "time": last_punch.punch_time.isoformat()
        } if last_punch else None,
        "today_punches": [
            {
                "type": p.punch_type,
                "time": p.punch_time.isoformat()
            }
            for p in today_punches
        ]
    }


async def get_department_summary(db: Session, department: str = None) -> Dict[str, Any]:
    """部署別サマリーを取得"""
    query = db.query(Employee).filter(Employee.is_active == True)
    
    if department:
        query = query.filter(Employee.department == department)
    
    employees = query.all()
    
    # 各従業員の状態を集計
    status_counts = {
        "in_office": 0,
        "outside": 0,
        "left": 0,
        "not_in": 0
    }
    
    for employee in employees:
        status = await get_employee_punch_status(db, employee.id)
        status_counts[status["status"]] += 1
    
    return {
        "department": department or "all",
        "total_employees": len(employees),
        "status_breakdown": status_counts,
        "attendance_rate": (status_counts["in_office"] + status_counts["outside"]) / len(employees) if employees else 0
    }


async def get_system_summary(db: Session) -> Dict[str, Any]:
    """システムサマリーを取得"""
    today = datetime.now().date()
    
    # 本日の統計
    today_stats = db.query(
        func.count(func.distinct(PunchRecord.employee_id)).label("unique_employees"),
        func.count(PunchRecord.id).label("total_punches")
    ).filter(
        func.date(PunchRecord.punch_time) == today
    ).first()
    
    return {
        "date": today.isoformat(),
        "unique_employees": today_stats.unique_employees if today_stats else 0,
        "total_punches": today_stats.total_punches if today_stats else 0,
        "system_status": "operational"
    }


async def get_active_employee_count(db: Session) -> int:
    """アクティブな従業員数を取得"""
    return db.query(func.count(Employee.id)).filter(
        Employee.is_active == True
    ).scalar()


async def get_device_health_summary() -> Dict[str, Any]:
    """デバイス健全性サマリーを取得"""
    monitor_summary = await device_monitor.get_monitoring_summary()
    
    # 全体的な健全性スコアを計算
    total_score = 0
    device_count = 0
    
    for device in monitor_summary.get("devices", []):
        total_score += device.get("health_score", 0)
        device_count += 1
    
    overall_health = total_score / device_count if device_count > 0 else 0
    
    return {
        "overall_health": round(overall_health, 2),
        "device_count": device_count,
        "status": "healthy" if overall_health > 0.7 else "degraded" if overall_health > 0.4 else "critical"
    }


async def get_recent_punches(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """最近の打刻を取得"""
    recent = db.query(PunchRecord).join(Employee).order_by(
        PunchRecord.punch_time.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "employee_name": p.employee.name if p.employee else "Unknown",
            "department": p.employee.department if p.employee else None,
            "punch_type": p.punch_type,
            "punch_time": p.punch_time.isoformat()
        }
        for p in recent
    ]


@router.get("/api/v1/punch/dashboard/metrics")
async def get_dashboard_metrics(db: Session = Depends(get_db)):
    """
    ダッシュボード用メトリクス
    
    Returns:
        現在のシステムメトリクス
    """
    today = datetime.now().date()
    
    # 本日の打刻数
    today_punch_count = db.query(func.count(PunchRecord.id)).filter(
        func.date(PunchRecord.punch_time) == today
    ).scalar()
    
    # アクティブな従業員数（本日打刻した人数）
    active_employees = db.query(
        func.count(func.distinct(PunchRecord.employee_id))
    ).filter(
        func.date(PunchRecord.punch_time) == today
    ).scalar()
    
    # デバイス健全性
    device_health = await get_device_health_summary()
    
    # エラー率（サンプル値）
    error_rate = 0.02
    
    # 平均応答時間（サンプル値）
    avg_response_time = 0.15
    
    return {
        "today_punch_count": today_punch_count,
        "active_employees": active_employees,
        "device_health": device_health,
        "error_rate": error_rate,
        "average_response_time": avg_response_time,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/v1/punch/dashboard/live-feed")
async def get_live_feed(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    ライブフィード（最新の打刻）
    
    Args:
        limit: 取得件数
        
    Returns:
        最新の打刻リスト
    """
    return await get_recent_punches(db, limit)


@router.get("/api/v1/punch/dashboard/alerts")
async def get_dashboard_alerts(db: Session = Depends(get_db)):
    """
    ダッシュボード用アラート
    
    Returns:
        アクティブなアラートリスト
    """
    alerts = await get_recent_alerts(db)
    
    # 重要度でソート
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 4))
    
    return {
        "alerts": alerts[:10],  # 上位10件
        "total_count": len(alerts),
        "timestamp": datetime.now().isoformat()
    }