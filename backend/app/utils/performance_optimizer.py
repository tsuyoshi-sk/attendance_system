"""
打刻システムパフォーマンス最適化サービス

システム全体のパフォーマンスを最適化し、高速レスポンスを実現します。
"""

import asyncio
import time
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict, OrderedDict
import threading
import logging
import json
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

logger = logging.getLogger(__name__)


class CacheEntry:
    """キャッシュエントリー"""
    
    def __init__(self, key: str, value: Any, ttl: int = 300):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.ttl = ttl
        self.hit_count = 0
        self.last_accessed = datetime.now()
    
    def is_expired(self) -> bool:
        """有効期限切れかチェック"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)
    
    def access(self):
        """アクセスを記録"""
        self.hit_count += 1
        self.last_accessed = datetime.now()


class LRUCache:
    """LRU（Least Recently Used）キャッシュ"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュから取得"""
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    # LRU: 最後に移動
                    self.cache.move_to_end(key)
                    entry.access()
                    self.stats["hits"] += 1
                    return entry.value
                else:
                    # 期限切れ
                    del self.cache[key]
            
            self.stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """キャッシュに設定"""
        with self._lock:
            if key in self.cache:
                # 既存エントリーを更新
                self.cache.move_to_end(key)
            elif len(self.cache) >= self.max_size:
                # 最も古いエントリーを削除
                oldest = next(iter(self.cache))
                del self.cache[oldest]
                self.stats["evictions"] += 1
            
            self.cache[key] = CacheEntry(key, value, ttl)
    
    def clear(self):
        """キャッシュをクリア"""
        with self._lock:
            self.cache.clear()
            self.stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        with self._lock:
            total = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total if total > 0 else 0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "evictions": self.stats["evictions"],
                "hit_rate": hit_rate
            }


