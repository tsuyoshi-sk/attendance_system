"""
Real-time System Monitoring and Metrics Collection

Comprehensive monitoring system for:
- Performance metrics
- Resource utilization
- Anomaly detection
- Auto-recovery mechanisms
"""

import asyncio
import psutil
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from collections import deque, defaultdict
import numpy as np
from dataclasses import dataclass, asdict
import aiohttp
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    tags: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Alert:
    """System alert"""
    id: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    type: str
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime
    auto_recovery_enabled: bool = True
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


class MetricsCollector:
    """Collects and stores system metrics"""
    
    def __init__(self, window_size: int = 3600):  # 1 hour window
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.window_size = window_size
        self._lock = asyncio.Lock()
    
    async def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric value"""
        async with self._lock:
            metric_point = MetricPoint(
                timestamp=time.time(),
                value=value,
                tags=tags or {}
            )
            self.metrics[name].append(metric_point)
    
    async def get_metric_stats(self, name: str, duration_seconds: int = 300) -> Dict[str, float]:
        """Get statistics for a metric over the specified duration"""
        async with self._lock:
            if name not in self.metrics:
                return {}
            
            current_time = time.time()
            cutoff_time = current_time - duration_seconds
            
            # Filter metrics within the time window
            values = [
                point.value for point in self.metrics[name]
                if point.timestamp >= cutoff_time
            ]
            
            if not values:
                return {}
            
            return {
                "count": len(values),
                "mean": np.mean(values),
                "min": np.min(values),
                "max": np.max(values),
                "std": np.std(values),
                "p50": np.percentile(values, 50),
                "p95": np.percentile(values, 95),
                "p99": np.percentile(values, 99),
            }
    
    async def get_metric_series(self, name: str, duration_seconds: int = 300) -> List[Dict[str, Any]]:
        """Get time series data for a metric"""
        async with self._lock:
            if name not in self.metrics:
                return []
            
            current_time = time.time()
            cutoff_time = current_time - duration_seconds
            
            return [
                point.to_dict()
                for point in self.metrics[name]
                if point.timestamp >= cutoff_time
            ]


class AnomalyDetector:
    """Detect anomalies in metrics using statistical methods"""
    
    def __init__(self, sensitivity: float = 2.5):
        self.sensitivity = sensitivity  # Z-score threshold
        self.baseline_window = 3600  # 1 hour for baseline
        self.min_samples = 30
    
    async def detect_anomaly(self, 
                           metric_name: str, 
                           current_value: float, 
                           historical_values: List[float]) -> Optional[Dict[str, Any]]:
        """Detect if current value is anomalous"""
        if len(historical_values) < self.min_samples:
            return None
        
        mean = np.mean(historical_values)
        std = np.std(historical_values)
        
        if std == 0:
            return None
        
        z_score = abs((current_value - mean) / std)
        
        if z_score > self.sensitivity:
            return {
                "metric": metric_name,
                "current_value": current_value,
                "mean": mean,
                "std": std,
                "z_score": z_score,
                "severity": self._calculate_severity(z_score),
                "direction": "high" if current_value > mean else "low"
            }
        
        return None
    
    def _calculate_severity(self, z_score: float) -> str:
        """Calculate anomaly severity based on z-score"""
        if z_score > 4:
            return "CRITICAL"
        elif z_score > 3:
            return "HIGH"
        elif z_score > 2.5:
            return "MEDIUM"
        else:
            return "LOW"


class SystemMonitor:
    """Main system monitoring class"""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 alert_webhook_url: Optional[str] = None):
        # Metrics collection
        self.metrics_collector = MetricsCollector()
        self.anomaly_detector = AnomalyDetector()
        
        # Redis for distributed state
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # Alerts
        self.alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable] = []
        self.alert_webhook_url = alert_webhook_url
        
        # Thresholds
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time_ms': 200.0,
            'error_rate': 5.0,
            'websocket_connections': 180,  # 90% of max
            'api_requests_per_second': 1000,
        }
        
        # Monitoring tasks
        self.monitoring_tasks: List[asyncio.Task] = []
        self.collection_interval = 5  # seconds
        
        # Auto-recovery actions
        self.recovery_actions = {
            'high_memory': self._recover_high_memory,
            'high_connections': self._recover_high_connections,
            'high_error_rate': self._recover_high_error_rate,
        }
    
    async def initialize(self):
        """Initialize the monitoring system"""
        try:
            # Initialize Redis
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Monitoring system Redis connection established")
            
            # Start monitoring tasks
            self.monitoring_tasks = [
                asyncio.create_task(self._collect_system_metrics()),
                asyncio.create_task(self._collect_application_metrics()),
                asyncio.create_task(self._anomaly_detection_loop()),
                asyncio.create_task(self._alert_processing_loop()),
            ]
            
            logger.info("System monitoring initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup monitoring resources"""
        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
    
    async def collect_metrics(self):
        """Public method to trigger metric collection"""
        await asyncio.gather(
            self._collect_system_metrics_once(),
            self._collect_application_metrics_once(),
            return_exceptions=True
        )
    
    async def _collect_system_metrics(self):
        """Continuously collect system metrics"""
        while True:
            try:
                await self._collect_system_metrics_once()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_system_metrics_once(self):
        """Collect system metrics once"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        await self.metrics_collector.record_metric("system.cpu.usage", cpu_percent)
        
        # Per-CPU metrics
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        for i, percent in enumerate(cpu_per_core):
            await self.metrics_collector.record_metric(
                "system.cpu.core.usage",
                percent,
                tags={"core": str(i)}
            )
        
        # Memory metrics
        memory = psutil.virtual_memory()
        await self.metrics_collector.record_metric("system.memory.usage", memory.percent)
        await self.metrics_collector.record_metric("system.memory.available_mb", memory.available / 1024 / 1024)
        await self.metrics_collector.record_metric("system.memory.used_mb", memory.used / 1024 / 1024)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        await self.metrics_collector.record_metric("system.disk.usage", disk.percent)
        await self.metrics_collector.record_metric("system.disk.free_gb", disk.free / 1024 / 1024 / 1024)
        
        # Network metrics
        net_io = psutil.net_io_counters()
        await self.metrics_collector.record_metric("system.network.bytes_sent", net_io.bytes_sent)
        await self.metrics_collector.record_metric("system.network.bytes_recv", net_io.bytes_recv)
        await self.metrics_collector.record_metric("system.network.packets_sent", net_io.packets_sent)
        await self.metrics_collector.record_metric("system.network.packets_recv", net_io.packets_recv)
        
        # Process metrics
        process = psutil.Process()
        await self.metrics_collector.record_metric("process.cpu.usage", process.cpu_percent())
        await self.metrics_collector.record_metric("process.memory.rss_mb", process.memory_info().rss / 1024 / 1024)
        await self.metrics_collector.record_metric("process.threads", process.num_threads())
        await self.metrics_collector.record_metric("process.fds", process.num_fds() if hasattr(process, 'num_fds') else 0)
    
    async def _collect_application_metrics(self):
        """Continuously collect application metrics"""
        while True:
            try:
                await self._collect_application_metrics_once()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting application metrics: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_application_metrics_once(self):
        """Collect application metrics once"""
        # Get metrics from enhanced connection manager
        from backend.app.websocket_enhanced import enhanced_connection_manager
        
        if enhanced_connection_manager:
            perf_data = await enhanced_connection_manager.performance_monitor()
            
            # WebSocket metrics
            await self.metrics_collector.record_metric(
                "websocket.active_connections",
                perf_data["system"]["active_connections"]
            )
            await self.metrics_collector.record_metric(
                "websocket.connection_usage_percent",
                perf_data["system"]["connection_usage_percent"]
            )
            await self.metrics_collector.record_metric(
                "websocket.message_queue_size",
                perf_data["system"]["message_queue_size"]
            )
            
            # Response time metrics
            if perf_data["response_time"]["avg"] > 0:
                await self.metrics_collector.record_metric(
                    "websocket.response_time.avg",
                    perf_data["response_time"]["avg"]
                )
                await self.metrics_collector.record_metric(
                    "websocket.response_time.p95",
                    perf_data["response_time"]["p95"]
                )
                await self.metrics_collector.record_metric(
                    "websocket.response_time.p99",
                    perf_data["response_time"]["p99"]
                )
            
            # Redis metrics
            if "redis" in perf_data:
                await self.metrics_collector.record_metric(
                    "redis.connected_clients",
                    perf_data["redis"]["redis_connected_clients"]
                )
                await self.metrics_collector.record_metric(
                    "redis.memory_used_mb",
                    perf_data["redis"]["redis_used_memory_mb"]
                )
        
        # Collect from Redis if available
        if self.redis_client:
            try:
                # Get API metrics from Redis
                api_metrics = await self.redis_client.hgetall("metrics:api")
                for endpoint, count in api_metrics.items():
                    await self.metrics_collector.record_metric(
                        "api.requests",
                        float(count),
                        tags={"endpoint": endpoint}
                    )
                
                # Get error counts
                error_counts = await self.redis_client.hgetall("metrics:errors")
                total_errors = sum(int(count) for count in error_counts.values())
                await self.metrics_collector.record_metric("api.errors.total", total_errors)
                
            except Exception as e:
                logger.error(f"Error collecting Redis metrics: {e}")
    
    async def analyze_performance(self) -> Dict[str, Any]:
        """Analyze overall system performance"""
        # Get recent metrics
        cpu_stats = await self.metrics_collector.get_metric_stats("system.cpu.usage", 300)
        memory_stats = await self.metrics_collector.get_metric_stats("system.memory.usage", 300)
        response_time_stats = await self.metrics_collector.get_metric_stats("websocket.response_time.avg", 300)
        
        # Calculate performance score (0-100)
        scores = []
        
        # CPU score (lower is better)
        if cpu_stats:
            cpu_score = max(0, 100 - cpu_stats["mean"])
            scores.append(cpu_score)
        
        # Memory score (lower is better)
        if memory_stats:
            memory_score = max(0, 100 - memory_stats["mean"])
            scores.append(memory_score)
        
        # Response time score (lower is better, scaled)
        if response_time_stats:
            # Assume 100ms is good, 500ms is bad
            rt_score = max(0, 100 - (response_time_stats["mean"] / 5))
            scores.append(rt_score)
        
        overall_score = np.mean(scores) if scores else 0
        
        return {
            "overall_score": round(overall_score, 2),
            "cpu": cpu_stats,
            "memory": memory_stats,
            "response_time": response_time_stats,
            "status": self._get_performance_status(overall_score),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_performance_status(self, score: float) -> str:
        """Get performance status based on score"""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 50:
            return "fair"
        else:
            return "poor"
    
    async def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in all metrics"""
        anomalies = []
        
        for metric_name, metric_deque in self.metrics_collector.metrics.items():
            if len(metric_deque) < 30:
                continue
            
            # Get recent values
            values = [point.value for point in list(metric_deque)[-100:]]
            current_value = values[-1] if values else None
            
            if current_value is None:
                continue
            
            # Detect anomaly
            anomaly = await self.anomaly_detector.detect_anomaly(
                metric_name,
                current_value,
                values[:-1]  # Historical values excluding current
            )
            
            if anomaly:
                anomalies.append(anomaly)
        
        return anomalies
    
    async def _anomaly_detection_loop(self):
        """Continuous anomaly detection"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                anomalies = await self.detect_anomalies()
                
                for anomaly in anomalies:
                    await self._handle_anomaly(anomaly)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in anomaly detection: {e}")
                await asyncio.sleep(60)
    
    async def _handle_anomaly(self, anomaly: Dict[str, Any]):
        """Handle detected anomaly"""
        # Create alert
        alert = Alert(
            id=f"anomaly_{anomaly['metric']}_{int(time.time())}",
            severity=anomaly["severity"],
            type="anomaly",
            message=f"Anomaly detected in {anomaly['metric']}: {anomaly['current_value']:.2f} ({anomaly['direction']})",
            metric_name=anomaly["metric"],
            current_value=anomaly["current_value"],
            threshold=anomaly["mean"] + (self.anomaly_detector.sensitivity * anomaly["std"]),
            timestamp=datetime.now()
        )
        
        await self._create_alert(alert)
    
    async def send_alerts(self, alerts: List[Alert]):
        """Send alerts through configured channels"""
        for handler in self.alert_handlers:
            try:
                await handler(alerts)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        # Send to webhook if configured
        if self.alert_webhook_url and alerts:
            await self._send_webhook_alert(alerts)
    
    async def _send_webhook_alert(self, alerts: List[Alert]):
        """Send alerts to webhook"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "alerts": [alert.to_dict() for alert in alerts],
                    "timestamp": datetime.now().isoformat()
                }
                
                async with session.post(
                    self.alert_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.error(f"Webhook alert failed: {response.status}")
        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
    
    async def auto_recovery(self, alert: Alert) -> bool:
        """Attempt automatic recovery for an alert"""
        if not alert.auto_recovery_enabled:
            return False
        
        # Map alert types to recovery actions
        recovery_map = {
            "system.memory.usage": "high_memory",
            "websocket.active_connections": "high_connections",
            "api.errors.total": "high_error_rate",
        }
        
        recovery_action = recovery_map.get(alert.metric_name)
        if recovery_action and recovery_action in self.recovery_actions:
            try:
                logger.info(f"Attempting auto-recovery for {alert.metric_name}")
                success = await self.recovery_actions[recovery_action]()
                
                if success:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    logger.info(f"Auto-recovery successful for {alert.metric_name}")
                
                return success
            except Exception as e:
                logger.error(f"Auto-recovery failed: {e}")
        
        return False
    
    async def _recover_high_memory(self) -> bool:
        """Recovery action for high memory usage"""
        try:
            # Clear caches
            import gc
            gc.collect()
            
            # Clear Redis caches if needed
            if self.redis_client:
                await self.redis_client.flushdb()
            
            return True
        except Exception as e:
            logger.error(f"Memory recovery failed: {e}")
            return False
    
    async def _recover_high_connections(self) -> bool:
        """Recovery action for high connection count"""
        try:
            # This would trigger connection cleanup or scaling
            from backend.app.websocket_enhanced import enhanced_connection_manager
            
            # Trigger auto-scaling
            await enhanced_connection_manager.auto_scaling()
            
            return True
        except Exception as e:
            logger.error(f"Connection recovery failed: {e}")
            return False
    
    async def _recover_high_error_rate(self) -> bool:
        """Recovery action for high error rate"""
        try:
            # Clear error counters and reset circuit breakers
            # In a real implementation, this would reset rate limiters
            # and circuit breakers
            
            return True
        except Exception as e:
            logger.error(f"Error rate recovery failed: {e}")
            return False
    
    async def _create_alert(self, alert: Alert):
        """Create a new alert"""
        self.alerts[alert.id] = alert
        
        # Store in Redis for persistence
        if self.redis_client:
            await self.redis_client.hset(
                "alerts:active",
                alert.id,
                json.dumps(alert.to_dict())
            )
        
        # Send alert
        await self.send_alerts([alert])
        
        # Attempt auto-recovery
        if alert.auto_recovery_enabled:
            asyncio.create_task(self.auto_recovery(alert))
    
    async def _alert_processing_loop(self):
        """Process alerts based on thresholds"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Check thresholds
                await self._check_thresholds()
                
                # Clean up resolved alerts
                await self._cleanup_resolved_alerts()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert processing: {e}")
                await asyncio.sleep(30)
    
    async def _check_thresholds(self):
        """Check metrics against thresholds"""
        for metric_name, threshold in self.thresholds.items():
            # Get current metric value
            stats = await self.metrics_collector.get_metric_stats(metric_name, 60)
            if not stats:
                continue
            
            current_value = stats["mean"]
            
            # Check if exceeds threshold
            if current_value > threshold:
                # Check if alert already exists
                alert_id = f"threshold_{metric_name}"
                if alert_id not in self.alerts:
                    alert = Alert(
                        id=alert_id,
                        severity="HIGH" if current_value > threshold * 1.2 else "MEDIUM",
                        type="threshold",
                        message=f"{metric_name} exceeded threshold: {current_value:.2f} > {threshold}",
                        metric_name=metric_name,
                        current_value=current_value,
                        threshold=threshold,
                        timestamp=datetime.now()
                    )
                    await self._create_alert(alert)
            else:
                # Resolve alert if exists and value is back to normal
                alert_id = f"threshold_{metric_name}"
                if alert_id in self.alerts and not self.alerts[alert_id].resolved:
                    self.alerts[alert_id].resolved = True
                    self.alerts[alert_id].resolved_at = datetime.now()
    
    async def _cleanup_resolved_alerts(self):
        """Clean up old resolved alerts"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        to_remove = []
        for alert_id, alert in self.alerts.items():
            if alert.resolved and alert.resolved_at and alert.resolved_at < cutoff_time:
                to_remove.append(alert_id)
        
        for alert_id in to_remove:
            del self.alerts[alert_id]
            if self.redis_client:
                await self.redis_client.hdel("alerts:active", alert_id)
    
    async def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring summary"""
        # Get performance analysis
        performance = await self.analyze_performance()
        
        # Get active alerts
        active_alerts = [
            alert.to_dict() for alert in self.alerts.values()
            if not alert.resolved
        ]
        
        # Get recent anomalies
        anomalies = await self.detect_anomalies()
        
        # Get metric summaries
        metric_summaries = {}
        for metric_name in ["system.cpu.usage", "system.memory.usage", "websocket.response_time.avg"]:
            stats = await self.metrics_collector.get_metric_stats(metric_name, 300)
            if stats:
                metric_summaries[metric_name] = stats
        
        return {
            "performance": performance,
            "alerts": {
                "active": active_alerts,
                "total": len(self.alerts),
                "resolved": sum(1 for a in self.alerts.values() if a.resolved)
            },
            "anomalies": anomalies[:10],  # Top 10 anomalies
            "metrics": metric_summaries,
            "system_status": self._determine_system_status(performance, active_alerts),
            "timestamp": datetime.now().isoformat()
        }
    
    def _determine_system_status(self, performance: Dict[str, Any], active_alerts: List[Dict[str, Any]]) -> str:
        """Determine overall system status"""
        # Check for critical alerts
        critical_alerts = [a for a in active_alerts if a["severity"] == "CRITICAL"]
        if critical_alerts:
            return "critical"
        
        # Check performance score
        perf_score = performance.get("overall_score", 0)
        if perf_score < 50:
            return "degraded"
        
        # Check high severity alerts
        high_alerts = [a for a in active_alerts if a["severity"] == "HIGH"]
        if len(high_alerts) > 2:
            return "warning"
        
        if perf_score >= 90 and not active_alerts:
            return "healthy"
        elif perf_score >= 75:
            return "good"
        else:
            return "fair"


# Global instance
system_monitor = SystemMonitor()


# Convenience functions
async def record_api_metric(endpoint: str, response_time: float, status_code: int):
    """Record API request metric"""
    await system_monitor.metrics_collector.record_metric(
        "api.response_time",
        response_time * 1000,  # Convert to ms
        tags={"endpoint": endpoint, "status": str(status_code)}
    )
    
    # Record to Redis for aggregation
    if system_monitor.redis_client:
        await system_monitor.redis_client.hincrby("metrics:api", endpoint, 1)
        if status_code >= 400:
            await system_monitor.redis_client.hincrby("metrics:errors", endpoint, 1)


async def record_websocket_metric(event_type: str, value: float):
    """Record WebSocket event metric"""
    await system_monitor.metrics_collector.record_metric(
        f"websocket.{event_type}",
        value
    )