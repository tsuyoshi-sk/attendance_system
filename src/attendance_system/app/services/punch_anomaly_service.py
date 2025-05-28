"""
打刻異常検出サービス

異常な打刻パターンを検出し、潜在的な問題を早期に発見します。
"""

from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging
import json

from backend.app.models.punch_record import PunchRecord, PunchType
from backend.app.models.employee import Employee
from backend.app.utils.time_calculator import TimeCalculator

logger = logging.getLogger(__name__)


class PunchAnomalyDetector:
    """異常打刻検出サービス"""
    
    ANOMALY_PATTERNS = {
        "RAPID_CONSECUTIVE": {
            "interval": 60,  # 秒
            "count": 3,
            "severity": "HIGH",
            "description": "短時間での連続打刻"
        },
        "MIDNIGHT_PUNCH": {
            "start": time(0, 0),
            "end": time(5, 0),
            "severity": "MEDIUM",
            "description": "深夜時間帯の打刻"
        },
        "WEEKEND_PUNCH": {
            "check_holidays": True,
            "severity": "LOW",
            "description": "休日の打刻"
        },
        "LONG_WORK_TIME": {
            "max_hours": 16,
            "severity": "HIGH",
            "description": "長時間勤務"
        },
        "IMPOSSIBLE_TRAVEL": {
            "min_interval": 300,  # 秒（5分）
            "max_distance": 1000,  # メートル
            "severity": "CRITICAL",
            "description": "物理的に不可能な移動"
        },
        "MISSING_PUNCH": {
            "check_pairs": True,
            "severity": "MEDIUM",
            "description": "打刻漏れ"
        },
        "DUPLICATE_IN": {
            "interval": 3600,  # 秒（1時間）
            "severity": "MEDIUM",
            "description": "重複した出勤打刻"
        },
        "IRREGULAR_PATTERN": {
            "deviation_threshold": 2.0,  # 標準偏差の倍数
            "severity": "LOW",
            "description": "通常パターンからの逸脱"
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.time_calculator = TimeCalculator()
    
    async def detect_anomalies(
        self, 
        punch_record: PunchRecord,
        check_historical: bool = True
    ) -> List[Dict[str, any]]:
        """
        異常パターン検出
        
        Args:
            punch_record: 検査対象の打刻記録
            check_historical: 過去データとの比較を行うか
            
        Returns:
            検出された異常のリスト
        """
        anomalies = []
        
        # 連続打刻チェック
        if rapid_check := await self._check_rapid_consecutive(punch_record):
            anomalies.append(rapid_check)
            
        # 深夜打刻チェック  
        if midnight_check := await self._check_midnight_punch(punch_record):
            anomalies.append(midnight_check)
            
        # 長時間勤務チェック
        if long_work_check := await self._check_long_work_time(punch_record):
            anomalies.append(long_work_check)
            
        # 打刻漏れチェック
        if missing_check := await self._check_missing_punch(punch_record):
            anomalies.append(missing_check)
            
        # 重複出勤チェック
        if duplicate_check := await self._check_duplicate_in(punch_record):
            anomalies.append(duplicate_check)
            
        # 過去データとの比較
        if check_historical:
            if irregular_check := await self._check_irregular_pattern(punch_record):
                anomalies.append(irregular_check)
        
        # 異常検出をログに記録
        if anomalies:
            logger.warning(
                f"Anomalies detected for employee {punch_record.employee_id}: "
                f"{json.dumps([a['type'] for a in anomalies])}"
            )
        
        return anomalies
    
    async def _check_rapid_consecutive(
        self, 
        punch_record: PunchRecord
    ) -> Optional[Dict[str, any]]:
        """短時間での連続打刻チェック"""
        pattern = self.ANOMALY_PATTERNS["RAPID_CONSECUTIVE"]
        
        # 指定時間内の打刻を取得
        recent_punches = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == punch_record.employee_id,
                PunchRecord.punch_time >= punch_record.punch_time - timedelta(seconds=pattern["interval"]),
                PunchRecord.punch_time <= punch_record.punch_time,
                PunchRecord.id != punch_record.id
            )
        ).all()
        
        if len(recent_punches) >= pattern["count"] - 1:
            return {
                "type": "RAPID_CONSECUTIVE",
                "severity": pattern["severity"],
                "description": pattern["description"],
                "details": {
                    "count": len(recent_punches) + 1,
                    "interval_seconds": pattern["interval"],
                    "punch_times": [p.punch_time.isoformat() for p in recent_punches]
                },
                "detected_at": datetime.now().isoformat()
            }
        
        return None
    
    async def _check_midnight_punch(
        self, 
        punch_record: PunchRecord
    ) -> Optional[Dict[str, any]]:
        """深夜時間帯の打刻チェック"""
        pattern = self.ANOMALY_PATTERNS["MIDNIGHT_PUNCH"]
        punch_time = punch_record.punch_time.time()
        
        if pattern["start"] <= punch_time <= pattern["end"]:
            return {
                "type": "MIDNIGHT_PUNCH",
                "severity": pattern["severity"],
                "description": pattern["description"],
                "details": {
                    "punch_time": punch_record.punch_time.isoformat(),
                    "time_range": f"{pattern['start'].isoformat()}-{pattern['end'].isoformat()}"
                },
                "detected_at": datetime.now().isoformat()
            }
        
        return None
    
    async def _check_long_work_time(
        self, 
        punch_record: PunchRecord
    ) -> Optional[Dict[str, any]]:
        """長時間勤務チェック"""
        if punch_record.punch_type != PunchType.OUT:
            return None
            
        pattern = self.ANOMALY_PATTERNS["LONG_WORK_TIME"]
        
        # 同日の出勤打刻を探す
        work_date = self.time_calculator.get_work_date(punch_record.punch_time)
        
        in_punch = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == punch_record.employee_id,
                PunchRecord.punch_type == PunchType.IN,
                func.date(PunchRecord.punch_time) == work_date
            )
        ).order_by(PunchRecord.punch_time.desc()).first()
        
        if in_punch:
            work_hours = (punch_record.punch_time - in_punch.punch_time).total_seconds() / 3600
            
            if work_hours > pattern["max_hours"]:
                return {
                    "type": "LONG_WORK_TIME",
                    "severity": pattern["severity"],
                    "description": pattern["description"],
                    "details": {
                        "work_hours": round(work_hours, 2),
                        "max_hours": pattern["max_hours"],
                        "in_time": in_punch.punch_time.isoformat(),
                        "out_time": punch_record.punch_time.isoformat()
                    },
                    "detected_at": datetime.now().isoformat()
                }
        
        return None
    
    async def _check_missing_punch(
        self, 
        punch_record: PunchRecord
    ) -> Optional[Dict[str, any]]:
        """打刻漏れチェック"""
        pattern = self.ANOMALY_PATTERNS["MISSING_PUNCH"]
        
        # 当日の全打刻を取得
        work_date = self.time_calculator.get_work_date(punch_record.punch_time)
        
        daily_punches = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == punch_record.employee_id,
                func.date(PunchRecord.punch_time) == work_date
            )
        ).order_by(PunchRecord.punch_time).all()
        
        # ペアチェック
        punch_types = [p.punch_type for p in daily_punches]
        
        # 出勤はあるが退勤がない
        if PunchType.IN in punch_types and PunchType.OUT not in punch_types:
            if datetime.now().hour >= 22:  # 22時以降でまだ退勤していない
                return {
                    "type": "MISSING_PUNCH",
                    "severity": pattern["severity"],
                    "description": "退勤打刻漏れの可能性",
                    "details": {
                        "missing_type": "OUT",
                        "last_punch": daily_punches[-1].punch_time.isoformat(),
                        "work_date": work_date.isoformat()
                    },
                    "detected_at": datetime.now().isoformat()
                }
        
        # 外出はあるが戻りがない
        outside_count = punch_types.count(PunchType.OUTSIDE)
        return_count = punch_types.count(PunchType.RETURN)
        
        if outside_count > return_count:
            last_outside = next(
                p for p in reversed(daily_punches) 
                if p.punch_type == PunchType.OUTSIDE
            )
            
            if (datetime.now() - last_outside.punch_time).total_seconds() > 7200:  # 2時間以上
                return {
                    "type": "MISSING_PUNCH",
                    "severity": pattern["severity"],
                    "description": "戻り打刻漏れの可能性",
                    "details": {
                        "missing_type": "RETURN",
                        "last_outside": last_outside.punch_time.isoformat(),
                        "duration_hours": round(
                            (datetime.now() - last_outside.punch_time).total_seconds() / 3600, 
                            2
                        )
                    },
                    "detected_at": datetime.now().isoformat()
                }
        
        return None
    
    async def _check_duplicate_in(
        self, 
        punch_record: PunchRecord
    ) -> Optional[Dict[str, any]]:
        """重複出勤チェック"""
        if punch_record.punch_type != PunchType.IN:
            return None
            
        pattern = self.ANOMALY_PATTERNS["DUPLICATE_IN"]
        
        # 近い時間の出勤打刻を探す
        recent_in = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == punch_record.employee_id,
                PunchRecord.punch_type == PunchType.IN,
                PunchRecord.punch_time >= punch_record.punch_time - timedelta(seconds=pattern["interval"]),
                PunchRecord.punch_time < punch_record.punch_time,
                PunchRecord.id != punch_record.id
            )
        ).first()
        
        if recent_in:
            return {
                "type": "DUPLICATE_IN",
                "severity": pattern["severity"],
                "description": pattern["description"],
                "details": {
                    "first_in": recent_in.punch_time.isoformat(),
                    "second_in": punch_record.punch_time.isoformat(),
                    "interval_minutes": round(
                        (punch_record.punch_time - recent_in.punch_time).total_seconds() / 60,
                        2
                    )
                },
                "detected_at": datetime.now().isoformat()
            }
        
        return None
    
    async def _check_irregular_pattern(
        self, 
        punch_record: PunchRecord
    ) -> Optional[Dict[str, any]]:
        """通常パターンからの逸脱チェック"""
        pattern = self.ANOMALY_PATTERNS["IRREGULAR_PATTERN"]
        
        # 過去30日間の同じ種類の打刻時刻を取得
        historical_punches = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == punch_record.employee_id,
                PunchRecord.punch_type == punch_record.punch_type,
                PunchRecord.punch_time >= datetime.now() - timedelta(days=30),
                PunchRecord.punch_time < punch_record.punch_time
            )
        ).all()
        
        if len(historical_punches) < 10:  # データが少なすぎる場合はスキップ
            return None
        
        # 時刻を分単位に変換
        historical_minutes = [
            p.punch_time.hour * 60 + p.punch_time.minute 
            for p in historical_punches
        ]
        current_minutes = punch_record.punch_time.hour * 60 + punch_record.punch_time.minute
        
        # 平均と標準偏差を計算
        import statistics
        mean = statistics.mean(historical_minutes)
        stdev = statistics.stdev(historical_minutes)
        
        # 標準偏差の倍数で判定
        deviation = abs(current_minutes - mean) / stdev if stdev > 0 else 0
        
        if deviation > pattern["deviation_threshold"]:
            return {
                "type": "IRREGULAR_PATTERN",
                "severity": pattern["severity"],
                "description": pattern["description"],
                "details": {
                    "punch_time": punch_record.punch_time.isoformat(),
                    "usual_time": f"{int(mean // 60):02d}:{int(mean % 60):02d}",
                    "deviation": round(deviation, 2),
                    "threshold": pattern["deviation_threshold"]
                },
                "detected_at": datetime.now().isoformat()
            }
        
        return None
    
    async def generate_anomaly_report(
        self, 
        start_date: datetime,
        end_date: datetime,
        employee_id: Optional[int] = None
    ) -> Dict[str, any]:
        """
        異常検知レポート生成
        
        Args:
            start_date: 開始日
            end_date: 終了日
            employee_id: 従業員ID（指定しない場合は全従業員）
            
        Returns:
            異常検知レポート
        """
        # 対象期間の打刻記録を取得
        query = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.punch_time >= start_date,
                PunchRecord.punch_time <= end_date
            )
        )
        
        if employee_id:
            query = query.filter(PunchRecord.employee_id == employee_id)
            
        punch_records = query.all()
        
        # 各打刻に対して異常検出を実行
        all_anomalies = []
        for record in punch_records:
            anomalies = await self.detect_anomalies(record, check_historical=True)
            for anomaly in anomalies:
                anomaly["employee_id"] = record.employee_id
                anomaly["punch_id"] = record.id
                all_anomalies.append(anomaly)
        
        # 異常を種類別に集計
        anomaly_summary = {}
        severity_summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for anomaly in all_anomalies:
            anomaly_type = anomaly["type"]
            severity = anomaly["severity"]
            
            if anomaly_type not in anomaly_summary:
                anomaly_summary[anomaly_type] = {
                    "count": 0,
                    "employees": set(),
                    "severity": severity,
                    "description": self.ANOMALY_PATTERNS[anomaly_type]["description"]
                }
            
            anomaly_summary[anomaly_type]["count"] += 1
            anomaly_summary[anomaly_type]["employees"].add(anomaly["employee_id"])
            severity_summary[severity] += 1
        
        # set をリストに変換
        for key in anomaly_summary:
            anomaly_summary[key]["employees"] = list(anomaly_summary[key]["employees"])
        
        # 優先度の高い異常を抽出
        high_priority_anomalies = [
            a for a in all_anomalies 
            if a["severity"] in ["CRITICAL", "HIGH"]
        ]
        
        return {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_anomalies": len(all_anomalies),
            "total_punches": len(punch_records),
            "anomaly_rate": len(all_anomalies) / len(punch_records) if punch_records else 0,
            "severity_summary": severity_summary,
            "anomaly_summary": anomaly_summary,
            "high_priority_anomalies": high_priority_anomalies[:10],  # 上位10件
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_employee_anomaly_history(
        self,
        employee_id: int,
        days: int = 30
    ) -> List[Dict[str, any]]:
        """
        従業員の異常履歴取得
        
        Args:
            employee_id: 従業員ID
            days: 過去何日分を取得するか
            
        Returns:
            異常履歴リスト
        """
        start_date = datetime.now() - timedelta(days=days)
        
        punch_records = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= start_date
            )
        ).order_by(PunchRecord.punch_time.desc()).all()
        
        anomaly_history = []
        for record in punch_records:
            anomalies = await self.detect_anomalies(record, check_historical=True)
            for anomaly in anomalies:
                anomaly["punch_time"] = record.punch_time.isoformat()
                anomaly["punch_type"] = record.punch_type
                anomaly_history.append(anomaly)
        
        return anomaly_history