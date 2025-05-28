"""
勤怠管理システム FastAPIメインアプリケーション

APIサーバーのエントリーポイントとなるモジュールです。
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, status, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session

from attendance_system.config.config import settings
from attendance_system.app.database import init_db, get_db
from attendance_system.app.middleware.security import add_security_middleware


# ログ設定
logging.basicConfig(
    level=getattr(logging, getattr(settings, 'LOG_LEVEL', 'INFO').upper()),
    format=getattr(settings, 'LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションのライフサイクル管理
    
    起動時と終了時の処理を定義します。
    """
    # 起動時の処理
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 起動中...")
    
    # 設定の検証
    try:
        if hasattr(settings, 'validate'):
            settings.validate()
        logger.info("設定の検証が完了しました")
    except Exception as e:
        logger.error(f"設定エラー: {e}")
        raise
    
    # データベースの初期化
    try:
        init_db()
        logger.info("データベースの初期化が完了しました")
    except Exception as e:
        logger.error(f"データベース初期化エラー: {e}")
        raise
    
    logger.info("アプリケーションの起動が完了しました")
    
    yield
    
    # 終了時の処理
    logger.info("アプリケーションを終了しています...")


# FastAPIアプリケーションの作成
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="PaSoRi RC-S300を使用した勤怠管理システムのAPIサーバー",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# セキュリティミドルウェアの追加
add_security_middleware(app, settings)


# グローバル例外ハンドラー
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTPExceptionのカスタムハンドラー"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "status_code": exc.status_code,
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """バリデーションエラーのカスタムハンドラー"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "入力データの検証エラー",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": exc.errors(),
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般的な例外のカスタムハンドラー"""
    logger.error(f"予期しないエラー: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "内部サーバーエラーが発生しました",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }
        }
    )


# ルートエンドポイント
@app.get("/", tags=["ルート"])
async def root() -> Dict[str, str]:
    """
    APIルートエンドポイント
    
    Returns:
        Dict[str, str]: アプリケーション情報
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


# ヘルスチェックエンドポイント
@app.get("/health", tags=["ヘルスチェック"])
async def health_check() -> Dict[str, Any]:
    """
    ヘルスチェックエンドポイント
    
    Returns:
        Dict[str, Any]: システムの稼働状況
    """
    return {
        "status": "healthy",
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected",
        "pasori": "ready" if not getattr(settings, 'PASORI_MOCK_MODE', True) else "mock_mode"
    }


# 統合ヘルスチェックエンドポイント
@app.get("/health/integrated", tags=["ヘルスチェック"])
async def integrated_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    統合ヘルスチェックエンドポイント
    
    全サブシステムの健全性を詳細にチェックします。
    
    Returns:
        Dict[str, Any]: 統合システムの詳細な稼働状況
    """
    try:
        from attendance_system.app.health_check import get_integrated_health_status
        return await get_integrated_health_status(db)
    except Exception as e:
        logger.error(f"統合ヘルスチェックエラー: {e}")
        return {"status": "unhealthy", "error": str(e)}


# 詳細情報エンドポイント
@app.get("/info", tags=["システム情報"])
async def get_info() -> Dict[str, Any]:
    """
    システム詳細情報エンドポイント
    
    Returns:
        Dict[str, Any]: システムの詳細情報
    """
    return {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
        },
        "features": {
            "slack_notification": getattr(settings, 'is_slack_enabled', lambda: False)(),
            "pasori_mock_mode": getattr(settings, 'is_mock_mode', lambda: True)(),
        },
    }


# APIルーターの登録（エラーハンドリング付き）
try:
    from attendance_system.app.api import auth, punch, admin, reports, analytics
    
    app.include_router(
        auth.router,
        prefix=f"{settings.API_V1_PREFIX}/auth",
        tags=["認証"]
    )
    
    app.include_router(
        punch.router,
        prefix=f"{settings.API_V1_PREFIX}/punch",
        tags=["打刻"]
    )
    
    app.include_router(
        admin.router,
        prefix=f"{settings.API_V1_PREFIX}/admin",
        tags=["管理"]
    )
    
    app.include_router(
        reports.router,
        prefix=f"{settings.API_V1_PREFIX}/reports",
        tags=["レポート"]
    )
    
    app.include_router(
        analytics.router,
        prefix=f"{settings.API_V1_PREFIX}/analytics",
        tags=["分析"]
    )
except ImportError as e:
    logger.warning(f"一部のAPIルーターが利用できません: {e}")


def main():
    """CLIエントリーポイント"""
    import uvicorn
    
    uvicorn.run(
        "attendance_system.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=getattr(settings, 'LOG_LEVEL', 'INFO').lower()
    )


if __name__ == "__main__":
    main()