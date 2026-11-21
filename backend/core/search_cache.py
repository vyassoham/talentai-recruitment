import os
import re
import time
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from core.config import settings

logger = logging.getLogger(__name__)

class SearchCacheManager:
    """
    High-performance two-tier cache for candidate search queries:
    1. Primary Tier: Distributed Upstash Redis with TTL (default: 300s / 5 mins).
    2. Fallback Tier: In-memory sliding TTL cache with LRU eviction.

    Dramatically reduces database queries, vector math, and LLM evaluations
    for repetitive searches (e.g. 'Senior Python Developer', 'React Frontend Lead').
    """
    def __init__(self, redis_url: Optional[str] = None, default_ttl: Optional[int] = None):
        self.default_ttl = default_ttl or getattr(settings, "SEARCH_CACHE_TTL_SECONDS", 300)
        self.enabled = getattr(settings, "SEARCH_CACHE_ENABLED", True)
        self._local_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._redis = None
        self.hits: int = 0
        self.misses: int = 0
        self.last_tier_used: Optional[str] = None

        url = redis_url if redis_url is not None else (settings.REDIS_URL or os.getenv("REDIS_URL"))
        if url:
            try:
                import redis
                self._redis = redis.Redis.from_url(url, decode_responses=True)
                self._redis.ping()
                logger.info("SearchCacheManager successfully connected to distributed Redis.")
            except Exception as e:
                logger.warning(f"Redis search cache unavailable ({e}); utilizing in-memory tier.")
                self._redis = None

    def build_cache_key(
        self, 
        org_id: Optional[str], 
        job_id: Optional[str], 
        query: Optional[str], 
        top_k: int, 
        fast_mode: Optional[bool], 
        rerank_top_n: Optional[int]
    ) -> str:
        """
        Builds a deterministic, tenant-isolated cache key.
        Normalizes natural language query by trimming and collapsing whitespace.
        """
        clean_q = re.sub(r'\s+', ' ', (query or "").strip().lower())
        safe_org = org_id or "global"
        safe_job = str(job_id or "default")
        raw_key = f"{safe_org}:{safe_job}:{clean_q}:{top_k}:{bool(fast_mode)}:{rerank_top_n or 0}"
        h = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()[:16]
        return f"talentai:search_cache:{safe_org}:{h}"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached search results from Redis or in-memory fallback.
        Returns None if cache is disabled, key not found, or TTL expired.
        """
        if not self.enabled:
            return None

        # 1. Check Distributed Redis
        if self._redis:
            try:
                data = self._redis.get(key)
                if data:
                    self.hits += 1
                    self.last_tier_used = "redis"
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get error for search cache ({e}); falling back to memory.")

        # 2. Check In-Memory Fallback
        now = time.time()
        entry = self._local_cache.get(key)
        if entry:
            val, expiry = entry
            if now < expiry:
                self.hits += 1
                self.last_tier_used = "memory"
                return val
            else:
                self._local_cache.pop(key, None)

        self.misses += 1
        return None

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Caches search results across Redis and in-memory tiers with TTL.
        """
        if not self.enabled:
            return

        ttl_sec = ttl or self.default_ttl

        # 1. Write to Distributed Redis
        if self._redis:
            try:
                self._redis.setex(key, ttl_sec, json.dumps(value, default=str))
            except Exception as e:
                logger.warning(f"Redis set error for search cache ({e}).")

        # 2. Write to In-Memory Cache with LRU bound
        if len(self._local_cache) >= 1000:
            # Evict oldest 200 keys
            old_keys = list(self._local_cache.keys())[:200]
            for k in old_keys:
                self._local_cache.pop(k, None)

        self._local_cache[key] = (value, time.time() + ttl_sec)

    def invalidate(self, org_id: Optional[str] = None) -> int:
        """
        Invalidates cached search entries.
        If org_id is provided, purges only keys belonging to that organization.
        """
        deleted_count = 0

        # 1. Invalidate Redis
        if self._redis:
            try:
                pattern = f"talentai:search_cache:{org_id}:*" if org_id else "talentai:search_cache:*"
                keys = self._redis.keys(pattern)
                if keys:
                    deleted_count = self._redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis cache invalidation error ({e}).")

        # 2. Invalidate In-Memory
        if org_id:
            to_del = [k for k in self._local_cache if f":{org_id}:" in k]
            for k in to_del:
                self._local_cache.pop(k, None)
                deleted_count += 1
        else:
            deleted_count += len(self._local_cache)
            self._local_cache.clear()

        return deleted_count

    def clear(self) -> int:
        """Purges all search cache entries across all organizations."""
        return self.invalidate(org_id=None)

    def get_stats(self) -> Dict[str, Any]:
        """Returns observability metrics for cache efficiency and health."""
        total = self.hits + self.misses
        hit_ratio = round((self.hits / total * 100), 2) if total > 0 else 0.0
        return {
            "enabled": self.enabled,
            "default_ttl_seconds": self.default_ttl,
            "redis_connected": self._redis is not None,
            "hits": self.hits,
            "misses": self.misses,
            "total_queries": total,
            "hit_ratio_percent": hit_ratio,
            "in_memory_item_count": len(self._local_cache)
        }

search_cache = SearchCacheManager()
