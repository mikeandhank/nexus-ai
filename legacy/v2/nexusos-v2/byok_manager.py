"""
NexusOS BYOK (Bring Your Own Key) Management
Allow users to add their own provider API keys with usage tracking
"""
import hashlib
import bcrypt
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import redis
import os
from cryptography.fernet import Fernet


class BYOKManager:
    """
    Manages user-provided API keys for external providers
    """
    
    def __init__(self, redis_url: str = None, encryption_key: str = None):
        self.redis = redis.from_url(redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        
        # Encryption for storing sensitive keys
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            self.encryption_key = os.environ.get(
                "BYOK_ENCRYPTION_KEY", 
                Fernet.generate_key()
            ).encode()
        
        self.fernet = Fernet(self.encryption_key)
        
        self.prefix = "byok:"
        self.usage_prefix = "byok:usage:"
    
    def add_provider_key(
        self,
        user_id: str,
        provider: str,
        api_key: str,
        display_name: str = None
    ) -> Dict:
        """
        Add a provider API key
        
        Args:
            user_id: The user's ID
            provider: Provider name (openai, anthropic, etc.)
            api_key: The actual API key
            display_name: Human-readable name
            
        Returns:
            Key info dict
        """
        # Validate provider
        valid_providers = ["openai", "anthropic", "google", "mistralai", "deepseek", "meta", "x-ai"]
        if provider not in valid_providers:
            return {"success": False, "error": f"Invalid provider: {provider}"}
        
        # Create key entry
        key_id = f"byok_{provider}_{hashlib.md5(api_key.encode()).hexdigest()[:8]}"
        
        # Encrypt the key for storage
        encrypted_key = self.fernet.encrypt(api_key.encode()).decode()
        
        # Hash for verification (without storing actual key)
        key_hash = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()
        
        key_data = {
            "id": key_id,
            "provider": provider,
            "display_name": display_name or f"{provider.title()} Key",
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "is_active": True,
            "monthly_limit": None,  # Can be set by user
        }
        
        # Store encrypted key
        self.redis.hset(
            f"{self.prefix}{user_id}",
            key_id,
            encrypted_key
        )
        
        # Store metadata
        self.redis.hset(
            f"{self.prefix}{user_id}:meta",
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
        
        return {
            "success": True,
            "key_id": key_id,
            "provider": provider,
            "display_name": key_data["display_name"],
            "created_at": key_data["created_at"],
        }
    
    def _hash_metadata(self, data: dict) -> str:
        """Hash metadata for storage"""
        import json
        return hashlib.sha256(json.dumps(data).encode()).hexdigest()
    
    def verify_and_get_key(self, user_id: str, provider: str) -> Optional[str]:
        """
        Get a provider key for use (returns decrypted key)
        
        Note: This should only be called when making API calls
        """
        # Find the key for this provider
        for key_id in self.redis.hkeys(f"{self.prefix}{user_id}"):
            if key_id.startswith(f"byok_{provider}_"):
                encrypted = self.redis.hget(f"{self.prefix}{user_id}", key_id)
                if encrypted:
                    try:
                        return self.fernet.decrypt(encrypted.encode()).decode()
                    except:
                        pass
        return None
    
    def list_provider_keys(self, user_id: str) -> List[Dict]:
        """List all provider keys for a user"""
        keys = []
        
        for key_id in self.redis.hkeys(f"{self.prefix}{user_id}"):
            # Get usage
            usage = self.redis.hgetall(f"{self.usage_prefix}{key_id}")
            
            # Get metadata
            meta_hash = self.redis.hget(f"{self.prefix}{user_id}:meta", key_id)
            
            # Parse provider from key_id
            parts = key_id.split("_")
            provider = parts[1] if len(parts) > 1 else "unknown"
            
            keys.append({
                "key_id": key_id,
                "provider": provider,
                "is_active": True,
                "total_requests": int(usage.get("total_requests", 0)),
                "total_cost": float(usage.get("total_cost", 0)),
                "month_start": usage.get("month_start"),
            })
        
        return keys
    
    def delete_provider_key(self, user_id: str, key_id: str) -> bool:
        """Delete a provider key"""
        # Verify ownership
        if not self.redis.hexists(f"{self.prefix}{user_id}", key_id):
            return False
        
        # Delete key and metadata
        self.redis.hdel(f"{self.prefix}{user_id}", key_id)
        self.redis.hdel(f"{self.prefix}{user_id}:meta", key_id)
        self.redis.delete(f"{self.usage_prefix}{key_id}")
        
        return True
    
    def track_usage(
        self,
        key_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> Dict:
        """Track usage for a BYOK"""
        now = datetime.now()
        month = now.strftime("%Y-%m")
        
        usage_key = f"{self.usage_prefix}{key_id}"
        current_month = self.redis.hget(usage_key, "month_start")
        
        pipe = self.redis.pipeline()
        
        pipe.hincrby(usage_key, "total_requests", 1)
        pipe.hincrby(usage_key, "total_input_tokens", input_tokens)
        pipe.hincrby(usage_key, "total_output_tokens", output_tokens)
        pipe.hincrbyfloat(usage_key, "total_cost", cost)
        
        if current_month != month:
            pipe.hset(usage_key, "month_start", month)
        
        pipe.execute()
        
        usage = self.redis.hgetall(usage_key)
        return {
            "total_requests": int(usage.get("total_requests", 0)),
            "total_cost": float(usage.get("total_cost", 0)),
        }
    
    def get_key_usage(self, key_id: str) -> Dict:
        """Get usage for a specific key"""
        usage = self.redis.hgetall(f"{self.usage_prefix}{key_id}")
        return {
            "total_requests": int(usage.get("total_requests", 0)),
            "total_input_tokens": int(usage.get("total_input_tokens", 0)),
            "total_output_tokens": int(usage.get("total_output_tokens", 0)),
            "total_cost": float(usage.get("total_cost", 0)),
            "month_start": usage.get("month_start"),
        }
    
    def set_monthly_limit(self, user_id: str, key_id: str, limit_usd: float) -> bool:
        """Set a monthly spending limit for a key"""
        meta_key = f"{self.prefix}{user_id}:meta"
        
        # Get existing metadata
        if not self.redis.hexists(meta_key, key_id):
            return False
        
        # Update limit
        # In real implementation, store and check this limit
        return True


# Global instance
_byok_manager = None

def get_byok_manager() -> BYOKManager:
    global _byok_manager
    if _byok_manager is None:
        _byok_manager = BYOKManager()
    return _byok_manager