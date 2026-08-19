import time
import logging
from fastapi import Request, HTTPException, status
from core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Sliding window rate limiter supporting both Redis and in-memory tracking.
    Protects expensive AI endpoints against Financial Denial of Service (FDoS).
    """
    def __init__(self):
        self._local_buckets = {}
        self._redis = None
        try:
            import redis
            self._redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._redis.ping()
        except Exception:
            self._redis = None

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        current_time = int(time.time())
        window_bucket = current_time // window_seconds
        redis_key = f"rate_limit:{key}:{window_bucket}"

        if self._redis:
            try:
                current_count = self._redis.incr(redis_key)
                if current_count == 1:
                    self._redis.expire(redis_key, window_seconds * 2)
                return current_count <= max_requests
            except Exception as e:
                logger.warning(f"Redis rate limit check error ({e}); using local fallback.")

        # In-memory sliding window fallback
        bucket = self._local_buckets.get(key, [])
        cutoff = current_time - window_seconds
        valid_timestamps = [t for t in bucket if t > cutoff]
        
        if len(valid_timestamps) >= max_requests:
            return False
            
        valid_timestamps.append(current_time)
        self._local_buckets[key] = valid_timestamps
        return True

limiter = RateLimiter()

def rate_limit(max_requests: int = 15, window_seconds: int = 60):
    """FastAPI Dependency for rate limiting per client IP and endpoint."""
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        rate_key = f"{client_ip}:{endpoint}"
        
        if not limiter.check_rate_limit(rate_key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: Maximum {max_requests} requests per {window_seconds}s allowed."
            )
    return dependency
