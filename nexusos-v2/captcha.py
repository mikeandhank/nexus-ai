"""
CAPTCHA Module
==============
Simple CAPTCHA for registration protection
"""
import os
import random
import string
import hashlib
import time
from typing import Tuple, Dict


class SimpleCaptcha:
    """
    Simple math-based CAPTCHA (no external dependencies)
    
    Generates simple math problems that are easy for humans,
    hard for basic bots.
    """
    
    def __init__(self):
        self.captcha_prefix = "captcha:"
        self.expiry_seconds = 300  # 5 minutes
    
    def generate(self, difficulty: str = "easy") -> Dict:
        """
        Generate a new CAPTCHA challenge
        
        Returns: {
            "challenge_id": "...",
            "question": "What is 5 + 3?",
            "answer_hash": "..."
        }
        """
        challenge_id = hashlib.sha256(
            f"{time.time()}{random.random()}".encode()
        ).hexdigest()[:16]
        
        if difficulty == "medium":
            # Double digit addition
            a = random.randint(10, 50)
            b = random.randint(10, 50)
            answer = a + b
            question = f"What is {a} + {b}?"
        else:
            # Easy: single digit
            a = random.randint(1, 9)
            b = random.randint(1, 9)
            answer = a + b
            question = f"What is {a} + {b}?"
        
        # Hash answer (never store plain text)
        answer_hash = hashlib.sha256(
            f"{challenge_id}:{answer}".encode()
        ).hexdigest()
        
        return {
            "challenge_id": challenge_id,
            "question": question,
            "answer_hash": answer_hash,
            "expires_in": self.expiry_seconds
        }
    
    def verify(self, challenge_id: str, user_answer: int, answer_hash: str) -> Tuple[bool, str]:
        """
        Verify user's answer
        
        Returns: (is_valid, error_message)
        """
        # Calculate expected hash
        expected_hash = hashlib.sha256(
            f"{challenge_id}:{user_answer}".encode()
        ).hexdigest()
        
        if expected_hash != answer_hash:
            return False, "Incorrect answer"
        
        return True, ""
    
    def is_rate_limited(self, ip: str, redis_client=None) -> bool:
        """
        Check if IP is rate-limited
        """
        if not redis_client:
            return False  # Skip if no Redis
        
        key = f"captcha:ratelimit:{ip}"
        count = redis_client.get(key)
        
        if count and int(count) > 5:
            return True  # Rate limited
        
        # Increment counter
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 3600)  # 1 hour
        pipe.execute()
        
        return False


class RateLimiter:
    """
    Rate limiting for registration and other endpoints
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.environ.get('REDIS_URL')
    
    def check_rate_limit(self, identifier: str, action: str, 
                        limit: int, window: int) -> Tuple[bool, Dict]:
        """
        Check if identifier has exceeded rate limit
        
        Args:
            identifier: User IP or user_id
            action: Action name (register, login, etc.)
            limit: Max requests allowed
            window: Time window in seconds
        
        Returns: (is_allowed, info)
        """
        if not self.redis_url:
            return True, {"allowed": True}
        
        import redis
        r = redis.from_url(self.redis_url)
        
        key = f"ratelimit:{action}:{identifier}"
        
        current = r.get(key)
        
        if current and int(current) >= limit:
            ttl = r.ttl(key)
            return False, {
                "allowed": False,
                "retry_after": ttl if ttl > 0 else window,
                "limit": limit,
                "window": window
            }
        
        # Increment
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        pipe.execute()
        
        return True, {"allowed": True, "remaining": limit - (int(r.get(key) or 1))}


# Registration rate limiter
registration_limiter = RateLimiter()
captcha = SimpleCaptcha()


def check_registration_rate_limit(ip: str) -> Tuple[bool, Dict]:
    """Check if IP can register (max 3 per hour)"""
    return registration_limiter.check_rate_limit(
        identifier=ip,
        action="register",
        limit=3,
        window=3600
    )


def generate_registration_captcha() -> Dict:
    """Generate captcha for registration"""
    return captcha.generate(difficulty="easy")


def verify_registration_captcha(challenge_id: str, answer: int, answer_hash: str) -> Tuple[bool, str]:
    """Verify registration captcha"""
    return captcha.verify(challenge_id, answer, answer_hash)