class PunchPerformanceOptimizer:
    """打刻システム性能最適化"""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.cache = LRUCache(max_size=2000)
        self.preload_cache = LRUCache(max_size=500)
        self.query_cache = LRUCache(max_size=1000)
        self._performance_metrics: Dict[str, List[float]] = defaultdict(list)
        self._optimization_tasks: List[asyncio.Task] = []
        self._running = False
    
    async def start_optimization(self):
        """最適化を開始"""
        if not self._running:
            self._running = True
            
            # バックグラウンドタスクを開始
            self._optimization_tasks = [
                asyncio.create_task(self._periodic_cache_warmup()),
                asyncio.create_task(self._periodic_cleanup()),
                asyncio.create_task(self._monitor_performance())
            ]
            
            logger.info("Performance optimization started")
    
    async def stop_optimization(self):
        """最適化を停止"""
        if self._running:
            self._running = False
            
            # タスクをキャンセル
            for task in self._optimization_tasks:
                task.cancel()
            
            await asyncio.gather(*self._optimization_tasks, return_exceptions=True)
            self._optimization_tasks.clear()
            
            logger.info("Performance optimization stopped")
    
    async def _periodic_cache_warmup(self):
        """定期的なキャッシュウォームアップ"""
        while self._running:
            try:
                await self._warmup_cache()
                await asyncio.sleep(300)  # 5分ごと
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache warmup: {str(e)}")
                await asyncio.sleep(60)
    
    async def _periodic_cleanup(self):
        """定期的なクリーンアップ"""
        while self._running:
            try:
                await self._cleanup_expired_data()
                await asyncio.sleep(3600)  # 1時間ごと
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup: {str(e)}")
                await asyncio.sleep(300)
    
    async def _monitor_performance(self):
        """パフォーマンス監視"""
        while self._running:
            try:
                metrics = await self._collect_performance_metrics()
                await self._analyze_and_optimize(metrics)
                await asyncio.sleep(60)  # 1分ごと
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring: {str(e)}")
                await asyncio.sleep(30)
    
    def cache_employee_data(self, employee_id: int, data: Dict[str, Any]):
        """従業員データをキャッシュ"""
        cache_key = f"employee:{employee_id}"
        self.cache.set(cache_key, data, ttl=600)  # 10分
    
    def get_cached_employee_data(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """キャッシュから従業員データを取得"""
        cache_key = f"employee:{employee_id}"
        return self.cache.get(cache_key)
    
    async def optimize_database_queries(self):
        """データベースクエリ最適化"""
        if not self.db:
            return
        
        # よく使用されるクエリを特定
        common_queries = await self._identify_common_queries()
        
        # インデックスの使用状況を分析
        index_usage = await self._analyze_index_usage()
        
        # クエリプランの最適化
        for query_pattern in common_queries:
            optimized = await self._optimize_query_plan(query_pattern)
            if optimized:
                self.query_cache.set(query_pattern, optimized, ttl=3600)
    
    async def intelligent_caching(self, employee_schedule: Dict[str, Any]):
        """
        インテリジェントキャッシュ
        
        Args:
            employee_schedule: 従業員スケジュール情報
        """
        current_hour = datetime.now().hour
        
        # 出勤時間帯の従業員データを事前ロード
        if 7 <= current_hour <= 10:  # 出勤ラッシュ時間
            await self._preload_morning_shift_data()
        elif 17 <= current_hour <= 20:  # 退勤ラッシュ時間
            await self._preload_evening_shift_data()
        
        # スケジュールに基づく個別プリロード
        for employee_id, schedule in employee_schedule.items():
            expected_time = schedule.get("expected_in_time")
            if expected_time:
                # 予定時刻の30分前からデータをプリロード
                preload_time = expected_time - timedelta(minutes=30)
                if datetime.now() >= preload_time:
                    await self._preload_employee_data(employee_id)
    
    async def _preload_morning_shift_data(self):
        """朝シフトデータのプリロード"""
        if not self.db:
            return
        
        # アクティブな従業員のリストを取得
        from backend.app.models.employee import Employee
        
        active_employees = self.db.query(Employee).filter(
            Employee.is_active == True
        ).all()
        
        # バッチでプリロード
        batch_size = 50
        for i in range(0, len(active_employees), batch_size):
            batch = active_employees[i:i + batch_size]
            
            for employee in batch:
                cache_key = f"employee:{employee.id}"
                if not self.preload_cache.get(cache_key):
                    employee_data = {
                        "id": employee.id,
                        "name": employee.name,
                        "card_idm_hash": employee.card_idm_hash,
                        "department": employee.department
                    }
                    self.preload_cache.set(cache_key, employee_data, ttl=7200)
            
            await asyncio.sleep(0.1)  # バッチ間の短い待機
    
    async def _preload_evening_shift_data(self):
        """夕方シフトデータのプリロード"""
        if not self.db:
            return
        
        # 本日の出勤記録がある従業員を優先的にプリロード
        from backend.app.models.punch_record import PunchRecord, PunchType
        
        today = date.today()
        
        today_punches = self.db.query(PunchRecord).filter(
            and_(
                func.date(PunchRecord.punch_time) == today,
                PunchRecord.punch_type == PunchType.IN
            )
        ).all()
        
        for punch in today_punches:
            employee_id = punch.employee_id
            cache_key = f"employee_out:{employee_id}"
            
            if not self.preload_cache.get(cache_key):
                # 退勤処理に必要なデータをプリロード
                self.preload_cache.set(cache_key, {
                    "employee_id": employee_id,
                    "in_time": punch.punch_time.isoformat(),
                    "preloaded": True
                }, ttl=3600)
    
    async def _preload_employee_data(self, employee_id: int):
        """個別従業員データのプリロード"""
        cache_key = f"employee_individual:{employee_id}"
        
        if self.preload_cache.get(cache_key):
            return
        
        # 従業員の最近の打刻パターンを取得
        recent_punches = await self._get_recent_punch_pattern(employee_id)
        
        self.preload_cache.set(cache_key, {
            "employee_id": employee_id,
            "recent_pattern": recent_punches,
            "preloaded_at": datetime.now().isoformat()
        }, ttl=1800)
    
    async def background_optimization(self):
        """バックグラウンド最適化"""
        # 非ピーク時間かチェック
        current_hour = datetime.now().hour
        is_off_peak = current_hour < 7 or current_hour > 20
        
        if is_off_peak:
            # データベースの最適化
            await self._optimize_database()
            
            # 古いデータのアーカイブ
            await self._archive_old_data()
            
            # キャッシュの再構築
            await self._rebuild_cache()
    
    async def _warmup_cache(self):
        """キャッシュウォームアップ"""
        logger.info("Starting cache warmup")
        
        # 頻繁にアクセスされるデータを特定
        hot_keys = await self._identify_hot_data()
        
        # ホットデータをキャッシュに読み込み
        for key, data in hot_keys.items():
            if not self.cache.get(key):
                self.cache.set(key, data, ttl=1800)
        
        logger.info(f"Cache warmup completed: {len(hot_keys)} items loaded")
    
    async def _cleanup_expired_data(self):
        """期限切れデータのクリーンアップ"""
        logger.info("Starting cleanup of expired data")
        
        # キャッシュから期限切れエントリーを削除
        # (LRUCacheは自動的に処理するが、明示的にも実行)
        
        # パフォーマンスメトリクスの古いデータを削除
        cutoff_time = datetime.now() - timedelta(hours=24)
        for metric_name in list(self._performance_metrics.keys()):
            # 24時間以上前のメトリクスは削除
            # (実装の詳細は省略)
            pass
    
    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """パフォーマンスメトリクスを収集"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cache_stats": self.cache.get_stats(),
            "preload_cache_stats": self.preload_cache.get_stats(),
            "query_cache_stats": self.query_cache.get_stats()
        }
        
        # 応答時間の統計
        if "response_times" in self._performance_metrics:
            response_times = self._performance_metrics["response_times"][-100:]
            if response_times:
                metrics["response_time"] = {
                    "avg": statistics.mean(response_times),
                    "min": min(response_times),
                    "max": max(response_times),
                    "p95": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
                }
        
        return metrics
    
    async def _analyze_and_optimize(self, metrics: Dict[str, Any]):
        """メトリクスを分析して最適化"""
        # キャッシュヒット率が低い場合
        cache_stats = metrics.get("cache_stats", {})
        if cache_stats.get("hit_rate", 0) < 0.5:
            logger.warning("Low cache hit rate detected")
            # キャッシュサイズを増やすか、TTLを調整
            
        # 応答時間が遅い場合
        response_time = metrics.get("response_time", {})
        if response_time.get("avg", 0) > 1.0:  # 1秒以上
            logger.warning("High response time detected")
            # より積極的なプリロードを実行
            await self._aggressive_preload()
    
    async def _identify_common_queries(self) -> List[str]:
        """よく使用されるクエリを特定"""
        # 実装は使用するORMやデータベースに依存
        return []
    
    async def _analyze_index_usage(self) -> Dict[str, Any]:
        """インデックス使用状況を分析"""
        # 実装はデータベースに依存
        return {}
    
    async def _optimize_query_plan(self, query_pattern: str) -> Optional[Dict[str, Any]]:
        """クエリプランを最適化"""
        # 実装はデータベースに依存
        return None
    
    async def _get_recent_punch_pattern(self, employee_id: int) -> List[Dict[str, Any]]:
        """最近の打刻パターンを取得"""
        if not self.db:
            return []
        
        # キャッシュチェック
        cache_key = f"punch_pattern:{employee_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # データベースから取得
        from backend.app.models.punch_record import PunchRecord
        
        recent_punches = self.db.query(PunchRecord).filter(
            and_(
                PunchRecord.employee_id == employee_id,
                PunchRecord.punch_time >= datetime.now() - timedelta(days=7)
            )
        ).order_by(PunchRecord.punch_time.desc()).limit(20).all()
        
        pattern = [
            {
                "type": p.punch_type,
                "time": p.punch_time.isoformat(),
                "day_of_week": p.punch_time.weekday()
            }
            for p in recent_punches
        ]
        
        # キャッシュに保存
        self.cache.set(cache_key, pattern, ttl=3600)
        
        return pattern
    
    async def _identify_hot_data(self) -> Dict[str, Any]:
        """ホットデータを特定"""
        hot_data = {}
        
        # アクセス頻度の高いキーを特定
        # (実装の詳細は使用パターンに依存)
        
        return hot_data
    
    async def _optimize_database(self):
        """データベースの最適化"""
        if not self.db:
            return
        
        logger.info("Starting database optimization")
        
        # VACUUM（SQLiteの場合）
        # ANALYZE（統計情報の更新）
        # インデックスの再構築
        
        # 実装はデータベースに依存
    
    async def _archive_old_data(self):
        """古いデータのアーカイブ"""
        if not self.db:
            return
        
        # 6ヶ月以上前のデータをアーカイブ
        archive_date = datetime.now() - timedelta(days=180)
        
        # 実装の詳細は要件に依存
    
    async def _rebuild_cache(self):
        """キャッシュの再構築"""
        logger.info("Rebuilding cache")
        
        # 重要なデータを再キャッシュ
        await self._warmup_cache()
    
    async def _aggressive_preload(self):
        """積極的なプリロード"""
        # 次の1時間に打刻予定の全従業員データをプリロード
        # (実装の詳細は省略)
        pass
    
    def record_response_time(self, operation: str, duration: float):
        """応答時間を記録"""
        self._performance_metrics[f"{operation}_response_times"].append(duration)
        
        # 最新1000件のみ保持
        if len(self._performance_metrics[f"{operation}_response_times"]) > 1000:
            self._performance_metrics[f"{operation}_response_times"] = \
                self._performance_metrics[f"{operation}_response_times"][-1000:]
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """最適化状態を取得"""
        return {
            "running": self._running,
            "cache_stats": {
                "main": self.cache.get_stats(),
                "preload": self.preload_cache.get_stats(),
                "query": self.query_cache.get_stats()
            },
            "active_tasks": len(self._optimization_tasks),
            "performance_metrics": {
                metric: {
                    "count": len(values),
                    "avg": statistics.mean(values) if values else 0
                }
                for metric, values in self._performance_metrics.items()
            }
        }


# コンテキストマネージャーでパフォーマンス計測
class measure_performance:
    """パフォーマンス計測コンテキストマネージャー"""
    
    def __init__(self, optimizer: PunchPerformanceOptimizer, operation: str):
        self.optimizer = optimizer
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.optimizer.record_response_time(self.operation, duration)