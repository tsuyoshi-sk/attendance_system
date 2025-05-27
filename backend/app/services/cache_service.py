"""
キャッシュサービス

Redisを使用したキャッシュ管理とフォールバック機能を提供します。
"""

import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Callable
from functools import wraps
import asyncio
import redis.asyncio as redis
from redis.exceptions import RedisError

from config.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """キャッシュサービスクラス"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.local_cache: dict = {}  # Redisが使用できない場合のフォールバック
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }
        self._initialized = False
    
    async def initialize(self):
        """キャッシュサービスの初期化"""
        if self._initialized:
            return
        
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False  # バイナリデータを扱うため
            )
            # 接続テスト
            await self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            self._initialized = True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory cache.")
            self.redis_client = None
            self._initialized = True
    
    async def get(
        self,
        key: str,
        default: Any = None,
        deserializer: Callable = None
    ) -> Any:
        """
        キャッシュから値を取得
        
        Args:
            key: キャッシュキー
            default: デフォルト値
            deserializer: デシリアライズ関数
        
        Returns:
            キャッシュされた値またはデフォルト値
        """
        full_key = f"{settings.REDIS_PREFIX}:{key}"
        
        try:
            if self.redis_client:
                value = await self.redis_client.get(full_key)
                if value is not None:
                    self.cache_stats["hits"] += 1
                    if deserializer:
                        return deserializer(value)
                    try:
                        return pickle.loads(value)
                    except:
                        return json.loads(value)
            else:
                # ローカルキャッシュから取得
                if full_key in self.local_cache:
                    entry = self.local_cache[full_key]
                    if entry["expires_at"] > datetime.now():
                        self.cache_stats["hits"] += 1
                        return entry["value"]
                    else:
                        del self.local_cache[full_key]
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.cache_stats["errors"] += 1
        
        self.cache_stats["misses"] += 1
        return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serializer: Callable = None
    ) -> bool:
        """
        キャッシュに値を設定
        
        Args:
            key: キャッシュキー
            value: 保存する値
            ttl: 有効期限（秒）
            serializer: シリアライズ関数
        
        Returns:
            成功した場合True
        """
        full_key = f"{settings.REDIS_PREFIX}:{key}"
        
        try:
            if serializer:
                serialized_value = serializer(value)
            else:
                try:
                    serialized_value = pickle.dumps(value)
                except:
                    serialized_value = json.dumps(value).encode()
            
            if self.redis_client:
                if ttl:
                    await self.redis_client.setex(full_key, ttl, serialized_value)
                else:
                    await self.redis_client.set(full_key, serialized_value)
                return True
            else:
                # ローカルキャッシュに保存
                expires_at = datetime.now() + timedelta(seconds=ttl) if ttl else datetime.max
                self.local_cache[full_key] = {
                    "value": value,
                    "expires_at": expires_at
                }
                # メモリ制限（1000エントリまで）
                if len(self.local_cache) > 1000:
                    # 最も古いエントリを削除
                    oldest_key = min(self.local_cache.keys(), 
                                   key=lambda k: self.local_cache[k].get("expires_at", datetime.max))
                    del self.local_cache[oldest_key]
                return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self.cache_stats["errors"] += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """
        キャッシュから削除
        
        Args:
            key: キャッシュキー
        
        Returns:
            成功した場合True
        """
        full_key = f"{settings.REDIS_PREFIX}:{key}"
        
        try:
            if self.redis_client:
                await self.redis_client.delete(full_key)
            else:
                self.local_cache.pop(full_key, None)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        パターンに一致するキーを削除
        
        Args:
            pattern: キーパターン（例: "user:*"）
        
        Returns:
            削除されたキーの数
        """
        full_pattern = f"{settings.REDIS_PREFIX}:{pattern}"
        deleted_count = 0
        
        try:
            if self.redis_client:
                # SCAN を使用して安全にキーを検索
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor, match=full_pattern, count=100
                    )
                    if keys:
                        deleted_count += await self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
            else:
                # ローカルキャッシュから削除
                import fnmatch
                keys_to_delete = [
                    k for k in self.local_cache.keys()
                    if fnmatch.fnmatch(k, full_pattern)
                ]
                for key in keys_to_delete:
                    del self.local_cache[key]
                    deleted_count += 1
            
            return deleted_count
        except Exception as e:
            logger.error(f"Cache delete pattern error for pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """キーが存在するか確認"""
        full_key = f"{settings.REDIS_PREFIX}:{key}"
        
        try:
            if self.redis_client:
                return await self.redis_client.exists(full_key) > 0
            else:
                if full_key in self.local_cache:
                    entry = self.local_cache[full_key]
                    if entry["expires_at"] > datetime.now():
                        return True
                    else:
                        del self.local_cache[full_key]
                return False
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def get_stats(self) -> dict:
        """キャッシュ統計情報を取得"""
        hit_rate = (self.cache_stats["hits"] / 
                   (self.cache_stats["hits"] + self.cache_stats["misses"]) 
                   if self.cache_stats["hits"] + self.cache_stats["misses"] > 0 else 0)
        
        stats = {
            **self.cache_stats,
            "hit_rate": f"{hit_rate:.2%}",
            "backend": "redis" if self.redis_client else "memory",
            "local_cache_size": len(self.local_cache)
        }
        
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                stats["redis_memory_used"] = info.get("used_memory_human", "N/A")
                stats["redis_connected_clients"] = info.get("connected_clients", 0)
            except:
                pass
        
        return stats
    
    async def clear_all(self) -> bool:
        """すべてのキャッシュをクリア"""
        try:
            if self.redis_client:
                await self.redis_client.flushdb()
            self.local_cache.clear()
            logger.info("All cache cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False


# シングルトンインスタンス
cache_service = CacheService()


def cached(
    key_prefix: str,
    ttl: int = 300,
    key_func: Optional[Callable] = None
):
    """
    非同期関数用のキャッシュデコレータ
    
    Args:
        key_prefix: キャッシュキーのプレフィックス
        ttl: キャッシュ有効期限（秒）
        key_func: キーを生成する関数
    
    使用例:
        @cached("user", ttl=600)
        async def get_user(user_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # キャッシュキーの生成
            if key_func:
                cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
            else:
                # デフォルト: 引数をキーに含める
                key_parts = [str(arg) for arg in args]
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                cache_key = f"{key_prefix}:{':'.join(key_parts)}"
            
            # キャッシュから取得を試みる
            cached_value = await cache_service.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # キャッシュにない場合は関数を実行
            result = await func(*args, **kwargs)
            
            # 結果をキャッシュに保存
            await cache_service.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    キャッシュを無効化するデコレータ
    
    Args:
        pattern: 削除するキーパターン
    
    使用例:
        @invalidate_cache("user:*")
        async def update_user(user_id: int, data: dict):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            # 関数実行後にキャッシュを削除
            await cache_service.delete_pattern(pattern)
            return result
        return wrapper
    return decorator