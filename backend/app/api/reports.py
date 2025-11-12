"""
レポートAPIエンドポイント

日次・月次レポート、CSV出力、各種集計APIを提供
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
import io
import csv

from backend.app.database import get_db
from backend.app.schemas.report import (
    DailyReportRequest, DailyReportResponse,
    MonthlyReportRequest, MonthlyReportResponse,
    ExportRequest, ReportType
)
from backend.app.services.report_service import ReportService
from backend.app.services.export_service import ExportService
from backend.app.utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def reports_health_check():
    """レポートAPI ヘルスチェック"""
    return {"status": "healthy", "module": "reports"}


@router.post("/daily", response_model=List[DailyReportResponse])
async def generate_daily_report(
    request: DailyReportRequest,
    db: Session = Depends(get_db)
) -> List[DailyReportResponse]:
    """
    日次レポートを生成
    
    Args:
        request: 日次レポートリクエスト
        db: データベースセッション
    
    Returns:
        List[DailyReportResponse]: 日次レポートのリスト
    """
    try:
        service = ReportService(db)
        reports = await service.generate_daily_reports(
            target_date=request.target_date,
            employee_ids=request.employee_ids
        )
        return reports
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"日次レポート生成エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="日次レポートの生成中にエラーが発生しました"
        )


@router.get("/daily/{target_date}")
async def get_daily_report(
    target_date: date,
    employee_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[DailyReportResponse]:
    """
    特定日の日次レポートを取得
    
    Args:
        target_date: 対象日
        employee_id: 従業員ID（省略時は全員）
        db: データベースセッション
    
    Returns:
        List[DailyReportResponse]: 日次レポートのリスト
    """
    try:
        service = ReportService(db)
        employee_ids = [employee_id] if employee_id else None
        reports = await service.generate_daily_reports(
            target_date=target_date,
            employee_ids=employee_ids
        )
        return reports
    except Exception as e:
        logger.error(f"日次レポート取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="日次レポートの取得中にエラーが発生しました"
        )


@router.get("/daily/employee/{employee_id}")
async def get_employee_daily_reports(
    employee_id: str,
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db)
) -> List[DailyReportResponse]:
    """
    従業員の期間内日次レポートを取得
    
    Args:
        employee_id: 従業員ID
        from_date: 開始日
        to_date: 終了日
        db: データベースセッション
    
    Returns:
        List[DailyReportResponse]: 日次レポートのリスト
    """
    try:
        if from_date > to_date:
            raise ValueError("開始日は終了日より前である必要があります")
            
        if (to_date - from_date).days > 31:
            raise ValueError("期間は最大31日間までです")
            
        service = ReportService(db)
        reports = []
        
        current_date = from_date
        while current_date <= to_date:
            daily_reports = await service.generate_daily_reports(
                target_date=current_date,
                employee_ids=[employee_id]
            )
            reports.extend(daily_reports)
            current_date += timedelta(days=1)
        
        return reports
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"従業員日次レポート取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="日次レポートの取得中にエラーが発生しました"
        )


@router.post("/monthly", response_model=List[MonthlyReportResponse])
async def generate_monthly_report(
    request: MonthlyReportRequest,
    db: Session = Depends(get_db)
) -> List[MonthlyReportResponse]:
    """
    月次レポートを生成
    
    Args:
        request: 月次レポートリクエスト
        db: データベースセッション
    
    Returns:
        List[MonthlyReportResponse]: 月次レポートのリスト
    """
    try:
        service = ReportService(db)
        reports = await service.generate_monthly_reports(
            year=request.year,
            month=request.month,
            employee_ids=request.employee_ids
        )
        return reports
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"月次レポート生成エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="月次レポートの生成中にエラーが発生しました"
        )


@router.get("/monthly/{year}/{month}")
async def get_monthly_report(
    year: int,
    month: int,
    employee_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[MonthlyReportResponse]:
    """
    特定月の月次レポートを取得
    
    Args:
        year: 年
        month: 月
        employee_id: 従業員ID（省略時は全員）
        db: データベースセッション
    
    Returns:
        List[MonthlyReportResponse]: 月次レポートのリスト
    """
    try:
        if month < 1 or month > 12:
            raise ValueError("月は1〜12の間で指定してください")
            
        service = ReportService(db)
        employee_ids = [employee_id] if employee_id else None
        reports = await service.generate_monthly_reports(
            year=year,
            month=month,
            employee_ids=employee_ids
        )
        return reports
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"月次レポート取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="月次レポートの取得中にエラーが発生しました"
        )


@router.get("/monthly/employee/{employee_id}/{year}/{month}")
async def get_employee_monthly_report(
    employee_id: str,
    year: int,
    month: int,
    db: Session = Depends(get_db)
) -> MonthlyReportResponse:
    """
    従業員の月次レポートを取得
    
    Args:
        employee_id: 従業員ID
        year: 年
        month: 月
        db: データベースセッション
    
    Returns:
        MonthlyReportResponse: 月次レポート
    """
    try:
        service = ReportService(db)
        reports = await service.generate_monthly_reports(
            year=year,
            month=month,
            employee_ids=[employee_id]
        )
        
        if not reports:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された従業員の月次レポートが見つかりません"
            )
        
        return reports[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"従業員月次レポート取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="月次レポートの取得中にエラーが発生しました"
        )


@router.get("/export/daily/csv")
async def export_daily_csv(
    date: Optional[date] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    employee_ids: Optional[List[str]] = None,
    db: Session = Depends(get_db)
) -> Response:
    """
    日次レポートをCSV形式でエクスポート

    Args:
        date: 単一日指定（from_date/to_dateと排他）
        from_date: 開始日（dateと排他）
        to_date: 終了日（dateと排他）
        employee_ids: 従業員IDリスト（省略時は全員）
        db: データベースセッション

    Returns:
        Response: CSVファイル

    Raises:
        HTTPException: パラメータが不正な場合
    """
    # パラメータバリデーション
    if date is not None:
        if from_date is not None or to_date is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="dateパラメータとfrom_date/to_dateパラメータは同時に指定できません"
            )
        # 単一日指定の場合
        actual_from_date = date
        actual_to_date = date
        filename = f"daily_{date}.csv"
    elif from_date is not None and to_date is not None:
        # 期間指定の場合
        actual_from_date = from_date
        actual_to_date = to_date
        filename = f"daily_{from_date}_{to_date}.csv"
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dateパラメータ、またはfrom_dateとto_dateの両方を指定してください"
        )

    try:
        export_service = ExportService(db)
        csv_content = await export_service.export_daily_csv(
            from_date=actual_from_date,
            to_date=actual_to_date,
            employee_ids=employee_ids
        )

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"日次CSV出力エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CSVファイルの生成中にエラーが発生しました"
        )


@router.get("/export/monthly/csv")
async def export_monthly_csv(
    year: int,
    month: int,
    employee_ids: Optional[List[str]] = None,
    db: Session = Depends(get_db)
) -> Response:
    """
    月次レポートをCSV形式でエクスポート
    
    Args:
        year: 年
        month: 月
        employee_ids: 従業員IDリスト（省略時は全員）
        db: データベースセッション
    
    Returns:
        Response: CSVファイル
    """
    try:
        export_service = ExportService(db)
        csv_content = await export_service.export_monthly_csv(
            year=year,
            month=month,
            employee_ids=employee_ids
        )
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=monthly_report_{year}_{month:02d}.csv"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"月次CSV出力エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CSVファイルの生成中にエラーが発生しました"
        )


@router.get("/export/payroll/csv")
async def export_payroll_csv(
    year: int,
    month: int,
    db: Session = Depends(get_db)
) -> Response:
    """
    給与計算用CSVをエクスポート
    
    Args:
        year: 年
        month: 月
        db: データベースセッション
    
    Returns:
        Response: CSVファイル
    """
    try:
        export_service = ExportService(db)
        csv_content = await export_service.export_payroll_csv(
            year=year,
            month=month
        )
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=payroll_{year}_{month:02d}.csv"
            }
        )
    except Exception as e:
        logger.error(f"給与CSV出力エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="給与CSVファイルの生成中にエラーが発生しました"
        )