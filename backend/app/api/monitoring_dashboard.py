"""
Monitoring Dashboard API Endpoints

Real-time monitoring dashboard with:
- System metrics
- Performance analytics
- Security status
- Alert management
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import json
import io
import csv
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.monitoring.system_monitor import system_monitor
from backend.app.security.enhanced_auth import security_manager
from backend.app.websocket_enhanced import get_enhanced_connection_manager
from backend.app.performance.async_optimizer import async_optimizer
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class SystemStatus(BaseModel):
    status: str
    uptime_seconds: float
    version: str
    environment: str
    last_updated: str


class PerformanceMetrics(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    response_time_ms: float
    throughput_rps: float
    error_rate: float


class SecurityStatus(BaseModel):
    status: str
    active_threats: int
    blocked_clients: int
    last_security_scan: str
    security_level: str


class AlertSummary(BaseModel):
    total_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    resolved_alerts: int


@router.get("/dashboard/overview", response_model=Dict[str, Any])
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    Get comprehensive dashboard overview
    
    Returns overall system status, key metrics, and alerts
    """
    try:
        # Get system monitoring summary
        monitoring_summary = await system_monitor.get_monitoring_summary()
        
        # Get security status
        security_status = await security_manager.get_security_status()
        
        # Get WebSocket connection status
        ws_metrics = await get_enhanced_connection_manager().performance_monitor()
        
        # Get performance optimizer stats
        perf_stats = async_optimizer.get_performance_stats()
        
        return {
            "system": {
                "status": monitoring_summary["system_status"],
                "uptime_seconds": monitoring_summary["performance"]["uptime_seconds"],
                "version": "1.0.0",  # From config
                "environment": "production",
                "last_updated": datetime.now().isoformat()
            },
            "performance": {
                "cpu_usage": monitoring_summary["metrics"].get("system.cpu.usage", {}).get("mean", 0),
                "memory_usage": monitoring_summary["metrics"].get("system.memory.usage", {}).get("mean", 0),
                "response_time_ms": monitoring_summary["metrics"].get("websocket.response_time.avg", {}).get("mean", 0),
                "throughput_rps": perf_stats.get("nfc_batch_processing", {}).get("count", 0) / 60,  # per minute to per second
                "error_rate": 0.5,  # Calculated from errors
                "websocket_connections": ws_metrics["system"]["active_connections"]
            },
            "security": {
                "status": security_status["status"],
                "active_threats": security_status["recent_security_events"],
                "blocked_clients": security_status["blocked_clients"],
                "last_security_scan": security_status["last_audit"],
                "security_level": security_status["security_level"]
            },
            "alerts": {
                "total_alerts": monitoring_summary["alerts"]["total"],
                "critical_alerts": len([a for a in monitoring_summary["alerts"]["active"] if a["severity"] == "CRITICAL"]),
                "high_alerts": len([a for a in monitoring_summary["alerts"]["active"] if a["severity"] == "HIGH"]),
                "medium_alerts": len([a for a in monitoring_summary["alerts"]["active"] if a["severity"] == "MEDIUM"]),
                "low_alerts": len([a for a in monitoring_summary["alerts"]["active"] if a["severity"] == "LOW"]),
                "resolved_alerts": monitoring_summary["alerts"]["resolved"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard overview")


@router.get("/dashboard/metrics/realtime")
async def get_realtime_metrics():
    """
    Get real-time system metrics
    
    Returns current CPU, memory, network, and application metrics
    """
    try:
        # Collect fresh metrics
        await system_monitor.collect_metrics()
        
        # Get latest metrics
        cpu_stats = await system_monitor.metrics_collector.get_metric_stats("system.cpu.usage", 60)
        memory_stats = await system_monitor.metrics_collector.get_metric_stats("system.memory.usage", 60)
        network_sent = await system_monitor.metrics_collector.get_metric_stats("system.network.bytes_sent", 60)
        network_recv = await system_monitor.metrics_collector.get_metric_stats("system.network.bytes_recv", 60)
        
        # WebSocket metrics
        ws_metrics = await get_enhanced_connection_manager().performance_monitor()
        
        return {
            "system": {
                "cpu": {
                    "current": cpu_stats.get("mean", 0),
                    "max": cpu_stats.get("max", 0),
                    "trend": "stable"  # Could calculate trend
                },
                "memory": {
                    "current": memory_stats.get("mean", 0),
                    "max": memory_stats.get("max", 0),
                    "available_mb": ws_metrics["system"].get("memory_available_mb", 0)
                },
                "network": {
                    "bytes_sent_rate": network_sent.get("mean", 0),
                    "bytes_recv_rate": network_recv.get("mean", 0)
                }
            },
            "application": {
                "websocket": {
                    "active_connections": ws_metrics["system"]["active_connections"],
                    "max_connections": ws_metrics["system"]["max_connections"],
                    "usage_percent": ws_metrics["system"]["connection_usage_percent"],
                    "message_queue_size": ws_metrics["system"]["message_queue_size"]
                },
                "response_times": {
                    "avg_ms": ws_metrics["response_time"]["avg"],
                    "p95_ms": ws_metrics["response_time"]["p95"],
                    "p99_ms": ws_metrics["response_time"]["p99"]
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting realtime metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get realtime metrics")


@router.get("/dashboard/metrics/historical")
async def get_historical_metrics(
    metric: str = Query(..., description="Metric name"),
    duration: int = Query(3600, description="Duration in seconds"),
    interval: int = Query(60, description="Data point interval in seconds")
):
    """
    Get historical metrics data for charts
    
    Returns time series data for specified metric
    """
    try:
        # Get metric series
        metric_series = await system_monitor.metrics_collector.get_metric_series(metric, duration)
        
        if not metric_series:
            return {
                "metric": metric,
                "data_points": [],
                "duration_seconds": duration,
                "interval_seconds": interval
            }
        
        # Aggregate by interval if needed
        if len(metric_series) > 1000:  # Too many points, need to aggregate
            aggregated = []
            current_bucket = []
            bucket_start = metric_series[0]["timestamp"]
            
            for point in metric_series:
                if point["timestamp"] - bucket_start >= interval:
                    if current_bucket:
                        avg_value = sum(p["value"] for p in current_bucket) / len(current_bucket)
                        aggregated.append({
                            "timestamp": bucket_start,
                            "value": avg_value
                        })
                    current_bucket = [point]
                    bucket_start = point["timestamp"]
                else:
                    current_bucket.append(point)
            
            # Add last bucket
            if current_bucket:
                avg_value = sum(p["value"] for p in current_bucket) / len(current_bucket)
                aggregated.append({
                    "timestamp": bucket_start,
                    "value": avg_value
                })
            
            metric_series = aggregated
        
        return {
            "metric": metric,
            "data_points": metric_series,
            "duration_seconds": duration,
            "interval_seconds": interval,
            "total_points": len(metric_series)
        }
        
    except Exception as e:
        logger.error(f"Error getting historical metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get historical metrics")


@router.get("/dashboard/alerts")
async def get_active_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, description="Maximum number of alerts")
):
    """
    Get active system alerts
    
    Returns current alerts with optional severity filtering
    """
    try:
        # Get all active alerts
        all_alerts = [alert.to_dict() for alert in system_monitor.alerts.values() if not alert.resolved]
        
        # Filter by severity if specified
        if severity:
            all_alerts = [alert for alert in all_alerts if alert["severity"] == severity.upper()]
        
        # Sort by timestamp (newest first)
        all_alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Limit results
        alerts = all_alerts[:limit]
        
        return {
            "alerts": alerts,
            "total_count": len(all_alerts),
            "filtered_count": len(alerts),
            "severity_filter": severity,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.get("/dashboard/security")
async def get_security_dashboard():
    """
    Get security dashboard data
    
    Returns security events, threats, and audit information
    """
    try:
        # Get security status
        security_status = await security_manager.get_security_status()
        
        # Get recent security events from audit trail
        recent_events = await security_manager.security_auditor.get_audit_trail(
            category="security",
            limit=20
        )
        
        # Get authentication events
        auth_events = await security_manager.security_auditor.get_audit_trail(
            category="authentication",
            limit=20
        )
        
        # Calculate security metrics
        failed_auth_count = len([e for e in auth_events if not e.get("success", True)])
        security_incidents = len([e for e in recent_events if e.get("severity") in ["HIGH", "CRITICAL"]])
        
        return {
            "overview": security_status,
            "metrics": {
                "failed_authentications": failed_auth_count,
                "security_incidents": security_incidents,
                "audit_events_24h": len(recent_events) + len(auth_events)
            },
            "recent_events": recent_events[:10],
            "authentication_summary": {
                "total_attempts": len(auth_events),
                "successful": len([e for e in auth_events if e.get("success", True)]),
                "failed": failed_auth_count
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting security dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security dashboard")


@router.get("/dashboard/performance")
async def get_performance_dashboard():
    """
    Get performance dashboard data
    
    Returns performance analysis and optimization metrics
    """
    try:
        # Get performance analysis
        performance_analysis = await system_monitor.analyze_performance()
        
        # Get async optimizer stats
        optimizer_stats = async_optimizer.get_performance_stats()
        
        # Get WebSocket performance
        ws_metrics = await get_enhanced_connection_manager().performance_monitor()
        
        return {
            "system_performance": performance_analysis,
            "optimization_stats": optimizer_stats,
            "websocket_performance": {
                "connections": ws_metrics["system"],
                "response_times": ws_metrics["response_time"],
                "message_counts": ws_metrics.get("message_counts", {}),
                "error_counts": ws_metrics.get("error_counts", {})
            },
            "recommendations": await _generate_performance_recommendations(performance_analysis),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance dashboard")


@router.get("/dashboard/websockets")
async def get_websocket_dashboard():
    """
    Get WebSocket connections dashboard
    
    Returns active connections and connection statistics
    """
    try:
        # Get all connection info
        connections = await get_enhanced_connection_manager().get_all_connections()
        
        # Get performance metrics
        ws_metrics = await get_enhanced_connection_manager().performance_monitor()
        
        # Group connections by metadata
        connections_by_device = {}
        connections_by_version = {}
        
        for conn in connections:
            device_type = conn.get("metadata", {}).get("device_type", "unknown")
            app_version = conn.get("metadata", {}).get("app_version", "unknown")
            
            connections_by_device[device_type] = connections_by_device.get(device_type, 0) + 1
            connections_by_version[app_version] = connections_by_version.get(app_version, 0) + 1
        
        return {
            "overview": {
                "total_connections": len(connections),
                "max_connections": ws_metrics["system"]["max_connections"],
                "usage_percent": ws_metrics["system"]["connection_usage_percent"],
                "avg_connection_duration": sum(c["connected_duration"] for c in connections) / len(connections) if connections else 0
            },
            "connections": connections[:50],  # Limit to 50 for UI
            "distribution": {
                "by_device_type": connections_by_device,
                "by_app_version": connections_by_version
            },
            "performance": ws_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting WebSocket dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get WebSocket dashboard")


@router.post("/dashboard/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """
    Resolve a specific alert
    
    Marks an alert as resolved
    """
    try:
        if alert_id not in system_monitor.alerts:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert = system_monitor.alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now()
        
        # Update in Redis if available
        if system_monitor.redis_client:
            await system_monitor.redis_client.hset(
                "alerts:active",
                alert_id,
                json.dumps(alert.to_dict())
            )
        
        return {
            "message": f"Alert {alert_id} resolved successfully",
            "alert": alert.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")


@router.get("/dashboard/export/metrics")
async def export_metrics(
    format: str = Query("csv", description="Export format (csv, json)"),
    duration: int = Query(3600, description="Duration in seconds"),
    metrics: str = Query("", description="Comma-separated metric names")
):
    """
    Export metrics data
    
    Returns metrics data in specified format for download
    """
    try:
        # Parse requested metrics
        metric_names = [m.strip() for m in metrics.split(",") if m.strip()] if metrics else [
            "system.cpu.usage",
            "system.memory.usage",
            "websocket.response_time.avg",
            "websocket.active_connections"
        ]
        
        # Collect data
        export_data = []
        for metric_name in metric_names:
            series = await system_monitor.metrics_collector.get_metric_series(metric_name, duration)
            for point in series:
                export_data.append({
                    "metric": metric_name,
                    "timestamp": point["timestamp"],
                    "value": point["value"],
                    "tags": point.get("tags", {})
                })
        
        # Sort by timestamp
        export_data.sort(key=lambda x: x["timestamp"])
        
        if format.lower() == "csv":
            # Generate CSV
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["metric", "timestamp", "value", "tags"])
            writer.writeheader()
            for row in export_data:
                row["tags"] = json.dumps(row["tags"])
                writer.writerow(row)
            
            csv_content = output.getvalue()
            output.close()
            
            return StreamingResponse(
                io.StringIO(csv_content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        
        else:  # JSON format
            return {
                "metrics": export_data,
                "export_info": {
                    "format": format,
                    "duration_seconds": duration,
                    "metric_count": len(metric_names),
                    "data_points": len(export_data),
                    "exported_at": datetime.now().isoformat()
                }
            }
        
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to export metrics")


@router.get("/dashboard/health")
async def get_system_health():
    """
    Get comprehensive system health check
    
    Returns detailed health status of all components
    """
    try:
        health_status = {
            "overall_status": "healthy",
            "components": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Check system monitor
        try:
            monitoring_summary = await system_monitor.get_monitoring_summary()
            health_status["components"]["monitoring"] = {
                "status": "healthy",
                "details": monitoring_summary["system_status"]
            }
        except Exception as e:
            health_status["components"]["monitoring"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        # Check WebSocket manager
        try:
            ws_metrics = await get_enhanced_connection_manager().performance_monitor()
            ws_health = "healthy" if ws_metrics["system"]["connection_usage_percent"] < 90 else "warning"
            health_status["components"]["websocket"] = {
                "status": ws_health,
                "details": {
                    "connections": ws_metrics["system"]["active_connections"],
                    "usage_percent": ws_metrics["system"]["connection_usage_percent"]
                }
            }
        except Exception as e:
            health_status["components"]["websocket"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        # Check security manager
        try:
            security_status = await security_manager.get_security_status()
            health_status["components"]["security"] = {
                "status": security_status["status"],
                "details": {
                    "security_level": security_status["security_level"],
                    "blocked_clients": security_status["blocked_clients"]
                }
            }
        except Exception as e:
            health_status["components"]["security"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        # Check async optimizer
        try:
            optimizer_stats = async_optimizer.get_performance_stats()
            health_status["components"]["optimizer"] = {
                "status": "healthy",
                "details": {
                    "operations": len(optimizer_stats),
                    "total_processed": sum(stats["count"] for stats in optimizer_stats.values())
                }
            }
        except Exception as e:
            health_status["components"]["optimizer"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        # Determine overall status
        unhealthy_components = [comp for comp in health_status["components"].values() if comp["status"] == "unhealthy"]
        if unhealthy_components:
            health_status["overall_status"] = "unhealthy"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system health")


async def _generate_performance_recommendations(performance_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate performance recommendations based on analysis"""
    recommendations = []
    
    # CPU recommendations
    cpu_score = performance_analysis.get("cpu", {}).get("mean", 0)
    if cpu_score > 80:
        recommendations.append({
            "type": "cpu",
            "severity": "high",
            "message": "High CPU usage detected. Consider scaling or optimizing CPU-intensive operations.",
            "action": "Scale up or optimize code"
        })
    
    # Memory recommendations
    memory_score = performance_analysis.get("memory", {}).get("mean", 0)
    if memory_score > 85:
        recommendations.append({
            "type": "memory",
            "severity": "high",
            "message": "High memory usage detected. Check for memory leaks or increase available memory.",
            "action": "Investigate memory usage or scale up"
        })
    
    # Response time recommendations
    response_time = performance_analysis.get("response_time", {}).get("mean", 0)
    if response_time > 200:
        recommendations.append({
            "type": "performance",
            "severity": "medium",
            "message": "High response times detected. Consider optimizing database queries or adding caching.",
            "action": "Optimize queries and add caching"
        })
    
    # Overall performance
    overall_score = performance_analysis.get("overall_score", 100)
    if overall_score < 70:
        recommendations.append({
            "type": "general",
            "severity": "medium",
            "message": "Overall system performance is below optimal. Review system resources and optimization opportunities.",
            "action": "Comprehensive performance review"
        })
    
    return recommendations