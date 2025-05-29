"""
API v1

勤怠管理システム APIバージョン1
"""

from fastapi import APIRouter

from . import auth, punch, admin, reports, analytics, employees, health

# v1 APIルーター
v1_router = APIRouter(prefix="/api/v1", tags=["API v1"])

# 各エンドポイントを登録
v1_router.include_router(auth.router, prefix="/auth", tags=["認証 v1"])
v1_router.include_router(punch.router, prefix="/punch", tags=["打刻 v1"])
v1_router.include_router(admin.router, prefix="/admin", tags=["管理 v1"])
v1_router.include_router(reports.router, prefix="/reports", tags=["レポート v1"])
v1_router.include_router(analytics.router, prefix="/analytics", tags=["分析 v1"])
v1_router.include_router(employees.router, prefix="/employees", tags=["従業員 v1"])
v1_router.include_router(health.router, prefix="/health", tags=["ヘルスチェック v1"])
