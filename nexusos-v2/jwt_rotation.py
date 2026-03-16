"""
JWT Key Rotation Module
Provides automatic JWT secret rotation
"""
import time
import jwt
import redis
import os
from cryptography.fernet import Fernet


class JWTKeyRotation:
    """
    Handles JWT key rotation with Redis storage
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        self.key_prefix = "jwt:keys:"
        self.current_key_id = "jwt:current_key"
        self.rotation_interval = 86400 * 30  # 30 days
        
    def generate_new_key(self) -> tuple:
        """Generate a new JWT signing key"""
        key_id = f"key_{int(time.time())}"
        secret = Fernet.generate_key().decode()
        
        return key_id, secret
    
    def store_key(self, key_id: str, secret: str, is_current: bool = False):
        """Store a key in Redis"""
        key = f"{self.key_prefix}{key_id}"
        self.redis.set(key, secret, ex=self.rotation_interval * 2)
        
        if is_current:
            self.redis.set(self.current_key_id, key_id)
    
    def get_current_key(self) -> tuple:
        """Get the current key ID and secret"""
        key_id = self.redis.get(self.current_key_id)
        
        if not key_id:
            # Generate first key
            key_id, secret = self.generate_new_key()
            self.store_key(key_id, secret, is_current=True)
            return key_id, secret
        
        key = f"{self.key_prefix}{key_id}"
        secret = self.redis.get(key)
        
        if not secret:
            # Key expired, generate new
            key_id, secret = self.generate_new_key()
            self.store_key(key_id, secret, is_current=True)
            return key_id, secret
        
        return key_id, secret
    
    def rotate(self):
        """Rotate to a new key"""
        key_id, secret = self.generate_new_key()
        self.store_key(key_id, secret, is_current=True)
        return key_id
    
    def get_old_keys(self, limit: int = 2) -> list:
        """Get old keys for verification"""
        current = self.redis.get(self.current_key_id)
        keys = []
        
        for key_id in self.redis.scan_iter(f"{self.key_prefix}*"):
            if key_id != f"{self.key_prefix}{current}":
                keys.append({
                    "key_id": key_id.replace(self.key_prefix, ""),
                    "secret": self.redis.get(key_id)
                })
        
        return keys[:limit]
    
    def create_token(self, payload: dict, expires_in: int = 3600) -> str:
        """Create a JWT token with current key"""
        key_id, secret = self.get_current_key()
        
        payload["kid"] = key_id
        payload["iat"] = int(time.time())
        payload["exp"] = int(time.time()) + expires_in
        
        return jwt.encode(payload, secret, algorithm="HS256")
    
    def verify_token(self, token: str) -> dict:
        """Verify a JWT token (tries current key first, then old keys)"""
        # Try current key
        try:
            key_id, secret = self.get_current_key()
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise
        except:
            pass
        
        # Try old keys
        for key_info in self.get_old_keys():
            try:
                return jwt.decode(token, key_info["secret"], algorithms=["HS256"])
            except:
                continue
        
        raise jwt.InvalidTokenError("Token verification failed")
    
    def get_keys_status(self) -> dict:
        """Get status of all keys"""
        current = self.redis.get(self.current_key_id)
        
        return {
            "current_key": current,
            "rotation_interval_days": self.rotation_interval // 86400,
            "old_keys_count": len(self.get_old_keys())
        }


# Convenience functions
_jwt_manager = None

def get_jwt_manager() -> JWTKeyRotation:
    """Get global JWT manager"""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTKeyRotation()
    return _jwt_manager


def create_token(payload: dict, expires_in: int = 3600) -> str:
    """Create a JWT token"""
    return get_jwt_manager().create_token(payload, expires_in)


def verify_token(token: str) -> dict:
    """Verify a JWT token"""
    return get_jwt_manager().verify_token(token)
