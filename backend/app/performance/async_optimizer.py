"""
Async Performance Optimization Module

High-performance async processing with:
- Connection pooling
- Batch processing
- Caching strategies
- Query optimization
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional, Callable, TypeVar, Union
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache, wraps
import aioredis
from aiocache import Cache, cached
from aiocache.serializers import JsonSerializer
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload, joinedload
from dataclasses import dataclass
from collections import defaultdict
import hashlib
import pickle
import logging

from backend.app.models import Employee, PunchRecord, PunchType
from backend.app.logging.enhanced_logger import enhanced_logger, log_performance

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheConfig:
    """Cache configuration"""
    ttl: int = 300  # 5 minutes default
    namespace: str = "default"
    serializer = JsonSerializer
    
    def get_key(self, key: str) -> str:
        """Get namespaced cache key"""
        return f"{self.namespace}:{key}"


class AsyncOptimizer:
    """Main async optimization class"""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 postgres_url: Optional[str] = None,
                 max_workers: int = 10):
        
        # Redis connection pool
        self.redis_url = redis_url
        self.redis_pool: Optional[aioredis.ConnectionPool] = None
        
        # PostgreSQL connection pool (if using async PostgreSQL)
        self.postgres_url = postgres_url
        self.pg_pool: Optional[asyncpg.Pool] = None
        
        # SQLAlchemy async engine
        self.async_engine = None
        self.async_session_maker = None
        
        # Thread pool for CPU-bound tasks
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        
        # Batch processing queues
        self.batch_queues: Dict[str, asyncio.Queue] = {}
        self.batch_processors: Dict[str, asyncio.Task] = {}
        
        # Cache instances
        self.memory_cache = Cache(Cache.MEMORY)
        self.redis_cache = Cache(Cache.REDIS, endpoint=redis_url, namespace="async_cache")
        
        # Performance metrics
        self.metrics = defaultdict(lambda: {'count': 0, 'total_time': 0})
    
    async def initialize(self):
        """Initialize optimizer resources"""
        try:
            # Initialize Redis pool
            self.redis_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                decode_responses=True
            )
            
            # Test Redis connection
            redis = aioredis.Redis(connection_pool=self.redis_pool)
            await redis.ping()
            logger.info("Async optimizer Redis pool initialized")
            
            # Initialize PostgreSQL pool if URL provided
            if self.postgres_url:
                self.pg_pool = await asyncpg.create_pool(
                    self.postgres_url,
                    min_size=5,
                    max_size=20,
                    command_timeout=60
                )
                logger.info("Async optimizer PostgreSQL pool initialized")
            
            # Initialize SQLAlchemy async engine
            if self.postgres_url:
                self.async_engine = create_async_engine(
                    self.postgres_url.replace('postgresql://', 'postgresql+asyncpg://'),
                    pool_size=20,
                    max_overflow=10,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
                self.async_session_maker = async_sessionmaker(
                    self.async_engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
            
            logger.info("Async optimizer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize async optimizer: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup optimizer resources"""
        # Cancel batch processors
        for processor in self.batch_processors.values():
            processor.cancel()
        
        # Close pools
        if self.redis_pool:
            await self.redis_pool.disconnect()
        
        if self.pg_pool:
            await self.pg_pool.close()
        
        if self.async_engine:
            await self.async_engine.dispose()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
    
    @log_performance("nfc_batch_processing")
    async def process_nfc_scan_batch(self, scan_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process NFC scan requests in batch for better performance"""
        start_time = time.time()
        
        # Group by similar operations
        grouped_requests = self._group_scan_requests(scan_requests)
        
        # Process each group concurrently
        tasks = []
        for group_key, requests in grouped_requests.items():
            if group_key == "card_lookup":
                task = self._batch_card_lookup(requests)
            elif group_key == "punch_creation":
                task = self._batch_punch_creation(requests)
            else:
                task = self._process_individual_scans(requests)
            
            tasks.append(task)
        
        # Wait for all groups to complete
        group_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        results = []
        for group_result in group_results:
            if isinstance(group_result, Exception):
                logger.error(f"Batch processing error: {group_result}")
                continue
            results.extend(group_result)
        
        # Record metrics
        processing_time = time.time() - start_time
        self._record_metric("nfc_batch_processing", processing_time)
        
        enhanced_logger.performance.log_api_request(
            "BATCH", 
            "/nfc/batch-scan",
            200,
            processing_time * 1000
        )
        
        return results
    
    def _group_scan_requests(self, requests: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group scan requests by operation type"""
        groups = defaultdict(list)
        
        for request in requests:
            # Determine operation type
            if request.get('operation') == 'lookup':
                groups['card_lookup'].append(request)
            elif request.get('operation') == 'punch':
                groups['punch_creation'].append(request)
            else:
                groups['mixed'].append(request)
        
        return groups
    
    async def _batch_card_lookup(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch lookup employee cards"""
        card_ids = [req['card_data']['idm'] for req in requests]
        
        # Hash all card IDs
        card_hashes = [hashlib.sha256(cid.encode()).hexdigest() for cid in card_ids]
        
        # Check cache first
        cached_employees = await self._batch_cache_get(card_hashes)
        
        # Find missing from cache
        missing_indices = [i for i, emp in enumerate(cached_employees) if emp is None]
        missing_hashes = [card_hashes[i] for i in missing_indices]
        
        if missing_hashes:
            # Batch database query
            async with self.async_session_maker() as session:
                stmt = select(Employee).where(Employee.card_id.in_(missing_hashes))
                result = await session.execute(stmt)
                employees = result.scalars().all()
                
                # Create lookup dict
                emp_dict = {emp.card_id: emp for emp in employees}
                
                # Update cache
                cache_updates = []
                for i, hash_val in enumerate(missing_hashes):
                    if hash_val in emp_dict:
                        emp = emp_dict[hash_val]
                        cached_employees[missing_indices[i]] = {
                            'id': emp.id,
                            'name': emp.name,
                            'department': emp.department,
                            'card_id': emp.card_id
                        }
                        cache_updates.append((hash_val, cached_employees[missing_indices[i]]))
                
                # Batch cache update
                if cache_updates:
                    await self._batch_cache_set(cache_updates)
        
        # Build results
        results = []
        for i, request in enumerate(requests):
            employee_data = cached_employees[i]
            results.append({
                'scan_id': request['scan_id'],
                'success': employee_data is not None,
                'employee_info': employee_data,
                'message': 'Employee found' if employee_data else 'Card not registered'
            })
        
        return results
    
    async def _batch_punch_creation(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch create punch records"""
        # Prepare punch records
        punch_records = []
        
        for request in requests:
            employee_info = request.get('employee_info')
            if not employee_info:
                continue
            
            punch_record = PunchRecord(
                employee_id=employee_info['id'],
                punch_type=PunchType.IN,  # Simplified - should determine actual type
                punch_time=datetime.fromtimestamp(request['timestamp'] / 1000),
                device_type='nfc_reader',
                note=f"Batch scan: {request['scan_id']}"
            )
            punch_records.append(punch_record)
        
        # Batch insert
        if punch_records:
            async with self.async_session_maker() as session:
                session.add_all(punch_records)
                await session.commit()
        
        # Build results
        results = []
        for i, request in enumerate(requests):
            if i < len(punch_records):
                results.append({
                    'scan_id': request['scan_id'],
                    'success': True,
                    'message': 'Punch recorded successfully',
                    'punch_record': {
                        'id': punch_records[i].id,
                        'type': punch_records[i].punch_type,
                        'time': punch_records[i].punch_time.isoformat()
                    }
                })
            else:
                results.append({
                    'scan_id': request['scan_id'],
                    'success': False,
                    'message': 'Failed to create punch record'
                })
        
        return results
    
    async def _process_individual_scans(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process scans individually"""
        tasks = [self._process_single_scan(req) for req in requests]
        return await asyncio.gather(*tasks)
    
    async def _process_single_scan(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process single scan request"""
        # Simplified processing
        return {
            'scan_id': request['scan_id'],
            'success': True,
            'message': 'Processed'
        }
    
    @cached(ttl=300, cache=Cache.REDIS, serializer=JsonSerializer())
    async def cache_frequent_queries(self, query_type: str) -> Any:
        """Cache frequently used queries"""
        if query_type == "active_employees":
            return await self._get_active_employees_cached()
        elif query_type == "department_list":
            return await self._get_departments_cached()
        elif query_type == "shift_patterns":
            return await self._get_shift_patterns_cached()
        else:
            return None
    
    async def _get_active_employees_cached(self) -> List[Dict[str, Any]]:
        """Get cached active employees"""
        async with self.async_session_maker() as session:
            stmt = select(Employee).where(Employee.is_active == True)
            result = await session.execute(stmt)
            employees = result.scalars().all()
            
            return [{
                'id': emp.id,
                'name': emp.name,
                'department': emp.department,
                'card_id': emp.card_id
            } for emp in employees]
    
    async def _get_departments_cached(self) -> List[str]:
        """Get cached department list"""
        async with self.async_session_maker() as session:
            stmt = select(Employee.department).distinct()
            result = await session.execute(stmt)
            return [row[0] for row in result if row[0]]
    
    async def _get_shift_patterns_cached(self) -> Dict[str, Any]:
        """Get cached shift patterns"""
        # Placeholder - would fetch from configuration
        return {
            'morning': {'start': '09:00', 'end': '18:00'},
            'evening': {'start': '13:00', 'end': '22:00'},
            'night': {'start': '22:00', 'end': '07:00'}
        }
    
    async def _batch_cache_get(self, keys: List[str]) -> List[Optional[Dict[str, Any]]]:
        """Batch get from cache"""
        redis = aioredis.Redis(connection_pool=self.redis_pool)
        
        # Use pipeline for batch operations
        pipe = redis.pipeline()
        for key in keys:
            pipe.get(f"employee:{key}")
        
        results = await pipe.execute()
        
        # Deserialize results
        return [json.loads(r) if r else None for r in results]
    
    async def _batch_cache_set(self, items: List[tuple[str, Dict[str, Any]]], ttl: int = 3600):
        """Batch set cache items"""
        redis = aioredis.Redis(connection_pool=self.redis_pool)
        
        # Use pipeline for batch operations
        pipe = redis.pipeline()
        for key, value in items:
            pipe.setex(f"employee:{key}", ttl, json.dumps(value))
        
        await pipe.execute()
    
    def create_batch_processor(self, 
                             name: str,
                             processor_func: Callable,
                             batch_size: int = 50,
                             batch_timeout: float = 0.5):
        """Create a batch processor for specific operation"""
        if name in self.batch_processors:
            return
        
        # Create queue
        self.batch_queues[name] = asyncio.Queue(maxsize=1000)
        
        # Create processor task
        self.batch_processors[name] = asyncio.create_task(
            self._batch_processor_loop(name, processor_func, batch_size, batch_timeout)
        )
    
    async def _batch_processor_loop(self,
                                  name: str,
                                  processor_func: Callable,
                                  batch_size: int,
                                  batch_timeout: float):
        """Batch processor loop"""
        queue = self.batch_queues[name]
        batch = []
        last_process_time = time.time()
        
        while True:
            try:
                # Collect items for batch
                while len(batch) < batch_size:
                    timeout = batch_timeout - (time.time() - last_process_time)
                    if timeout <= 0:
                        break
                    
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=timeout)
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break
                
                # Process batch if we have items
                if batch:
                    try:
                        await processor_func(batch)
                        batch.clear()
                    except Exception as e:
                        logger.error(f"Batch processor {name} error: {e}")
                
                last_process_time = time.time()
                
            except asyncio.CancelledError:
                # Process remaining items before exit
                if batch:
                    try:
                        await processor_func(batch)
                    except Exception as e:
                        logger.error(f"Batch processor {name} final error: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error in batch processor {name}: {e}")
                await asyncio.sleep(1)
    
    async def add_to_batch(self, processor_name: str, item: Any):
        """Add item to batch processor"""
        if processor_name not in self.batch_queues:
            raise ValueError(f"Batch processor {processor_name} not found")
        
        await self.batch_queues[processor_name].put(item)
    
    async def run_in_thread_pool(self, func: Callable, *args, **kwargs) -> Any:
        """Run CPU-bound function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args, **kwargs)
    
    def _record_metric(self, operation: str, duration: float):
        """Record performance metric"""
        self.metrics[operation]['count'] += 1
        self.metrics[operation]['total_time'] += duration
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics"""
        stats = {}
        
        for operation, data in self.metrics.items():
            if data['count'] > 0:
                stats[operation] = {
                    'count': data['count'],
                    'total_time': data['total_time'],
                    'avg_time': data['total_time'] / data['count']
                }
        
        return stats


class OptimizedQueries:
    """Optimized database queries"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_employee_by_card_optimized(self, card_id: str) -> Optional[Employee]:
        """Optimized employee lookup with eager loading"""
        stmt = select(Employee).options(
            selectinload(Employee.punch_records)
        ).where(Employee.card_id == card_id)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_recent_punches_optimized(self, 
                                         employee_id: int,
                                         days: int = 7) -> List[PunchRecord]:
        """Get recent punches with optimized query"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        stmt = select(PunchRecord).where(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= cutoff_date
            )
        ).order_by(PunchRecord.punch_time.desc())
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def batch_insert_punch_records(self, records: List[PunchRecord]):
        """Batch insert punch records"""
        self.session.add_all(records)
        await self.session.flush()
    
    async def get_department_statistics(self, department: str) -> Dict[str, Any]:
        """Get department statistics with single query"""
        today = datetime.now().date()
        
        stmt = select(
            func.count(func.distinct(PunchRecord.employee_id)).label('active_employees'),
            func.count(PunchRecord.id).label('total_punches'),
            func.avg(
                func.extract('epoch', PunchRecord.punch_time) - 
                func.extract('epoch', func.date_trunc('day', PunchRecord.punch_time))
            ).label('avg_punch_time')
        ).select_from(PunchRecord).join(Employee).where(
            and_(
                Employee.department == department,
                func.date(PunchRecord.punch_time) == today
            )
        )
        
        result = await self.session.execute(stmt)
        row = result.one()
        
        return {
            'active_employees': row.active_employees or 0,
            'total_punches': row.total_punches or 0,
            'avg_punch_time': float(row.avg_punch_time or 0)
        }


