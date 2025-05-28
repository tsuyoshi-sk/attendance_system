"""
カードセキュリティ検証機能

カードの偽造検出、行動パターン分析、なりすまし防止を実現します。
"""

import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging
import statistics
import json

from backend.app.models.punch_record import PunchRecord
from backend.app.models.employee import Employee
from backend.app.models.employee_card import EmployeeCard

logger = logging.getLogger(__name__)


class CardSecurityValidator:
    """カードセキュリティ検証"""

    SECURITY_RULES = {
        "idm_pattern": {
            "min_length": 16,
            "max_length": 16,
            "valid_prefixes": [
                "01",
                "02",
                "03",
                "04",
                "05",
            ],  # Sony FeliCa の一般的なプレフィックス
        },
        "behavior_analysis": {
            "location_radius": 1000,  # メートル
            "time_window": 300,  # 秒（5分）
            "pattern_threshold": 0.8,
            "min_history_days": 7,
        },
        "risk_thresholds": {"low": 0.3, "medium": 0.6, "high": 0.8, "critical": 0.9},
    }

    def __init__(self, db: Session):
        self.db = db
        self._behavior_cache: Dict[int, Dict] = {}
        self._risk_scores: Dict[str, float] = {}

    async def detect_card_forgery(self, card_data: Dict[str, any]) -> Dict[str, any]:
        """
        カード偽造検出

        Args:
            card_data: カードデータ（IDm、読み取り特性など）

        Returns:
            セキュリティ検証結果
        """
        idm = card_data.get("idm", "")
        read_time = card_data.get("read_time", 0)
        signal_strength = card_data.get("signal_strength", 0)

        security_checks = {
            "idm_format": self._check_idm_format(idm),
            "timing_analysis": self._check_timing_pattern(read_time),
            "signal_analysis": self._check_signal_pattern(signal_strength),
            "entropy_check": self._check_idm_entropy(idm),
            "blacklist_check": await self._check_blacklist(idm),
        }

        # セキュリティスコアを計算
        security_score = await self._calculate_security_score(
            security_checks, card_data
        )

        # リスクレベルを判定
        risk_level = self._determine_risk_level(security_score)

        result = {
            "is_suspicious": security_score < 0.7,
            "risk_level": risk_level,
            "security_score": round(security_score, 3),
            "checks": security_checks,
            "details": self._generate_security_details(security_checks, security_score),
            "timestamp": datetime.now().isoformat(),
        }

        # 高リスクの場合はログに記録
        if risk_level in ["HIGH", "CRITICAL"]:
            logger.warning(
                f"High risk card detected: {idm[:8]}... "
                f"Score: {security_score}, Risk: {risk_level}"
            )

        return result

    def _check_idm_format(self, idm: str) -> Dict[str, any]:
        """IDmフォーマットチェック"""
        rules = self.SECURITY_RULES["idm_pattern"]

        checks = {
            "valid_length": len(idm) == rules["min_length"],
            "valid_chars": all(c in "0123456789ABCDEF" for c in idm.upper()),
            "valid_prefix": any(
                idm.upper().startswith(p) for p in rules["valid_prefixes"]
            ),
            "not_sequential": not self._is_sequential(idm),
            "not_repeated": not self._is_repeated_pattern(idm),
        }

        passed = all(checks.values())
        confidence = sum(checks.values()) / len(checks)

        return {"passed": passed, "confidence": confidence, "details": checks}

    def _check_timing_pattern(self, read_time: float) -> Dict[str, any]:
        """読み取り時間パターンチェック"""
        # 正常な読み取り時間は通常0.1〜0.5秒
        normal_range = (0.1, 0.5)

        if read_time <= 0:
            return {"passed": False, "confidence": 0, "reason": "Invalid read time"}

        if normal_range[0] <= read_time <= normal_range[1]:
            confidence = 1.0
        elif read_time < normal_range[0]:
            # 速すぎる（エミュレータの可能性）
            confidence = max(0, read_time / normal_range[0])
        else:
            # 遅すぎる
            confidence = max(0, 1 - (read_time - normal_range[1]) / normal_range[1])

        return {
            "passed": confidence > 0.5,
            "confidence": confidence,
            "read_time": read_time,
            "normal_range": normal_range,
        }

    def _check_signal_pattern(self, signal_strength: float) -> Dict[str, any]:
        """信号強度パターンチェック"""
        # 正常な信号強度の範囲（仮定値）
        normal_range = (0.3, 0.9)

        if signal_strength <= 0 or signal_strength > 1:
            return {
                "passed": False,
                "confidence": 0,
                "reason": "Invalid signal strength",
            }

        if normal_range[0] <= signal_strength <= normal_range[1]:
            confidence = 1.0
        else:
            # 範囲外の信号強度
            if signal_strength < normal_range[0]:
                confidence = signal_strength / normal_range[0]
            else:
                confidence = (1 - signal_strength) / (1 - normal_range[1])

        return {
            "passed": confidence > 0.5,
            "confidence": confidence,
            "signal_strength": signal_strength,
            "normal_range": normal_range,
        }

    def _check_idm_entropy(self, idm: str) -> Dict[str, any]:
        """IDmのエントロピーチェック"""
        # 文字の出現頻度を計算
        char_freq = {}
        for char in idm.upper():
            char_freq[char] = char_freq.get(char, 0) + 1

        # エントロピーを計算
        total_chars = len(idm)
        entropy = 0
        for freq in char_freq.values():
            probability = freq / total_chars
            if probability > 0:
                import math

                entropy -= probability * math.log2(probability)

        # 期待されるエントロピー範囲（16進数16文字の場合）
        max_entropy = 4.0  # log2(16)
        min_acceptable_entropy = 2.0

        normalized_entropy = entropy / max_entropy

        return {
            "passed": entropy >= min_acceptable_entropy,
            "confidence": min(1.0, entropy / min_acceptable_entropy),
            "entropy": round(entropy, 3),
            "normalized": round(normalized_entropy, 3),
        }

    async def _check_blacklist(self, idm: str) -> Dict[str, any]:
        """ブラックリストチェック"""
        # TODO: 実際のブラックリストDBと連携
        # ここでは仮のチェックを実装

        known_invalid_patterns = [
            "0000000000000000",
            "FFFFFFFFFFFFFFFF",
            "1234567890ABCDEF",
        ]

        is_blacklisted = idm.upper() in known_invalid_patterns

        return {
            "passed": not is_blacklisted,
            "confidence": 0.0 if is_blacklisted else 1.0,
            "blacklisted": is_blacklisted,
        }

    def _is_sequential(self, idm: str) -> bool:
        """連続パターンチェック"""
        for i in range(len(idm) - 3):
            if idm[i : i + 4] in [
                "0123",
                "1234",
                "2345",
                "3456",
                "4567",
                "5678",
                "6789",
                "789A",
                "89AB",
                "9ABC",
                "ABCD",
                "BCDE",
                "CDEF",
            ]:
                return True
        return False

    def _is_repeated_pattern(self, idm: str) -> bool:
        """繰り返しパターンチェック"""
        # 同じ文字が4回以上連続
        for i in range(len(idm) - 3):
            if len(set(idm[i : i + 4])) == 1:
                return True

        # 2文字パターンの繰り返し
        for i in range(0, len(idm) - 3, 2):
            if idm[i : i + 2] == idm[i + 2 : i + 4]:
                return True

        return False

    async def _calculate_security_score(
        self, checks: Dict[str, Dict], card_data: Dict[str, any]
    ) -> float:
        """セキュリティスコアを計算"""
        weights = {
            "idm_format": 0.3,
            "timing_analysis": 0.2,
            "signal_analysis": 0.2,
            "entropy_check": 0.2,
            "blacklist_check": 0.1,
        }

        total_score = 0
        total_weight = 0

        for check_name, weight in weights.items():
            if check_name in checks:
                confidence = checks[check_name].get("confidence", 0)
                total_score += confidence * weight
                total_weight += weight

        if total_weight > 0:
            return total_score / total_weight
        return 0.0

    def _determine_risk_level(self, security_score: float) -> str:
        """リスクレベルを判定"""
        thresholds = self.SECURITY_RULES["risk_thresholds"]

        risk_score = 1 - security_score

        if risk_score >= thresholds["critical"]:
            return "CRITICAL"
        elif risk_score >= thresholds["high"]:
            return "HIGH"
        elif risk_score >= thresholds["medium"]:
            return "MEDIUM"
        elif risk_score >= thresholds["low"]:
            return "LOW"
        else:
            return "MINIMAL"

    def _generate_security_details(
        self, checks: Dict[str, Dict], security_score: float
    ) -> str:
        """セキュリティ詳細を生成"""
        failed_checks = [
            name for name, check in checks.items() if not check.get("passed", True)
        ]

        if not failed_checks:
            return "All security checks passed"

        details = []

        if "idm_format" in failed_checks:
            details.append("Invalid card ID format detected")
        if "timing_analysis" in failed_checks:
            details.append("Abnormal card reading time")
        if "signal_analysis" in failed_checks:
            details.append("Suspicious signal strength")
        if "entropy_check" in failed_checks:
            details.append("Low entropy in card ID (possible fake)")
        if "blacklist_check" in failed_checks:
            details.append("Card is blacklisted")

        return "; ".join(details)

    async def behavioral_analysis(
        self, employee_id: int, punch_pattern: Dict[str, any]
    ) -> Dict[str, any]:
        """
        行動パターン分析

        Args:
            employee_id: 従業員ID
            punch_pattern: 打刻パターンデータ

        Returns:
            行動分析結果
        """
        # 従業員の過去の行動パターンを取得
        historical_pattern = await self._get_employee_behavior_pattern(employee_id)

        if not historical_pattern:
            return {
                "analysis_available": False,
                "reason": "Insufficient historical data",
                "risk_level": "UNKNOWN",
            }

        # 現在のパターンと比較
        anomalies = []

        # 時間パターン分析
        time_anomaly = await self._analyze_time_pattern(
            employee_id, punch_pattern, historical_pattern
        )
        if time_anomaly["is_anomaly"]:
            anomalies.append(time_anomaly)

        # 場所パターン分析（位置情報が利用可能な場合）
        if "location" in punch_pattern:
            location_anomaly = await self._analyze_location_pattern(
                employee_id, punch_pattern, historical_pattern
            )
            if location_anomaly["is_anomaly"]:
                anomalies.append(location_anomaly)

        # 頻度パターン分析
        frequency_anomaly = await self._analyze_frequency_pattern(
            employee_id, punch_pattern, historical_pattern
        )
        if frequency_anomaly["is_anomaly"]:
            anomalies.append(frequency_anomaly)

        # リスクスコアを計算
        risk_score = self._calculate_behavior_risk_score(anomalies)

        return {
            "analysis_available": True,
            "anomalies": anomalies,
            "risk_score": round(risk_score, 3),
            "risk_level": self._determine_risk_level(1 - risk_score),
            "confidence": historical_pattern.get("confidence", 0.5),
            "recommendation": self._generate_behavior_recommendation(
                anomalies, risk_score
            ),
        }

    async def _get_employee_behavior_pattern(
        self, employee_id: int
    ) -> Optional[Dict[str, any]]:
        """従業員の行動パターンを取得"""
        # キャッシュチェック
        if employee_id in self._behavior_cache:
            cached = self._behavior_cache[employee_id]
            if cached["expires"] > datetime.now():
                return cached["pattern"]

        # 過去30日間の打刻データを取得
        start_date = datetime.now() - timedelta(days=30)

        punch_records = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee_id,
                    PunchRecord.punch_time >= start_date,
                )
            )
            .all()
        )

        if len(punch_records) < 20:  # 最低20件のデータが必要
            return None

        # パターンを分析
        pattern = {
            "usual_in_time": self._calculate_usual_time(
                [p for p in punch_records if p.punch_type == "IN"]
            ),
            "usual_out_time": self._calculate_usual_time(
                [p for p in punch_records if p.punch_type == "OUT"]
            ),
            "usual_locations": self._calculate_usual_locations(punch_records),
            "daily_punch_count": statistics.mean(
                [
                    len([p for p in punch_records if p.punch_time.date() == d])
                    for d in set(p.punch_time.date() for p in punch_records)
                ]
            ),
            "confidence": min(1.0, len(punch_records) / 100),  # 100件で最大信頼度
            "data_points": len(punch_records),
        }

        # キャッシュに保存
        self._behavior_cache[employee_id] = {
            "pattern": pattern,
            "expires": datetime.now() + timedelta(hours=1),
        }

        return pattern

    def _calculate_usual_time(self, punch_records: List[PunchRecord]) -> Dict[str, any]:
        """通常の打刻時刻を計算"""
        if not punch_records:
            return {"mean": None, "std": None}

        # 時刻を分単位に変換
        minutes = [p.punch_time.hour * 60 + p.punch_time.minute for p in punch_records]

        return {
            "mean": statistics.mean(minutes),
            "std": statistics.stdev(minutes) if len(minutes) > 1 else 0,
            "samples": len(minutes),
        }

    def _calculate_usual_locations(
        self, punch_records: List[PunchRecord]
    ) -> List[Dict[str, any]]:
        """通常の打刻場所を計算"""
        locations = {}

        for record in punch_records:
            if record.location_name:
                locations[record.location_name] = (
                    locations.get(record.location_name, 0) + 1
                )

        # 頻度順にソート
        sorted_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)

        return [
            {"name": loc, "frequency": freq / len(punch_records)}
            for loc, freq in sorted_locations[:5]  # 上位5箇所
        ]

    async def _analyze_time_pattern(
        self,
        employee_id: int,
        current_pattern: Dict[str, any],
        historical_pattern: Dict[str, any],
    ) -> Dict[str, any]:
        """時間パターン分析"""
        punch_type = current_pattern.get("punch_type")
        punch_time = current_pattern.get("punch_time")

        if not punch_type or not punch_time:
            return {"is_anomaly": False}

        usual_time_key = f"usual_{punch_type.lower()}_time"
        usual_time = historical_pattern.get(usual_time_key, {})

        if not usual_time.get("mean"):
            return {"is_anomaly": False}

        # 現在の時刻を分単位に変換
        current_minutes = punch_time.hour * 60 + punch_time.minute

        # 偏差を計算
        deviation = abs(current_minutes - usual_time["mean"])
        std = usual_time.get("std", 30)  # デフォルト30分

        # 3標準偏差を超える場合は異常
        is_anomaly = deviation > 3 * std

        return {
            "is_anomaly": is_anomaly,
            "type": "time_pattern",
            "deviation_minutes": round(deviation, 1),
            "usual_time": f"{int(usual_time['mean'] // 60):02d}:{int(usual_time['mean'] % 60):02d}",
            "confidence": min(1.0, usual_time.get("samples", 0) / 20),
        }

    async def _analyze_location_pattern(
        self,
        employee_id: int,
        current_pattern: Dict[str, any],
        historical_pattern: Dict[str, any],
    ) -> Dict[str, any]:
        """場所パターン分析"""
        current_location = current_pattern.get("location", {}).get("name")

        if not current_location:
            return {"is_anomaly": False}

        usual_locations = historical_pattern.get("usual_locations", [])

        # 通常の場所リストに含まれているかチェック
        is_known_location = any(
            loc["name"] == current_location for loc in usual_locations
        )

        # 新しい場所での打刻は潜在的な異常
        is_anomaly = not is_known_location and len(usual_locations) > 0

        return {
            "is_anomaly": is_anomaly,
            "type": "location_pattern",
            "current_location": current_location,
            "known_locations": [loc["name"] for loc in usual_locations],
            "confidence": 0.8 if len(usual_locations) >= 3 else 0.5,
        }

    async def _analyze_frequency_pattern(
        self,
        employee_id: int,
        current_pattern: Dict[str, any],
        historical_pattern: Dict[str, any],
    ) -> Dict[str, any]:
        """頻度パターン分析"""
        # 本日の打刻回数を取得
        today = datetime.now().date()

        today_punches = (
            self.db.query(PunchRecord)
            .filter(
                and_(
                    PunchRecord.employee_id == employee_id,
                    func.date(PunchRecord.punch_time) == today,
                )
            )
            .count()
        )

        usual_daily_count = historical_pattern.get("daily_punch_count", 4)

        # 通常の2倍以上は異常
        is_anomaly = today_punches > usual_daily_count * 2

        return {
            "is_anomaly": is_anomaly,
            "type": "frequency_pattern",
            "today_count": today_punches,
            "usual_count": round(usual_daily_count, 1),
            "confidence": 0.7,
        }

    def _calculate_behavior_risk_score(self, anomalies: List[Dict[str, any]]) -> float:
        """行動リスクスコアを計算"""
        if not anomalies:
            return 1.0  # 異常なし = 低リスク

        # 各異常の重み
        weights = {
            "time_pattern": 0.4,
            "location_pattern": 0.4,
            "frequency_pattern": 0.2,
        }

        risk_score = 0
        total_weight = 0

        for anomaly in anomalies:
            anomaly_type = anomaly.get("type")
            confidence = anomaly.get("confidence", 0.5)
            weight = weights.get(anomaly_type, 0.3)

            risk_score += (1 - confidence) * weight
            total_weight += weight

        if total_weight > 0:
            return max(0, 1 - risk_score / total_weight)

        return 0.5

    def _generate_behavior_recommendation(
        self, anomalies: List[Dict[str, any]], risk_score: float
    ) -> str:
        """行動分析に基づく推奨事項を生成"""
        if not anomalies:
            return "正常な行動パターンです"

        if risk_score < 0.3:
            return "高リスク: 本人確認を推奨します"
        elif risk_score < 0.6:
            return "中リスク: 追加の監視が必要です"
        elif risk_score < 0.8:
            return "低リスク: 継続的な監視を推奨します"
        else:
            return "最小リスク: 通常の逸脱範囲内です"
