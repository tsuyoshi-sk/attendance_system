"""
統合ヘルスチェックシステム

全サブシステムの健全性を監視する統合ヘルスチェック機能を提供します。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import logging
from pathlib import Path

from sqlalchemy import text, select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import get_db, engine
from backend.app.models import Employee, PunchRecord, DailySummary, MonthlySummary, User
from config.config import config

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """ヘルスステータス定義"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class SubsystemHealth:
    """サブシステムのヘルスチェック結果"""

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict] = None,
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.checked_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "checked_at": self.checked_at.isoformat(),
        }


class HealthChecker:
    """統合ヘルスチェッカー"""

    def __init__(self, db: Session):
        self.db = db

    async def check_all(self) -> Dict[str, Any]:
        """全システムのヘルスチェックを実行"""
        start_time = datetime.now()

        # 各サブシステムのチェックを並行実行
        checks = await asyncio.gather(
            self._check_database(),
            self._check_punch_system(),
            self._check_employee_system(),
            self._check_report_system(),
            self._check_analytics_system(),
            self._check_pasori(),
            self._check_file_system(),
            return_exceptions=True,
        )

        # 結果の集計
        subsystems = []
        overall_status = HealthStatus.HEALTHY
        unhealthy_count = 0
        degraded_count = 0

        for check in checks:
            if isinstance(check, Exception):
                logger.error(f"ヘルスチェックエラー: {check}")
                subsystems.append(
                    SubsystemHealth(
                        "unknown", HealthStatus.UNKNOWN, f"チェック失敗: {str(check)}"
                    )
                )
                unhealthy_count += 1
            else:
                subsystems.append(check)
                if check.status == HealthStatus.UNHEALTHY:
                    unhealthy_count += 1
                elif check.status == HealthStatus.DEGRADED:
                    degraded_count += 1

        # 全体ステータスの判定
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED

        # 処理時間の計算
        duration = (datetime.now() - start_time).total_seconds()

        return {
            "status": overall_status.value,
            "timestamp": start_time.isoformat(),
            "duration_seconds": duration,
            "subsystems": [s.to_dict() for s in subsystems],
            "summary": {
                "total": len(subsystems),
                "healthy": sum(
                    1 for s in subsystems if s.status == HealthStatus.HEALTHY
                ),
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
            },
        }

    async def _check_database(self) -> SubsystemHealth:
        """データベース接続チェック"""
        try:
            # 接続テスト
            result = self.db.execute(text("SELECT 1"))
            result.scalar()

            # テーブル数の確認
            tables = self.db.execute(
                text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            ).scalar()

            # レコード数の確認
            employee_count = self.db.query(func.count(Employee.id)).scalar()
            punch_count = self.db.query(func.count(PunchRecord.id)).scalar()

            return SubsystemHealth(
                "database",
                HealthStatus.HEALTHY,
                "データベース正常",
                {
                    "tables": tables,
                    "employees": employee_count,
                    "punch_records": punch_count,
                },
            )
        except SQLAlchemyError as e:
            logger.error(f"データベースエラー: {e}")
            return SubsystemHealth(
                "database", HealthStatus.UNHEALTHY, f"データベース接続エラー: {str(e)}"
            )

    async def _check_punch_system(self) -> SubsystemHealth:
        """打刻システムチェック"""
        try:
            # 最新の打刻記録を確認
            latest_punch = (
                self.db.query(PunchRecord)
                .order_by(PunchRecord.punch_time.desc())
                .first()
            )

            if not latest_punch:
                return SubsystemHealth(
                    "punch_system", HealthStatus.HEALTHY, "打刻記録なし（新規システム）"
                )

            # 最後の打刻からの経過時間
            time_since_last = datetime.now() - latest_punch.punch_time

            # 今日の打刻数
            today_count = (
                self.db.query(func.count(PunchRecord.id))
                .filter(func.date(PunchRecord.punch_time) == datetime.now().date())
                .scalar()
            )

            status = HealthStatus.HEALTHY
            message = "打刻システム正常"

            # 12時間以上打刻がない場合は警告
            if time_since_last > timedelta(hours=12):
                status = HealthStatus.DEGRADED
                message = "12時間以上打刻記録なし"

            return SubsystemHealth(
                "punch_system",
                status,
                message,
                {
                    "last_punch": latest_punch.punch_time.isoformat(),
                    "time_since_last_minutes": int(
                        time_since_last.total_seconds() / 60
                    ),
                    "today_count": today_count,
                },
            )
        except Exception as e:
            logger.error(f"打刻システムチェックエラー: {e}")
            return SubsystemHealth(
                "punch_system", HealthStatus.UNHEALTHY, f"チェックエラー: {str(e)}"
            )

    async def _check_employee_system(self) -> SubsystemHealth:
        """従業員管理システムチェック"""
        try:
            # アクティブな従業員数
            active_employees = (
                self.db.query(func.count(Employee.id))
                .filter(Employee.is_active == True)
                .scalar()
            )

            # カード登録済み従業員数
            with_card = (
                self.db.query(func.count(Employee.id))
                .filter(Employee.card_idm_hash.isnot(None))
                .scalar()
            )

            # 管理者アカウント数
            admin_count = (
                self.db.query(func.count(User.id))
                .filter(User.is_admin == True, User.is_active == True)
                .scalar()
            )

            status = HealthStatus.HEALTHY
            message = "従業員管理システム正常"

            if active_employees == 0:
                status = HealthStatus.DEGRADED
                message = "アクティブな従業員が登録されていません"
            elif admin_count == 0:
                status = HealthStatus.UNHEALTHY
                message = "管理者アカウントが存在しません"

            return SubsystemHealth(
                "employee_system",
                status,
                message,
                {
                    "active_employees": active_employees,
                    "with_card": with_card,
                    "admin_accounts": admin_count,
                    "card_registration_rate": f"{(with_card/active_employees*100 if active_employees > 0 else 0):.1f}%",
                },
            )
        except Exception as e:
            logger.error(f"従業員管理システムチェックエラー: {e}")
            return SubsystemHealth(
                "employee_system", HealthStatus.UNHEALTHY, f"チェックエラー: {str(e)}"
            )

    async def _check_report_system(self) -> SubsystemHealth:
        """レポートシステムチェック"""
        try:
            # 最新の日次集計
            latest_daily = (
                self.db.query(DailySummary)
                .order_by(DailySummary.work_date.desc())
                .first()
            )

            # 最新の月次集計
            latest_monthly = (
                self.db.query(MonthlySummary)
                .order_by(MonthlySummary.year.desc(), MonthlySummary.month.desc())
                .first()
            )

            status = HealthStatus.HEALTHY
            message = "レポートシステム正常"
            details = {}

            if latest_daily:
                days_behind = (datetime.now().date() - latest_daily.work_date).days
                details["latest_daily_summary"] = latest_daily.work_date.isoformat()
                details["daily_days_behind"] = days_behind

                if days_behind > 2:
                    status = HealthStatus.DEGRADED
                    message = f"日次集計が{days_behind}日遅れています"
            else:
                details["latest_daily_summary"] = None

            if latest_monthly:
                details[
                    "latest_monthly_summary"
                ] = f"{latest_monthly.year}-{latest_monthly.month:02d}"
            else:
                details["latest_monthly_summary"] = None

            return SubsystemHealth("report_system", status, message, details)
        except Exception as e:
            logger.error(f"レポートシステムチェックエラー: {e}")
            return SubsystemHealth(
                "report_system", HealthStatus.UNHEALTHY, f"チェックエラー: {str(e)}"
            )

    async def _check_analytics_system(self) -> SubsystemHealth:
        """分析システムチェック"""
        try:
            # 分析用データの可用性チェック
            has_data = self.db.query(PunchRecord).limit(1).first() is not None

            if not has_data:
                return SubsystemHealth(
                    "analytics_system",
                    HealthStatus.DEGRADED,
                    "分析データが存在しません",
                    {"has_data": False},
                )

            # キャッシュディレクトリの確認
            cache_dir = Path(config.DATA_DIR) / "analytics_cache"
            cache_exists = cache_dir.exists()

            return SubsystemHealth(
                "analytics_system",
                HealthStatus.HEALTHY,
                "分析システム正常",
                {
                    "has_data": True,
                    "cache_directory": str(cache_dir),
                    "cache_exists": cache_exists,
                },
            )
        except Exception as e:
            logger.error(f"分析システムチェックエラー: {e}")
            return SubsystemHealth(
                "analytics_system", HealthStatus.UNHEALTHY, f"チェックエラー: {str(e)}"
            )

    async def _check_pasori(self) -> SubsystemHealth:
        """PaSoRiデバイスチェック"""
        try:
            if config.PASORI_MOCK_MODE:
                return SubsystemHealth(
                    "pasori", HealthStatus.HEALTHY, "モックモードで動作中", {"mock_mode": True}
                )

            # 実際のPaSoRiチェック（簡易版）
            # TODO: 実際のデバイス接続チェックを実装
            return SubsystemHealth(
                "pasori",
                HealthStatus.HEALTHY,
                "PaSoRi準備完了",
                {"mock_mode": False, "timeout_seconds": config.PASORI_TIMEOUT},
            )
        except Exception as e:
            logger.error(f"PaSoRiチェックエラー: {e}")
            return SubsystemHealth(
                "pasori", HealthStatus.UNHEALTHY, f"デバイスエラー: {str(e)}"
            )

    async def _check_file_system(self) -> SubsystemHealth:
        """ファイルシステムチェック"""
        try:
            issues = []

            # 必要なディレクトリの確認
            required_dirs = [
                Path(config.DATA_DIR),
                Path(config.LOG_DIR),
                Path(config.DATA_DIR) / "exports",
                Path(config.DATA_DIR) / "backups",
            ]

            for dir_path in required_dirs:
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    issues.append(f"ディレクトリを作成: {dir_path}")

            # ディスク容量チェック（簡易版）
            # TODO: 実際のディスク容量チェックを実装

            status = HealthStatus.HEALTHY
            message = "ファイルシステム正常"

            if issues:
                status = HealthStatus.DEGRADED
                message = f"{len(issues)}個のディレクトリを作成しました"

            return SubsystemHealth(
                "file_system",
                status,
                message,
                {
                    "data_dir": str(Path(config.DATA_DIR).absolute()),
                    "log_dir": str(Path(config.LOG_DIR).absolute()),
                    "issues": issues,
                },
            )
        except Exception as e:
            logger.error(f"ファイルシステムチェックエラー: {e}")
            return SubsystemHealth(
                "file_system", HealthStatus.UNHEALTHY, f"チェックエラー: {str(e)}"
            )


# FastAPI用のエンドポイント関数
async def get_integrated_health_status(db: Session) -> Dict[str, Any]:
    """統合ヘルスチェックの実行"""
    checker = HealthChecker(db)
    return await checker.check_all()


# 定期実行用の関数
async def periodic_health_check():
    """定期的なヘルスチェック実行"""
    from backend.app.database import SessionLocal

    while True:
        try:
            db = SessionLocal()
            checker = HealthChecker(db)
            result = await checker.check_all()

            # 異常時の通知
            if result["status"] != HealthStatus.HEALTHY.value:
                logger.warning(f"システムヘルス異常: {result}")
                # TODO: Slack通知などを実装

        except Exception as e:
            logger.error(f"定期ヘルスチェックエラー: {e}")
        finally:
            db.close()

        # 5分ごとに実行
        await asyncio.sleep(300)
