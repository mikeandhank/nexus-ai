"""
NexusOS API Key Management
Generate, encrypt, and manage API keys with usage metering
"""
import secrets
import hashlib
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import redis
import os
import base64


class APIKeyManager:
    """
    Manages API keys with encryption and usage tracking
    """
    
    def __init__(self, redis_url: str = None, encryption_key: str = None):
        self.redis = redis.from_url(redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        
        # Generate or use provided encryption key
        if encryption_key:
            self.encryption_key = self._derive_key(encryption_key)
        else:
            # Generate a key for this instance
            self.encryption_key = Fernet.generate_key()
        
        self.fernet = Fernet(self.encryption_key)
        self.keys_prefix = "apikey:"
        self.usage_prefix = "apikey:usage:"
        self.rate_prefix = "apikey:rate:"
        
        # API key format: nxs_live_xxxxxxxxxxxxx
        self.KEY_PREFIX = "nxs_live_"
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        salt = b"nexusos-apikey-salt-2026"
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def generate_key(self, user_id: str, name: str, tier: str = "free") -> dict:
        """
        Generate a new API key
        
        Returns:
            dict with key_id, key (masked), created_at, tier
        """
        # Generate random key part (24 characters)
        random_part = secrets.token_urlsafe(24)
        key_string = f"{self.KEY_PREFIX}{random_part}"
        
        # Create key ID
        key_id = f"key_{secrets.token_hex(8)}"
        
        # Hash the key for storage
        key_hash = bcrypt.hashpw(key_string.encode(), bcrypt.gensalt()).decode()
        
        # Encrypt the full key for storage (so we can show it once)
        encrypted_key = self.fernet.encrypt(key_string.encode()).decode()
        
        # Store key metadata
        key_data = {
            "id": key_id,
            "name": name,
            "user_id": user_id,
            "key_hash": key_hash,
            "tier": tier,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "is_active": True,
            "monthly_limit": self._get_tier_limit(tier, "requests"),
            "monthly_tokens": self._get_tier_limit(tier, "tokens"),
        }
        
        # Store in Redis
        self.redis.hset(
            f"{self.keys_prefix}{user_id}",
            key_id,
            encrypted_key  # Store encrypted key
        )
        
        # Store metadata separately (not encrypted)
        self.redis.hset(
            f"{self.keys_prefix}{user_id}:meta",
            key_id,
            self._hash_metadata(key_data)
        )
        
        # Initialize usage tracking
        self.redis.hset(
            f"{self.usage_prefix}{key_id}",
            mapping={
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost": 0,
                "month_start": datetime.utcnow().strftime("%Y-%m"),
            }
        )
        
        # Initialize rate limiting
        self.redis.hset(
            f"{self.rate_prefix}{key_id}",
            mapping={
                "requests_today": 0,
                "tokens_today": 0,
                "last_reset": datetime.utcnow().strftime("%Y-%m-%d"),
            }
        )
        
        return {
            "key_id": key_id,
            "key": key_string,  # Only shown once!
            "name": name,
            "tier": tier,
            "created_at": key_data["created_at"],
            "monthly_limit": key_data["monthly_limit"],
            "monthly_tokens": key_data["monthly_tokens"],
        }
    
    def _hash_metadata(self, data: dict) -> str:
        """Hash metadata for storage"""
        import json
        return hashlib.sha256(json.dumps(data).encode()).hexdigest()
    
    def _get_tier_limit(self, tier: str, limit_type: str) -> int:
        """Get tier limits"""
        limits = {
            "free": {"requests": 50, "tokens": 10000},
            "basic": {"requests": 1000, "tokens": 1000000},
            "pro": {"requests": 10000, "tokens": 10000000},
            "enterprise": {"requests": -1, "tokens": -1},
        }
        return limits.get(tier, limits["free"]).get(limit_type, 50)
    
    def verify_key(self, key_string: str) -> Optional[dict]:
        """
        Verify an API key and return user info
        
        Returns:
            User info dict if valid, None if invalid
        """
        # Find the user who owns this key
        for user_id in self.redis.scan_iter(f"{self.keys_prefix}*"):
            if user_id.endswith(":meta"):
                continue
            
            for key_id in self.redis.hkeys(user_id):
                # Get encrypted key and compare
                encrypted = self.redis.hget(user_id, key_id)
                if not encrypted:
                    continue
                
                try:
                    stored_key = self.fernet.decrypt(encrypted.encode()).decode()
                    if stored_key == key_string:
                        # Key matches, get metadata
                        meta_key = f"{user_id}:meta"
                        meta_hash = self.redis.hget(meta_key, key_id)
                        if meta_hash:
                            return {
                                "key_id": key_id,
                                "user_id": user_id.replace(f"{self.keys_prefix}", ""),
                            }
                except:
                    continue
        
        return None
    
    def get_key_info(self, user_id: str, key_id: str) -> Optional[dict]:
        """Get information about an API key"""
        meta_key = f"{self.keys_prefix}{user_id}:meta"
        meta_hash = self.redis.hget(meta_key, key_id)
        
        if not meta_hash:
            return None
        
        # Parse metadata from hash (in real implementation, store actual data)
        return {
            "key_id": key_id,
            "is_active": True,  # Would decode from metadata
        }
    
    def list_keys(self, user_id: str) -> List[dict]:
        """List all API keys for a user"""
        keys = []
        meta_key = f"{self.keys_prefix}{user_id}:meta"
        
        for key_id in self.redis.hkeys(meta_key):
            # Get usage
            usage = self.redis.hgetall(f"{self.usage_prefix}{key_id}")
            rate = self.redis.hgetall(f"{self.rate_prefix}{key_id}")
            
            # Get metadata (in real impl, decode actual metadata)
            keys.append({
                "key_id": key_id,
                "last_used": usage.get("last_used"),
                "total_requests": int(usage.get("total_requests", 0)),
                "total_cost": float(usage.get("total_cost", 0)),
            })
        
        return keys
    
    def revoke_key(self, user_id: str, key_id: str) -> bool:
        """Revoke (delete) an API key"""
        # Delete key
        self.redis.hdel(f"{self.keys_prefix}{user_id}", key_id)
        self.redis.hdel(f"{self.keys_prefix}{user_id}:meta", key_id)
        
        # Delete usage data
        self.redis.delete(f"{self.usage_prefix}{key_id}")
        self.redis.delete(f"{self.rate_prefix}{key_id}")
        
        return True
    
    def track_usage(
        self,
        key_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> dict:
        """
        Track API usage for a key
        
        Returns:
            Updated usage stats
        """
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")
        month = now.strftime("%Y-%m")
        
        usage_key = f"{self.usage_prefix}{key_id}"
        rate_key = f"{self.rate_prefix}{key_id}"
        
        pipe = self.redis.pipeline()
        
        # Update total usage
        pipe.hincrby(usage_key, "total_requests", 1)
        pipe.hincrby(usage_key, "total_input_tokens", input_tokens)
        pipe.hincrby(usage_key, "total_output_tokens", output_tokens)
        pipe.hincrbyfloat(usage_key, "total_cost", cost)
        pipe.hset(usage_key, "last_used", now.isoformat())
        pipe.hset(usage_key, "month_start", month)
        
        # Update rate limiting (daily reset)
        current_day = self.redis.hget(rate_key, "last_reset")
        if current_day != today:
            pipe.hset(rate_key, "requests_today", 0)
            pipe.hset(rate_key, "tokens_today", 0)
            pipe.hset(rate_key, "last_reset", today)
        
        pipe.hincrby(rate_key, "requests_today", 1)
        pipe.hincrby(rate_key, "tokens_today", input_tokens + output_tokens)
        
        pipe.execute()
        
        # Return updated stats
        usage = self.redis.hgetall(usage_key)
        rate = self.redis.hgetall(rate_key)
        
        return {
            "requests_today": int(rate.get("requests_today", 0)),
            "tokens_today": int(rate.get("tokens_today", 0)),
            "total_requests": int(usage.get("total_requests", 0)),
            "total_cost": float(usage.get("total_cost", 0)),
        }
    
    def check_rate_limit(self, key_id: str) -> Tuple[bool, str]:
        """Check if key is within rate limits"""
        rate_key = f"{self.rate_prefix}{key_id}"
        usage_key = f"{self.usage_prefix}{key_id}"
        
        rate = self.redis.hgetall(rate_key)
        usage = self.redis.hgetall(usage_key)
        
        # Get key's limits
        user_id = None
        for u in self.redis.scan_iter(f"{self.keys_prefix}*"):
            if u.endswith(":meta"):
                continue
            if self.redis.hget(u, key_id):
                user_id = u.replace(f"{self.keys_prefix}", "")
                break
        
        if user_id:
            meta_key = f"{self.keys_prefix}{user_id}:meta"
            meta_hash = self.redis.hget(meta_key, key_id)
            # In real impl, decode actual limits
        
        requests_today = int(rate.get("requests_today", 0))
        tokens_today = int(rate.get("tokens_today", 0))
        
        # Get limits (default to free tier)
        monthly_limit = 50  # Free tier
        monthly_tokens = 10000  # Free tier
        
        if requests_today >= monthly_limit and monthly_limit > 0:
            return False, f"Daily request limit exceeded ({monthly_limit}/day)"
        
        if tokens_today >= monthly_tokens and monthly_tokens > 0:
            return False, f"Daily token limit exceeded ({monthly_tokens}/day)"
        
        return True, "OK"
    
    def get_encryption_key(self) -> str:
        """Get the encryption key (for storage/sharing)"""
        return self.encryption_key.decode()


# Global instance
_key_manager = None

def get_key_manager() -> APIKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager