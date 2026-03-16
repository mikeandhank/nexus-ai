"""
Network-Level Rate Limiting Module
Provides rate limiting using Redis for distributed rate limiting
"""
import time
from typing import Optional, Tuple
import redis


class RateLimiter:
    """
    Distributed rate limiter using Redis sliding window algorithm
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def is_allowed(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit
        
        Args:
            key: Identifier (user_id, IP, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            (allowed: bool, remaining: int)
        """
        now = time.time()
        window_start = now - window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiry on the key
        pipe.expire(key, window_seconds)
        
        results = pipe.execute()
        current_count = results[1]
        
        if current_count >= max_requests:
            # Over limit - remove the request we just added
            self.redis.zrem(key, str(now))
            remaining = 0
            return False, remaining
        
        remaining = max_requests - current_count - 1
        return True, remaining
    
    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests in current window"""
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old entries and count
        self.redis.zremrangebyscore(key, 0, window_start)
        current_count = self.redis.zcard(key)
        
        return max(0, max_requests - current_count)
    
    def reset(self, key: str) -> bool:
        """Reset rate limit for a key"""
        return self.redis.delete(key) > 0


# Pre-configured limiters
def get_user_rate_limiter() -> RateLimiter:
    """Rate limiter for user-level limits"""
    return RateLimiter()


# Default limits
DEFAULT_LIMITS = {
    "chat": (60, 60),      # 60 requests per minute
    "api": (100, 60),      # 100 requests per minute
    "agent_create": (10, 60),  # 10 agent creations per minute
    "webhook": (30, 60),   # 30 webhook calls per minute
}


def check_rate_limit(
    user_id: str, 
    endpoint: str = "api",
    custom_limits: dict = None
) -> Tuple[bool, int]:
    """
    Convenience function to check rate limits
    
    Usage:
        allowed, remaining = check_rate_limit("user123", "chat")
    """
    limits = custom_limits or DEFAULT_LIMITS
    max_requests, window = limits.get(endpoint, (100, 60))
    
    limiter = get_user_rate_limiter()
    key = f"ratelimit:{endpoint}:{user_id}"
    
    return limiter.is_allowed(key, max_requests, window)
