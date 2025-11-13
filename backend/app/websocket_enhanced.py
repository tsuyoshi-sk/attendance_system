"""
Enhanced WebSocket Connection Manager with Redis Support

High-performance WebSocket management for NFC scanning with:
- Connection pooling
- Message batching
- Performance monitoring
- Auto-scaling capabilities
"""

import asyncio
import json
import time
import uvloop
from typing import Dict, Set, List, Optional, Any
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect
import logging
from collections import defaultdict, deque
import psutil

logger = logging.getLogger(__name__)

# Set uvloop as the event loop policy for better performance
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class PerformanceMetrics:
    """Performance metrics tracking"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.response_times = deque(maxlen=window_size)
        self.message_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.connection_times = deque(maxlen=window_size)
        self.last_reset = time.time()
    
    def record_response_time(self, duration: float):
        """Record response time in milliseconds"""
        self.response_times.append(duration * 1000)
    
    def record_connection_time(self, duration: float):
        """Record connection time in milliseconds"""
        self.connection_times.append(duration * 1000)
    
    def increment_message_count(self, message_type: str):
        """Increment message count by type"""
        self.message_counts[message_type] += 1
    
    def increment_error_count(self, error_type: str):
        """Increment error count by type"""
        self.error_counts[error_type] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        response_times_list = list(self.response_times)
        connection_times_list = list(self.connection_times)
        
        return {
            "response_time": {
                "avg": sum(response_times_list) / len(response_times_list) if response_times_list else 0,
                "min": min(response_times_list) if response_times_list else 0,
                "max": max(response_times_list) if response_times_list else 0,
                "p95": sorted(response_times_list)[int(len(response_times_list) * 0.95)] if len(response_times_list) > 1 else 0,
                "p99": sorted(response_times_list)[int(len(response_times_list) * 0.99)] if len(response_times_list) > 1 else 0,
            },
            "connection_time": {
                "avg": sum(connection_times_list) / len(connection_times_list) if connection_times_list else 0,
            },
            "message_counts": dict(self.message_counts),
            "error_counts": dict(self.error_counts),
            "uptime_seconds": time.time() - self.last_reset,
        }


class EnhancedNFCConnectionManager:
    """Enhanced WebSocket connection manager with Redis support"""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 max_connections: int = 200,
                 message_batch_size: int = 50,
                 batch_timeout: float = 0.1):
        # Connection management
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.max_connections = max_connections
        
        # Redis setup
        self.redis_url = redis_url
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        
        # Message batching
        self.message_queue = asyncio.Queue(maxsize=1000)
        self.message_batch_size = message_batch_size
        self.batch_timeout = batch_timeout
        self.batch_processor_task: Optional[asyncio.Task] = None
        
        # Performance monitoring
        self.performance_metrics = PerformanceMetrics()
        self.health_check_interval = 30  # seconds
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Locks for thread safety
        self._connection_lock = asyncio.Lock()
        self._metrics_lock = asyncio.Lock()
        
        # Auto-scaling
        self.scaling_threshold = 0.8  # 80% capacity
        self.scaling_enabled = True
        
    async def initialize(self):
        """Initialize the connection manager"""
        try:
            # Initialize Redis connection pool
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=100,
                decode_responses=True
            )
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
            # Start background tasks
            self.batch_processor_task = asyncio.create_task(self._batch_message_processor())
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("Enhanced WebSocket manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        # Cancel background tasks
        if self.batch_processor_task:
            self.batch_processor_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        
        # Close all connections
        for client_id in list(self.active_connections.keys()):
            await self.disconnect(client_id)
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()
    
    async def optimized_connect(self, websocket: WebSocket, client_id: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Optimized connection handling with performance tracking
        
        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
            metadata: Optional client metadata
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        start_time = time.time()
        
        try:
            # Check connection limit
            if len(self.active_connections) >= self.max_connections:
                if self.scaling_enabled:
                    await self._trigger_auto_scaling()
                else:
                    logger.warning(f"Connection limit reached: {self.max_connections}")
                    return False
            
            # Accept connection
            await websocket.accept()
            
            async with self._connection_lock:
                self.active_connections[client_id] = websocket
                self.connection_metadata[client_id] = {
                    "connected_at": datetime.now(),
                    "last_activity": datetime.now(),
                    "message_count": 0,
                    "metadata": metadata or {}
                }
            
            # Store in Redis for distributed tracking
            await self.redis_client.hset(
                "nfc:connections",
                client_id,
                json.dumps({
                    "connected_at": datetime.now().isoformat(),
                    "metadata": metadata or {}
                })
            )
            
            # Track connection time
            self.performance_metrics.record_connection_time(time.time() - start_time)
            self.performance_metrics.increment_message_count("connection")
            
            logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
            
            # Send initial configuration
            await self.send_personal_message(client_id, {
                "type": "connection_established",
                "client_id": client_id,
                "server_time": datetime.now().isoformat(),
                "config": {
                    "heartbeat_interval": 30,
                    "reconnect_delay": 5,
                    "max_retry_attempts": 3
                }
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error during connection: {e}")
            self.performance_metrics.increment_error_count("connection_error")
            return False
    
    async def disconnect(self, client_id: str):
        """Disconnect a client"""
        try:
            async with self._connection_lock:
                if client_id in self.active_connections:
                    websocket = self.active_connections.pop(client_id)
                    self.connection_metadata.pop(client_id, None)
                    
                    try:
                        await websocket.close()
                    except Exception:
                        pass
            
            # Remove from Redis
            await self.redis_client.hdel("nfc:connections", client_id)
            
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
            
        except Exception as e:
            logger.error(f"Error during disconnection: {e}")
    
    async def send_personal_message(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        start_time = time.time()
        
        try:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
                
                # Update metadata
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]["last_activity"] = datetime.now()
                    self.connection_metadata[client_id]["message_count"] += 1
                
                # Track performance
                self.performance_metrics.record_response_time(time.time() - start_time)
                self.performance_metrics.increment_message_count("personal_message")
                
        except WebSocketDisconnect:
            await self.disconnect(client_id)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.performance_metrics.increment_error_count("send_error")
    
    async def broadcast(self, message: Dict[str, Any], exclude: Set[str] = None):
        """Broadcast message to all connected clients"""
        exclude = exclude or set()
        
        # Add to message queue for batch processing
        await self.message_queue.put({
            "type": "broadcast",
            "message": message,
            "exclude": exclude,
            "timestamp": time.time()
        })
    
    async def bulk_message_processor(self):
        """Process messages in bulk for better performance"""
        await self._batch_message_processor()
    
    async def _batch_message_processor(self):
        """Internal batch message processor"""
        batch = []
        last_process_time = time.time()
        
        while True:
            try:
                # Collect messages for batch
                while len(batch) < self.message_batch_size:
                    try:
                        # Wait for message with timeout
                        timeout = self.batch_timeout - (time.time() - last_process_time)
                        if timeout <= 0:
                            break
                        
                        message = await asyncio.wait_for(
                            self.message_queue.get(),
                            timeout=timeout
                        )
                        batch.append(message)
                        
                    except asyncio.TimeoutError:
                        break
                
                # Process batch if we have messages
                if batch:
                    await self._process_message_batch(batch)
                    batch.clear()
                
                last_process_time = time.time()
                
                # Small delay to prevent tight loop
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                await asyncio.sleep(1)
    
    async def _process_message_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of messages"""
        start_time = time.time()
        
        # Group messages by type
        broadcasts = []
        
        for item in batch:
            if item["type"] == "broadcast":
                broadcasts.append(item)
        
        # Process broadcasts
        if broadcasts:
            # Combine similar broadcasts
            combined_message = {
                "type": "batch_update",
                "updates": [b["message"] for b in broadcasts],
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to all connections
            disconnected = set()
            tasks = []
            
            for client_id, websocket in self.active_connections.items():
                # Check if client should be excluded
                if any(client_id in b.get("exclude", set()) for b in broadcasts):
                    continue
                
                # Create send task
                task = asyncio.create_task(self._send_with_error_handling(
                    client_id, websocket, combined_message
                ))
                tasks.append((client_id, task))
            
            # Wait for all sends to complete
            if tasks:
                results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
                
                # Check for disconnections
                for (client_id, _), result in zip(tasks, results):
                    if isinstance(result, Exception) or result is False:
                        disconnected.add(client_id)
            
            # Clean up disconnected clients
            for client_id in disconnected:
                await self.disconnect(client_id)
            
            # Track performance
            batch_time = time.time() - start_time
            self.performance_metrics.record_response_time(batch_time / len(broadcasts))
            self.performance_metrics.increment_message_count(f"batch_broadcast_{len(broadcasts)}")
    
    async def _send_with_error_handling(self, client_id: str, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """Send message with error handling"""
        try:
            await websocket.send_json(message)
            return True
        except WebSocketDisconnect:
            return False
        except Exception as e:
            logger.error(f"Error sending to {client_id}: {e}")
            return False
    
    async def connection_health_check(self):
        """Check health of all connections"""
        now = datetime.now()
        stale_connections = []
        
        async with self._connection_lock:
            for client_id, metadata in self.connection_metadata.items():
                last_activity = metadata.get("last_activity", now)
                if now - last_activity > timedelta(minutes=5):
                    stale_connections.append(client_id)
        
        # Ping stale connections
        for client_id in stale_connections:
            try:
                await self.send_personal_message(client_id, {
                    "type": "ping",
                    "timestamp": now.isoformat()
                })
            except Exception:
                await self.disconnect(client_id)
    
    async def _health_check_loop(self):
        """Periodic health check loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.connection_health_check()
                
                # Log metrics
                metrics = await self.performance_monitor()
                logger.info(f"WebSocket metrics: {metrics}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check: {e}")
    
    async def auto_scaling(self):
        """Auto-scale based on load"""
        current_load = len(self.active_connections) / self.max_connections
        
        if current_load > self.scaling_threshold:
            await self._trigger_auto_scaling()
    
    async def _trigger_auto_scaling(self):
        """Trigger auto-scaling actions"""
        logger.warning(f"Auto-scaling triggered. Current connections: {len(self.active_connections)}/{self.max_connections}")
        
        # In a real implementation, this would:
        # 1. Notify load balancer
        # 2. Spin up additional instances
        # 3. Distribute load
        
        # For now, just increase local capacity
        self.max_connections = int(self.max_connections * 1.5)
        logger.info(f"Increased max connections to: {self.max_connections}")
    
    async def performance_monitor(self) -> Dict[str, Any]:
        """Get performance monitoring data"""
        metrics = self.performance_metrics.get_metrics()
        
        # Add system metrics
        system_metrics = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "active_connections": len(self.active_connections),
            "max_connections": self.max_connections,
            "connection_usage_percent": (len(self.active_connections) / self.max_connections * 100) if self.max_connections > 0 else 0,
            "message_queue_size": self.message_queue.qsize(),
        }
        
        # Add Redis metrics
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                redis_metrics = {
                    "redis_connected_clients": redis_info.get("connected_clients", 0),
                    "redis_used_memory_mb": redis_info.get("used_memory", 0) / 1024 / 1024,
                    "redis_total_commands": redis_info.get("total_commands_processed", 0),
                }
                metrics["redis"] = redis_metrics
            except Exception as e:
                logger.error(f"Error getting Redis metrics: {e}")
        
        metrics["system"] = system_metrics
        
        return metrics
    
    async def get_connection_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific connection"""
        if client_id in self.connection_metadata:
            metadata = self.connection_metadata[client_id].copy()
            metadata["connected_duration"] = (datetime.now() - metadata["connected_at"]).total_seconds()
            return metadata
        return None
    
    async def get_all_connections(self) -> List[Dict[str, Any]]:
        """Get information about all active connections"""
        connections = []
        for client_id, metadata in self.connection_metadata.items():
            info = metadata.copy()
            info["client_id"] = client_id
            info["connected_duration"] = (datetime.now() - metadata["connected_at"]).total_seconds()
            connections.append(info)
        return connections


# Singleton instance (lazy initialization to avoid event loop issues during import)
from typing import Optional as _Optional
_enhanced_manager: _Optional[EnhancedNFCConnectionManager] = None


def get_enhanced_connection_manager() -> EnhancedNFCConnectionManager:
    """
    Get or create the singleton EnhancedNFCConnectionManager instance.

    This uses lazy initialization to avoid creating asyncio.Queue objects
    during module import, which would fail if no event loop exists yet.

    Returns:
        EnhancedNFCConnectionManager: The singleton instance
    """
    global _enhanced_manager
    if _enhanced_manager is None:
        _enhanced_manager = EnhancedNFCConnectionManager()
    return _enhanced_manager


# Context manager for easy setup/cleanup
@asynccontextmanager
async def websocket_manager():
    """Context manager for WebSocket manager lifecycle"""
    manager = get_enhanced_connection_manager()
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.cleanup()