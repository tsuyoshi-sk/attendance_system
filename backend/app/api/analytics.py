"""
分析APIエンドポイント

ダッシュボード、統計分析、チャートデータ用のAPIを提供
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.report import (
    DashboardResponse, StatisticsResponse, ChartDataResponse
)
from backend.app.services.analytics_service import AnalyticsService
from backend.app.utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def analytics_health_check():
    """分析API ヘルスチェック"""
    return {"status": "healthy", "module": "analytics"}


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: Session = Depends(get_db)
) -> DashboardResponse:
    """
    ダッシュボードデータを取得
    
    Args:
        db: データベースセッション
    
    Returns:
        DashboardResponse: ダッシュボードデータ
    """
    try:
        service = AnalyticsService(db)
        dashboard_data = await service.get_dashboard_data()
        return dashboard_data
    except Exception as e:
        logger.error(f"ダッシュボードデータ取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ダッシュボードデータの取得中にエラーが発生しました"
        )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    period: str = "month",
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    統計データを取得
    
    Args:
        period: 期間（day, week, month, year）
        year: 年（月・年集計時）
        month: 月（月集計時）
        db: データベースセッション
    
    Returns:
        StatisticsResponse: 統計データ
    """
    try:
        if period not in ["day", "week", "month", "year"]:
            raise ValueError("期間は day, week, month, year のいずれかを指定してください")
        
        service = AnalyticsService(db)
        stats = await service.get_statistics(
            period=period,
            year=year,
            month=month
        )
        return stats
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"統計データ取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="統計データの取得中にエラーが発生しました"
        )


@router.get("/charts/work-hours-trend", response_model=ChartDataResponse)
async def get_work_hours_trend(
    months: int = 6,
    employee_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> ChartDataResponse:
    """
    労働時間トレンドチャートデータを取得
    
    Args:
        months: 過去何ヶ月分のデータを取得するか
        employee_id: 従業員ID（省略時は全体）
        db: データベースセッション
    
    Returns:
        ChartDataResponse: チャートデータ
    """
    try:
        if months < 1 or months > 12:
            raise ValueError("期間は1〜12ヶ月の間で指定してください")
        
        service = AnalyticsService(db)
        chart_data = await service.get_work_hours_trend(
            months=months,
            employee_id=employee_id
        )
        return chart_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"労働時間トレンド取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="チャートデータの取得中にエラーが発生しました"
        )


@router.get("/charts/overtime-distribution", response_model=ChartDataResponse)
async def get_overtime_distribution(
    year: int,
    month: int,
    db: Session = Depends(get_db)
) -> ChartDataResponse:
    """
    残業時間分布チャートデータを取得
    
    Args:
        year: 年
        month: 月
        db: データベースセッション
    
    Returns:
        ChartDataResponse: チャートデータ
    """
    try:
        service = AnalyticsService(db)
        chart_data = await service.get_overtime_distribution(
            year=year,
            month=month
        )
        return chart_data
    except Exception as e:
        logger.error(f"残業時間分布取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="チャートデータの取得中にエラーが発生しました"
        )


@router.get("/charts/attendance-rate", response_model=ChartDataResponse)
async def get_attendance_rate_chart(
    months: int = 6,
    db: Session = Depends(get_db)
) -> ChartDataResponse:
    """
    出勤率チャートデータを取得
    
    Args:
        months: 過去何ヶ月分のデータを取得するか
        db: データベースセッション
    
    Returns:
        ChartDataResponse: チャートデータ
    """
    try:
        service = AnalyticsService(db)
        chart_data = await service.get_attendance_rate_trend(
            months=months
        )
        return chart_data
    except Exception as e:
        logger.error(f"出勤率チャート取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="チャートデータの取得中にエラーが発生しました"
        )


@router.get("/alerts/current")
async def get_current_alerts(
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    現在のアラートを取得
    
    Args:
        db: データベースセッション
    
    Returns:
        List[Dict[str, Any]]: アラートリスト
    """
    try:
        service = AnalyticsService(db)
        alerts = await service.get_current_alerts()
        return alerts
    except Exception as e:
        logger.error(f"アラート取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="アラートの取得中にエラーが発生しました"
        )


@router.get("/summary/realtime")
async def get_realtime_summary(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    リアルタイム勤怠状況サマリーを取得
    
    Args:
        db: データベースセッション
    
    Returns:
        Dict[str, Any]: リアルタイムサマリー
    """
    try:
        service = AnalyticsService(db)
        summary = await service.get_realtime_summary()
        return summary
    except Exception as e:
        logger.error(f"リアルタイムサマリー取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="リアルタイムサマリーの取得中にエラーが発生しました"
        )