# Cache decorators
def async_cache(ttl: int = 300, key_func: Optional[Callable] = None):
    """Async cache decorator with custom key function"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = await async_optimizer.redis_cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await async_optimizer.redis_cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def batch_process(processor_name: str):
    """Decorator to automatically batch process function calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Add to batch queue
            await async_optimizer.add_to_batch(
                processor_name,
                {'func': func, 'args': args, 'kwargs': kwargs}
            )
        
        return wrapper
    return decorator


# Global instance
async_optimizer = AsyncOptimizer()


# Connection pool manager
class ConnectionPoolManager:
    """Manage various connection pools"""
    
    def __init__(self):
        self.pools: Dict[str, Any] = {}
    
    async def create_redis_pool(self, url: str, name: str = "default") -> aioredis.ConnectionPool:
        """Create Redis connection pool"""
        pool = aioredis.ConnectionPool.from_url(
            url,
            max_connections=50,
            decode_responses=True
        )
        self.pools[f"redis_{name}"] = pool
        return pool
    
    async def create_pg_pool(self, url: str, name: str = "default") -> asyncpg.Pool:
        """Create PostgreSQL connection pool"""
        pool = await asyncpg.create_pool(
            url,
            min_size=10,
            max_size=50,
            command_timeout=60
        )
        self.pools[f"pg_{name}"] = pool
        return pool
    
    async def cleanup_all(self):
        """Cleanup all pools"""
        for name, pool in self.pools.items():
            try:
                if "redis" in name:
                    await pool.disconnect()
                elif "pg" in name:
                    await pool.close()
            except Exception as e:
                logger.error(f"Error cleaning up pool {name}: {e}")


# Global pool manager
pool_manager = ConnectionPoolManager()