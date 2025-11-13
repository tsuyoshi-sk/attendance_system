"""
勤怠管理システム FastAPIメインアプリケーション

APIサーバーのエントリーポイントとなるモジュールです。
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.config import config
from backend.app.database import init_db, get_db
from backend.app.api import punch, admin, auth, reports, analytics
from backend.app.health_check import get_integrated_health_status
from backend.app.middleware.security_async import add_security_middleware
from backend.app.security.ratelimit import limiter


# ログ設定
try:
    # LOG_FORMATが存在しない場合のデフォルト値
    log_format = getattr(config, 'LOG_FORMAT', '%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    log_level = getattr(config, 'LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
        ]
    )
except Exception as e:
    # ログ設定が失敗した場合のフォールバック
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    logging.warning(f"Failed to configure logging with config values: {e}")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションのライフサイクル管理
    
    起動時と終了時の処理を定義します。
    """
    # 起動時の処理
    logger.info(f"{config.APP_NAME} v{config.APP_VERSION} 起動中...")
    
    # データベースの初期化
    try:
        init_db()
        logger.info("データベースの初期化が完了しました")
    except Exception as e:
        logger.error(f"データベース初期化エラー: {e}")
        raise
    
    # TODO: 初期データ作成処理があれば追加
    
    logger.info("アプリケーションの起動が完了しました")
    
    yield
    
    # 終了時の処理
    logger.info("アプリケーションを終了しています...")


# FastAPIアプリケーションの作成
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="PaSoRi RC-S380/RC-S300を使用した勤怠管理システムのAPIサーバー",
    lifespan=lifespan,
    # ドキュメントを常時有効化
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# レート制限をFastAPIアプリに登録
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """リクエストの処理時間をレスポンスヘッダーに追加するミドルウェア"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"

    # 遅いリクエストの警告（1秒超）
    if process_time > 1.0:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {process_time:.2f}s (client: {request.client.host if request.client else 'unknown'})"
        )

    return response

# セキュリティミドルウェアの追加
add_security_middleware(app, config)


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
    sanitized_errors = []
    for error in exc.errors():
        error_copy = error.copy()
        ctx = error_copy.get("ctx")
        if ctx:
            error_copy["ctx"] = {
                key: str(value) if isinstance(value, Exception) else value
                for key, value in ctx.items()
            }
        sanitized_errors.append(error_copy)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "入力データの検証エラー",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": sanitized_errors,
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
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
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
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
        "database": "connected",  # TODO: 実際のDB接続チェックを実装
        "pasori": "ready" if not config.PASORI_MOCK_MODE else "mock_mode"
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
    from backend.app.health_check import get_integrated_health_status
    return get_integrated_health_status(db)


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
            "name": config.APP_NAME,
            "version": config.APP_VERSION,
            "debug": config.DEBUG,
        },
        "features": {
            "slack_notification": config.is_slack_enabled(),
            "pasori_mock_mode": config.is_mock_mode(),
        },
        "settings": {
            "business_hours": {
                "start": str(config.BUSINESS_START_TIME),
                "end": str(config.BUSINESS_END_TIME),
            },
            "break_time": {
                "start": str(config.BREAK_START_TIME),
                "end": str(config.BREAK_END_TIME),
            },
            "rounding": {
                "daily_minutes": config.DAILY_ROUND_MINUTES,
                "monthly_minutes": config.MONTHLY_ROUND_MINUTES,
            },
            "overtime_rates": {
                "normal": config.OVERTIME_RATE_NORMAL,
                "late": config.OVERTIME_RATE_LATE,
                "night": config.NIGHT_RATE,
                "holiday": config.HOLIDAY_RATE,
            }
        }
    }


# デバッグ用エンドポイント
@app.get("/debug/routes")
async def debug_routes():
    """利用可能なルート一覧を返す"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods)
            })
    return {"routes": routes}


# APIルーターの登録
app.include_router(
    auth.router,
    prefix=f"{config.API_V1_PREFIX}/auth",
    tags=["認証"]
)

app.include_router(
    punch.router,
    prefix=f"{config.API_V1_PREFIX}/punch",
    tags=["打刻"]
)

app.include_router(
    admin.router,
    prefix=f"{config.API_V1_PREFIX}/admin",
    tags=["管理"]
)

app.include_router(
    reports.router,
    prefix=f"{config.API_V1_PREFIX}/reports",
    tags=["レポート"]
)

app.include_router(
    analytics.router,
    prefix=f"{config.API_V1_PREFIX}/analytics",
    tags=["分析"]
)


# SPA統合（フロントエンド配信）
try:
    from .spa_mount_runtime import apply_spa_mount  # type: ignore
    apply_spa_mount(app)
    logger.info("SPA統合が完了しました")
except Exception as e:
    logger.warning(f"SPA統合をスキップしました: {e}")


def main():
    """CLIエントリーポイント"""
    import uvicorn
    
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
