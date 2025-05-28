"""
打刻データ補正サービス

異常な打刻データに対する補正提案と自動修正機能を提供します。
"""

from datetime import datetime, timedelta, date, time
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging
import statistics

from backend.app.models.punch_record import PunchRecord, PunchType
from backend.app.models.employee import Employee
from backend.app.services.punch_anomaly_service import PunchAnomalyDetector

logger = logging.getLogger(__name__)


class PunchCorrectionService:
    """打刻データ補正サービス"""

    CORRECTION_RULES = {
        "MISSING_OUT": {
            "auto_correct": False,
            "default_work_hours": 8,
            "max_work_hours": 12,
            "confidence_threshold": 0.7,
        },
        "MISSING_RETURN": {
            "auto_correct": False,
            "default_break_hours": 1,
            "max_break_hours": 4,
            "confidence_threshold": 0.8,
        },
        "DUPLICATE_PUNCH": {
            "auto_correct": True,
            "merge_window": 180,  # 秒（3分）
            "confidence_threshold": 0.9,
        },
        "TIME_ADJUSTMENT": {
            "auto_correct": True,
            "max_adjustment": 60,  # 秒
            "confidence_threshold": 0.95,
        },
        "SEQUENCE_ERROR": {"auto_correct": False, "confidence_threshold": 0.6},
    }

    def __init__(self, db: Session):
        self.db = db
        self.anomaly_detector = PunchAnomalyDetector(db)

    async def suggest_corrections(
        self, anomaly_data: Dict[str, any], employee_id: int
    ) -> List[Dict[str, any]]:
        """
        補正提案生成

        Args:
            anomaly_data: 異常検知データ
            employee_id: 従業員ID

        Returns:
            補正提案リスト
        """
        suggestions = []
        anomaly_type = anomaly_data["type"]

        if anomaly_type == "MISSING_PUNCH":
            missing_type = anomaly_data["details"].get("missing_type")
            if missing_type == "OUT":
                suggestion = await self._suggest_missing_out_correction(
                    employee_id, anomaly_data
                )
                if suggestion:
                    suggestions.append(suggestion)

            elif missing_type == "RETURN":
                suggestion = await self._suggest_missing_return_correction(
                    employee_id, anomaly_data
                )
                if suggestion:
                    suggestions.append(suggestion)

        elif anomaly_type == "DUPLICATE_IN":
            suggestion = await self._suggest_duplicate_correction(
                employee_id, anomaly_data
            )
            if suggestion:
                suggestions.append(suggestion)

        elif anomaly_type == "IRREGULAR_PATTERN":
            suggestion = await self._suggest_pattern_correction(
                employee_id, anomaly_data
            )
            if suggestion:
                suggestions.append(suggestion)

        return suggestions

    async def _suggest_missing_out_correction(
        self, employee_id: int, anomaly_data: Dict[str, any]
    ) -> Optional[Dict[str, any]]:
        """退勤打刻漏れの補正提案"""
        work_date = date.fromisoformat(anomaly_data["details"]["work_date"])

        # 従業員の通常の勤務パターンを分析
        historical_data = await self._analyze_work_pattern(employee_id, "OUT")

        if not historical_data:
            # デフォルト値を使用
            suggested_time = datetime.combine(work_date, time(18, 0))  # デフォルト18:00
            confidence = 0.5
        else:
            # 過去のデータから推定
            avg_out_minutes = historical_data["average_time_minutes"]
            suggested_time = datetime.combine(
                work_date, time(int(avg_out_minutes // 60), int(avg_out_minutes % 60))
            )
            confidence = min(0.9, historical_data["consistency_score"])

        # 最大勤務時間チェック
        in_punch = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee_id,
                    PunchRecord.punch_type == PunchType.IN,
                    func.date(PunchRecord.punch_time) == work_date,
                )
            )
            .first()
        )

        if in_punch:
            work_hours = (suggested_time - in_punch.punch_time).total_seconds() / 3600
            if work_hours > self.CORRECTION_RULES["MISSING_OUT"]["max_work_hours"]:
                # 最大勤務時間で調整
                suggested_time = in_punch.punch_time + timedelta(
                    hours=self.CORRECTION_RULES["MISSING_OUT"]["max_work_hours"]
                )
                confidence *= 0.8

        return {
            "type": "ADD_PUNCH",
            "punch_type": "OUT",
            "suggested_time": suggested_time.isoformat(),
            "confidence": round(confidence, 2),
            "reason": "退勤打刻漏れの可能性",
            "based_on": "historical_pattern" if historical_data else "default_value",
            "requires_approval": True,
            "correction_details": {
                "work_date": work_date.isoformat(),
                "in_time": in_punch.punch_time.isoformat() if in_punch else None,
                "estimated_work_hours": round(work_hours, 2) if in_punch else None,
            },
        }

    async def _suggest_missing_return_correction(
        self, employee_id: int, anomaly_data: Dict[str, any]
    ) -> Optional[Dict[str, any]]:
        """戻り打刻漏れの補正提案"""
        last_outside = datetime.fromisoformat(anomaly_data["details"]["last_outside"])

        # 従業員の通常の外出パターンを分析
        break_pattern = await self._analyze_break_pattern(employee_id)

        if break_pattern:
            avg_break_minutes = break_pattern["average_break_minutes"]
            suggested_time = last_outside + timedelta(minutes=avg_break_minutes)
            confidence = break_pattern["consistency_score"]
        else:
            # デフォルト1時間の休憩
            suggested_time = last_outside + timedelta(hours=1)
            confidence = 0.6

        # 最大休憩時間チェック
        break_hours = (suggested_time - last_outside).total_seconds() / 3600
        if break_hours > self.CORRECTION_RULES["MISSING_RETURN"]["max_break_hours"]:
            suggested_time = last_outside + timedelta(
                hours=self.CORRECTION_RULES["MISSING_RETURN"]["max_break_hours"]
            )
            confidence *= 0.7

        return {
            "type": "ADD_PUNCH",
            "punch_type": "RETURN",
            "suggested_time": suggested_time.isoformat(),
            "confidence": round(confidence, 2),
            "reason": "戻り打刻漏れの可能性",
            "based_on": "break_pattern" if break_pattern else "default_value",
            "requires_approval": True,
            "correction_details": {
                "outside_time": last_outside.isoformat(),
                "estimated_break_minutes": round(
                    (suggested_time - last_outside).total_seconds() / 60, 2
                ),
            },
        }

    async def _suggest_duplicate_correction(
        self, employee_id: int, anomaly_data: Dict[str, any]
    ) -> Optional[Dict[str, any]]:
        """重複打刻の補正提案"""
        first_punch = datetime.fromisoformat(anomaly_data["details"]["first_in"])
        second_punch = datetime.fromisoformat(anomaly_data["details"]["second_in"])

        # どちらを残すべきか判定
        # 基本的には最初の打刻を採用
        keep_first = True
        confidence = 0.9

        # 他の打刻との整合性チェック
        daily_punches = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee_id,
                    func.date(PunchRecord.punch_time) == first_punch.date(),
                )
            )
            .order_by(PunchRecord.punch_time)
            .all()
        )

        # 退勤時刻との関係で判定
        out_punch = next(
            (p for p in daily_punches if p.punch_type == PunchType.OUT), None
        )

        if out_punch:
            work_hours_first = (
                out_punch.punch_time - first_punch
            ).total_seconds() / 3600
            work_hours_second = (
                out_punch.punch_time - second_punch
            ).total_seconds() / 3600

            # より妥当な勤務時間の方を採用
            if abs(work_hours_second - 8) < abs(work_hours_first - 8):
                keep_first = False

        return {
            "type": "REMOVE_PUNCH",
            "target_time": (second_punch if keep_first else first_punch).isoformat(),
            "keep_time": (first_punch if keep_first else second_punch).isoformat(),
            "confidence": confidence,
            "reason": "重複した出勤打刻",
            "requires_approval": False,  # 高信頼度なので自動補正可能
            "correction_details": {
                "interval_minutes": anomaly_data["details"]["interval_minutes"],
                "decision": "keep_first" if keep_first else "keep_second",
            },
        }

    async def _suggest_pattern_correction(
        self, employee_id: int, anomaly_data: Dict[str, any]
    ) -> Optional[Dict[str, any]]:
        """パターン逸脱の補正提案"""
        # 通常パターンからの逸脱は提案のみ（自動補正しない）
        usual_time = anomaly_data["details"]["usual_time"]
        actual_time = datetime.fromisoformat(anomaly_data["details"]["punch_time"])
        deviation = anomaly_data["details"]["deviation"]

        return {
            "type": "TIME_ADJUSTMENT",
            "current_time": actual_time.isoformat(),
            "suggested_time": None,  # 時刻調整は提案しない
            "confidence": 0.5,
            "reason": f"通常の打刻時刻（{usual_time}）から大きく逸脱",
            "requires_approval": True,
            "correction_details": {
                "usual_pattern": usual_time,
                "deviation_score": deviation,
                "action": "review_required",
            },
        }

    async def auto_correct_minor_issues(
        self, punch_record: PunchRecord
    ) -> Optional[Dict[str, any]]:
        """
        軽微な問題の自動補正

        Args:
            punch_record: 打刻記録

        Returns:
            補正結果（補正した場合）
        """
        corrections_made = []

        # 1. 秒単位の微調整（0秒に正規化）
        if punch_record.punch_time.second != 0:
            original_time = punch_record.punch_time
            punch_record.punch_time = punch_record.punch_time.replace(
                second=0, microsecond=0
            )
            corrections_made.append(
                {
                    "type": "TIME_NORMALIZATION",
                    "original": original_time.isoformat(),
                    "corrected": punch_record.punch_time.isoformat(),
                    "reason": "秒単位の正規化",
                }
            )

        # 2. 明らかな日付エラー（未来の日付）
        if punch_record.punch_time > datetime.now() + timedelta(minutes=1):
            # 1分以上未来の場合は現在時刻に修正
            original_time = punch_record.punch_time
            punch_record.punch_time = datetime.now().replace(second=0, microsecond=0)
            corrections_made.append(
                {
                    "type": "FUTURE_TIME_CORRECTION",
                    "original": original_time.isoformat(),
                    "corrected": punch_record.punch_time.isoformat(),
                    "reason": "未来の時刻を現在時刻に修正",
                }
            )

        if corrections_made:
            self.db.commit()
            logger.info(
                f"Auto-corrected punch record {punch_record.id}: "
                f"{len(corrections_made)} corrections made"
            )

            return {
                "punch_id": punch_record.id,
                "corrections": corrections_made,
                "auto_corrected": True,
                "corrected_at": datetime.now().isoformat(),
            }

        return None

    async def _analyze_work_pattern(
        self, employee_id: int, punch_type: str
    ) -> Optional[Dict[str, any]]:
        """従業員の勤務パターン分析"""
        # 過去30日間の打刻データを取得
        thirty_days_ago = datetime.now() - timedelta(days=30)

        historical_punches = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee_id,
                    PunchRecord.punch_type == punch_type,
                    PunchRecord.punch_time >= thirty_days_ago,
                )
            )
            .all()
        )

        if len(historical_punches) < 5:  # データが少なすぎる
            return None

        # 時刻を分単位に変換
        time_minutes = [
            p.punch_time.hour * 60 + p.punch_time.minute for p in historical_punches
        ]

        # 統計分析
        avg_minutes = statistics.mean(time_minutes)
        stdev_minutes = statistics.stdev(time_minutes) if len(time_minutes) > 1 else 0

        # 一貫性スコア（標準偏差が小さいほど高い）
        consistency_score = max(0, 1 - (stdev_minutes / 60))  # 1時間の偏差で0.0

        return {
            "average_time_minutes": avg_minutes,
            "stdev_minutes": stdev_minutes,
            "consistency_score": consistency_score,
            "sample_size": len(historical_punches),
        }

    async def _analyze_break_pattern(
        self, employee_id: int
    ) -> Optional[Dict[str, any]]:
        """従業員の休憩パターン分析"""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # 外出・戻りのペアを取得
        outside_punches = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee_id,
                    PunchRecord.punch_type == PunchType.OUTSIDE,
                    PunchRecord.punch_time >= thirty_days_ago,
                )
            )
            .all()
        )

        break_durations = []

        for outside_punch in outside_punches:
            # 対応する戻り打刻を探す
            return_punch = (
                self.db.query(PunchRecord)
                .filter(
                    and_(
                        PunchRecord.employee_id == employee_id,
                        PunchRecord.punch_type == PunchType.RETURN,
                        PunchRecord.punch_time > outside_punch.punch_time,
                        func.date(PunchRecord.punch_time)
                        == func.date(outside_punch.punch_time),
                    )
                )
                .order_by(PunchRecord.punch_time)
                .first()
            )

            if return_punch:
                duration_minutes = (
                    return_punch.punch_time - outside_punch.punch_time
                ).total_seconds() / 60
                break_durations.append(duration_minutes)

        if len(break_durations) < 3:  # データが少なすぎる
            return None

        # 統計分析
        avg_break = statistics.mean(break_durations)
        stdev_break = (
            statistics.stdev(break_durations) if len(break_durations) > 1 else 0
        )

        # 一貫性スコア
        consistency_score = max(0, 1 - (stdev_break / 30))  # 30分の偏差で0.0

        return {
            "average_break_minutes": avg_break,
            "stdev_minutes": stdev_break,
            "consistency_score": consistency_score,
            "sample_size": len(break_durations),
        }

    async def apply_correction(
        self, correction: Dict[str, any], approved_by: int
    ) -> Dict[str, any]:
        """
        補正の適用

        Args:
            correction: 補正提案
            approved_by: 承認者ID

        Returns:
            適用結果
        """
        try:
            if correction["type"] == "ADD_PUNCH":
                # 新しい打刻を追加
                new_punch = PunchRecord(
                    employee_id=correction.get("employee_id"),
                    punch_type=correction["punch_type"],
                    punch_time=datetime.fromisoformat(correction["suggested_time"]),
                    is_modified=True,
                    modified_by=approved_by,
                    modified_at=datetime.now(),
                    modification_reason=correction["reason"],
                    note="自動補正により追加",
                )
                self.db.add(new_punch)
                self.db.commit()

                return {
                    "success": True,
                    "action": "added",
                    "punch_id": new_punch.id,
                    "applied_at": datetime.now().isoformat(),
                }

            elif correction["type"] == "REMOVE_PUNCH":
                # 打刻を削除（実際には無効化）
                target_punch = (
                    self.db.query(PunchRecord)
                    .filter(
                        and_(
                            PunchRecord.punch_time
                            == datetime.fromisoformat(correction["target_time"]),
                            PunchRecord.employee_id == correction.get("employee_id"),
                        )
                    )
                    .first()
                )

                if target_punch:
                    target_punch.is_modified = True
                    target_punch.modified_by = approved_by
                    target_punch.modified_at = datetime.now()
                    target_punch.modification_reason = correction["reason"]
                    target_punch.note = "重複のため無効化"
                    self.db.commit()

                    return {
                        "success": True,
                        "action": "removed",
                        "punch_id": target_punch.id,
                        "applied_at": datetime.now().isoformat(),
                    }

            return {"success": False, "error": "Unknown correction type"}

        except Exception as e:
            logger.error(f"Failed to apply correction: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
