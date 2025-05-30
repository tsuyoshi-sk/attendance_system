"""
Enhanced FastAPI Main Application

Integrated main application with all performance and security enhancements:
- Enhanced WebSocket management
- Advanced security
- Real-time monitoring
- Performance optimization
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import time
import uuid

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.config import config
from backend.app.database import init_db, get_db

# Import existing API routers
from backend.app.api import punch, admin, auth, reports, analytics, punch_monitoring

# Import enhanced modules
from backend.app.api import nfc_enhanced, monitoring_dashboard
from backend.app.websocket_enhanced import enhanced_connection_manager, websocket_manager
from backend.app.monitoring.system_monitor import system_monitor
from backend.app.security.enhanced_auth import security_manager
from backend.app.performance.async_optimizer import async_optimizer
from backend.app.logging.enhanced_logger import enhanced_logger, log_api_request, record_api_metric


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track API performance"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Set logging context
        enhanced_logger.set_context(request_id=request_id)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Log API request
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time_ms=response_time * 1000
            )
            
            # Record metrics for monitoring
            await record_api_metric(
                endpoint=request.url.path,
                response_time=response_time,
                status_code=response.status_code
            )
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{response_time:.3f}"
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Log error
            enhanced_logger.log_exception(e, {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "response_time": response_time
            })
            
            # Record error metric
            await record_api_metric(
                endpoint=request.url.path,
                response_time=response_time,
                status_code=500
            )
            
            raise
        finally:
            # Clear logging context
            enhanced_logger.clear_context()


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for enhanced protection"""
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        
        # Check if IP is blocked (basic implementation)
        # In production, this would check Redis/database
        
        # Validate request size
        if hasattr(request, "body"):
            try:
                body = await request.body()
                if len(body) > 10 * 1024 * 1024:  # 10MB limit
                    raise HTTPException(
                        status_code=413,
                        detail="Request entity too large"
                    )
            except Exception:
                pass  # Body might not be available
        
        # Add security headers
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Enhanced application lifecycle management
    """
    # Startup
    enhanced_logger.logger.info(f"{config.APP_NAME} v{config.APP_VERSION} starting with enhancements...")
    
    try:
        # Validate configuration
        config.validate()
        enhanced_logger.logger.info("Configuration validated")
        
        # Initialize database
        init_db()
        enhanced_logger.logger.info("Database initialized")
        
        # Initialize enhanced components
        enhanced_logger.logger.info("Initializing enhanced components...")
        
        # Initialize WebSocket manager
        await enhanced_connection_manager.initialize()
        enhanced_logger.logger.info("Enhanced WebSocket manager initialized")
        
        # Initialize monitoring system
        await system_monitor.initialize()
        enhanced_logger.logger.info("System monitor initialized")
        
        # Initialize security manager
        await security_manager.initialize()
        enhanced_logger.logger.info("Security manager initialized")
        
        # Initialize performance optimizer
        await async_optimizer.initialize()
        enhanced_logger.logger.info("Async optimizer initialized")
        
        enhanced_logger.logger.info("All enhanced components initialized successfully")
        
        # Start background tasks
        asyncio.create_task(background_tasks())
        
        enhanced_logger.logger.info("Enhanced application startup completed")
        
    except Exception as e:
        enhanced_logger.logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    enhanced_logger.logger.info("Enhanced application shutting down...")
    
    try:
        # Cleanup enhanced components
        await enhanced_connection_manager.cleanup()
        await system_monitor.cleanup()
        await async_optimizer.cleanup()
        
        enhanced_logger.logger.info("Enhanced application shutdown completed")
        
    except Exception as e:
        enhanced_logger.logger.error(f"Shutdown error: {e}")


async def background_tasks():
    """Background tasks for enhanced features"""
    tasks = [
        # Periodic metrics collection
        periodic_metrics_collection(),
        
        # Security monitoring
        periodic_security_monitoring(),
        
        # Performance optimization
        periodic_performance_optimization(),
        
        # Log cleanup
        periodic_log_cleanup()
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)


async def periodic_metrics_collection():
    """Collect metrics periodically"""
    while True:
        try:
            await system_monitor.collect_metrics()
            await asyncio.sleep(30)  # Every 30 seconds
        except Exception as e:
            enhanced_logger.logger.error(f"Metrics collection error: {e}")
            await asyncio.sleep(60)


async def periodic_security_monitoring():
    """Monitor security events periodically"""
    while True:
        try:
            # Check for security anomalies
            anomalies = await system_monitor.detect_anomalies()
            if anomalies:
                enhanced_logger.logger.warning(f"Security anomalies detected: {len(anomalies)}")
            
            await asyncio.sleep(60)  # Every minute
        except Exception as e:
            enhanced_logger.logger.error(f"Security monitoring error: {e}")
            await asyncio.sleep(120)


async def periodic_performance_optimization():
    """Optimize performance periodically"""
    while True:
        try:
            # Trigger cache cleanup or optimization
            await async_optimizer.run_in_thread_pool(lambda: None)  # Placeholder
            await asyncio.sleep(300)  # Every 5 minutes
        except Exception as e:
            enhanced_logger.logger.error(f"Performance optimization error: {e}")
            await asyncio.sleep(600)


async def periodic_log_cleanup():
    """Clean up old logs periodically"""
    while True:
        try:
            # Compress old audit files
            await enhanced_logger.audit.compress_old_audit_files()
            await asyncio.sleep(3600)  # Every hour
        except Exception as e:
            enhanced_logger.logger.error(f"Log cleanup error: {e}")
            await asyncio.sleep(7200)


# Create FastAPI application
app = FastAPI(
    title=f"{config.APP_NAME} Enhanced",
    version=config.APP_VERSION,
    description="Enhanced PaSoRi RC-S380/RC-S300 勤怠管理システム with performance and security optimizations",
    lifespan=lifespan,
    docs_url="/docs" if config.DEBUG else None,
    redoc_url="/redoc" if config.DEBUG else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(PerformanceMiddleware)
app.add_middleware(SecurityMiddleware)


# Enhanced exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Enhanced HTTP exception handler"""
    # Log security events for certain errors
    if exc.status_code == 401:
        await enhanced_logger.audit.log_audit_event(
            category="security",
            action="unauthorized_access",
            actor=request.client.host,
            target=request.url.path,
            result="denied"
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "status_code": exc.status_code,
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation error handler"""
    enhanced_logger.logger.warning(
        "Validation error",
        path=request.url.path,
        errors=exc.errors()
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "入力データの検証エラー",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": exc.errors(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Enhanced general exception handler"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    enhanced_logger.log_exception(exc, {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host
    })
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "内部サーバーエラーが発生しました",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "request_id": request_id
            }
        }
    )


# Enhanced root endpoints
@app.get("/", tags=["ルート"])
async def root() -> Dict[str, str]:
    """Enhanced API root endpoint"""
    return {
        "name": f"{config.APP_NAME} Enhanced",
        "version": config.APP_VERSION,
        "status": "running",
        "features": [
            "enhanced_websocket",
            "advanced_security",
            "real_time_monitoring",
            "performance_optimization"
        ]
    }


@app.get("/health/enhanced", tags=["ヘルスチェック"])
async def enhanced_health_check() -> Dict[str, Any]:
    """Enhanced health check endpoint"""
    try:
        # Check all enhanced components
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {}
        }
        
        # Check WebSocket manager
        try:
            ws_metrics = await enhanced_connection_manager.performance_monitor()
            health_status["components"]["websocket"] = {
                "status": "healthy",
                "connections": ws_metrics["system"]["active_connections"],
                "max_connections": ws_metrics["system"]["max_connections"]
            }
        except Exception as e:
            health_status["components"]["websocket"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check monitoring system
        try:
            monitoring_summary = await system_monitor.get_monitoring_summary()
            health_status["components"]["monitoring"] = {
                "status": "healthy",
                "system_status": monitoring_summary["system_status"]
            }
        except Exception as e:
            health_status["components"]["monitoring"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check security manager
        try:
            security_status = await security_manager.get_security_status()
            health_status["components"]["security"] = {
                "status": security_status["status"],
                "security_level": security_status["security_level"]
            }
        except Exception as e:
            health_status["components"]["security"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        enhanced_logger.log_exception(e)
        raise HTTPException(
            status_code=500,
            detail="Health check failed"
        )


# Include API routers
# Original routers
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

app.include_router(
    punch_monitoring.router,
    prefix=f"{config.API_V1_PREFIX}/monitoring",
    tags=["リアルタイム監視"]
)

# Enhanced routers
app.include_router(
    nfc_enhanced.router,
    prefix=f"{config.API_V1_PREFIX}/nfc-enhanced",
    tags=["NFC拡張"]
)

app.include_router(
    monitoring_dashboard.router,
    prefix=f"{config.API_V1_PREFIX}/monitoring",
    tags=["監視ダッシュボード"]
)


if __name__ == "__main__":
    import uvicorn
    
    enhanced_logger.logger.info("Starting enhanced FastAPI application")
    
    uvicorn.run(
        "main_enhanced:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower(),
        access_log=True
    )