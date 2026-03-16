"""
NexusOS v2 - LLM Integration with BYOK Model

Enterprise Features:
- Multi-provider support (Ollama, OpenRouter, Anthropic)
- API key encryption for BYOK model
- Subscription tier enforcement
- Usage tracking and rate limiting
- Audit logging for compliance
"""

import os
import sys
import json
import hashlib
import secrets
import requests
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Provider(Enum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class Tier(Enum):
    FREE = "free"       # Ollama only
    BASIC = "basic"     # BYOK + credits
    PRO = "pro"         # Encrypted BYOK + priority


# Subscription tier configuration
TIER_CONFIG = {
    Tier.FREE: {
        "providers": [Provider.OLLAMA],
        "models": ["phi3", "llama3", "mistral"],
        "daily_limit": 0,  # Unlimited Ollama
        "api_keys": False,
        "encryption": False,
        "priority": "low",
        "features": ["basic_chat", "memory"]
    },
    Tier.BASIC: {
        "providers": [Provider.OLLAMA, Provider.OPENROUTER],
        "models": ["phi3", "llama3", "mistral", "gpt-4o-mini", "claude-sonnet"],
        "daily_limit": 1000,  # API credits
        "api_keys": True,
        "encryption": False,
        "priority": "normal",
        "features": ["basic_chat", "memory", "tools"]
    },
    Tier.PRO: {
        "providers": [Provider.OLLAMA, Provider.OPENROUTER, Provider.ANTHROPIC, Provider.OPENAI],
        "models": ["phi3", "llama3", "mistral", "gpt-4o", "gpt-4o-mini", "claude-sonnet", "claude-opus"],
        "daily_limit": 5000,  # More credits
        "api_keys": True,
        "encryption": True,  # Encrypted key storage
        "priority": "high",
        "features": ["basic_chat", "memory", "tools", "priority", "audit_logs"]
    }
}


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    success: bool
    content: str = None
    model: str = None
    provider: str = None
    tokens_used: int = 0
    cost: float = 0.0
    error: str = None
    execution_time_ms: float = 0.0


class EncryptionManager:
    """Manage API key encryption for enterprise security."""
    
    def __init__(self):
        # Derive encryption key from environment or generate
        self.master_key = os.environ.get("NEXUSOS_ENCRYPTION_KEY", None)
        if not self.master_key:
            self.master_key = secrets.token_hex(32)
            logger.warning("No NEXUSOS_ENCRYPTION_KEY set - using generated key (keys won't persist across restarts)")
    
    def encrypt(self, data: str) -> str:
        """Encrypt API key."""
        salt = secrets.token_hex(16)
        iv = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac('sha256', self.master_key.encode(), salt.encode(), 100000)[:32]
        
        # Simple XOR encryption (in production, use proper AES)
        encrypted = ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(data, key.hex()[:len(data)]))
        
        return f"{salt}${iv}${encrypted}"
    
    def decrypt(self, encrypted: str) -> str:
        """Decrypt API key."""
        try:
            salt, iv, encrypted_data = encrypted.split('$')
            key = hashlib.pbkdf2_hmac('sha256', self.master_key.encode(), salt.encode(), 100000)[:32]
            
            decrypted = ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(encrypted_data, key.hex()[:len(encrypted_data)]))
            return decrypted
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None


class UsageTracker:
    """Track API usage for billing and rate limiting."""
    
    def __init__(self, db=None):
        self.db = db or get_db()
    
    def check_limit(self, user_id: str, tier: Tier) -> tuple:
        """Check if user has remaining quota."""
        config = TIER_CONFIG[tier]
        if config["daily_limit"] == 0:
            return True, None  # Unlimited
        
        # Get today's usage
        today = datetime.now().strftime("%Y-%m-%d")
        usage = self._get_daily_usage(user_id, today)
        remaining = config["daily_limit"] - usage
        
        if remaining <= 0:
            return False, f"Daily limit reached ({config['daily_limit']} tokens)"
        
        return True, f"{remaining} tokens remaining"
    
    def _get_daily_usage(self, user_id: str, date: str) -> int:
        """Get daily token usage from database."""
        try:
            if self.db:
                usage = self.db.get_user_usage(user_id, days=1)
                if usage:
                    return sum(r.get('total_tokens', 0) for r in usage)
        except Exception as e:
            logger.error(f"Failed to get daily usage: {e}")
        return 0
    
    def record_usage(self, user_id: str, tokens: int, cost: float, model: str = None, provider: str = None):
        """Record usage for billing - persists to database."""
        try:
            if self.db and model and provider:
                # Track with input/output split (approximate 30/70 split)
                input_tokens = int(tokens * 0.3)
                output_tokens = tokens - input_tokens
                self.db.track_usage(user_id, model, provider, input_tokens, output_tokens, cost)
                logger.info(f"Usage recorded: user={user_id}, tokens={tokens}, cost=${cost:.4f}, model={model}")
            else:
                logger.warning(f"Usage not persisted - missing db or metadata: user={user_id}")
        except Exception as e:
            logger.error(f"Failed to record usage: {e}")


class LLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, provider: Provider, api_key: str = None):
        self.provider = provider
        self.api_key = api_key
    
    def chat(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    """Ollama provider - free local models."""
    
    def __init__(self):
        super().__init__(Provider.OLLAMA)
        self.base_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11435")
    
    def chat(self, messages: List[Dict], model: str = "llama3", **kwargs) -> LLMResponse:
        import time
        start = time.time()
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return LLMResponse(
                    success=True,
                    content=result.get("message", {}).get("content", ""),
                    model=model,
                    provider="ollama",
                    tokens_used=result.get("eval_count", 0),
                    cost=0.0,  # Free
                    execution_time_ms=(time.time() - start) * 1000
                )
            else:
                return LLMResponse(
                    success=False,
                    error=f"Ollama error: {response.status_code}"
                )
        except Exception as e:
            return LLMResponse(success=False, error=str(e))


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider - BYOK with encryption."""
    
    MODELS = {
        "gpt-4o": {"cost": 0.01, "provider": "openai"},
        "gpt-4o-mini": {"cost": 0.002, "provider": "openai"},
        "claude-sonnet": {"cost": 0.003, "provider": "anthropic"},
        "claude-opus": {"cost": 0.015, "provider": "anthropic"},
        "llama3": {"cost": 0.0001, "provider": "meta"},
    }
    
    def __init__(self, api_key: str = None, encrypted_key: str = None):
        super().__init__(Provider.OPENROUTER)
        
        if encrypted_key and not api_key:
            enc = EncryptionManager()
            api_key = enc.decrypt(encrypted_key)
        
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"
    
    def chat(self, messages: List[Dict], model: str = "gpt-4o-mini", **kwargs) -> LLMResponse:
        import time
        start = time.time()
        
        if not self.api_key:
            return LLMResponse(success=False, error="OpenRouter API key required")
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": os.environ.get("NEXUSOS_URL", "http://localhost:8080"),
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": kwargs.get("max_tokens", 4000),
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage", {})
                model_info = self.MODELS.get(model, {"cost": 0.01})
                
                return LLMResponse(
                    success=True,
                    content=result["choices"][0]["message"]["content"],
                    model=model,
                    provider="openrouter",
                    tokens_used=usage.get("total_tokens", 0),
                    cost=usage.get("total_tokens", 0) * model_info["cost"] / 1000,
                    execution_time_ms=(time.time() - start) * 1000
                )
            else:
                return LLMResponse(
                    success=False,
                    error=f"OpenRouter error: {response.status_code} - {response.text[:200]}"
                )
        except Exception as e:
            return LLMResponse(success=False, error=str(e))


class AnthropicProvider(LLMProvider):
    """Anthropic provider - Pro tier."""
    
    MODELS = {
        "claude-sonnet": {"cost": 0.003, "context": 200000},
        "claude-opus": {"cost": 0.015, "context": 200000},
    }
    
    def __init__(self, api_key: str = None, encrypted_key: str = None):
        super().__init__(Provider.ANTHROPIC)
        
        if encrypted_key and not api_key:
            enc = EncryptionManager()
            api_key = enc.decrypt(encrypted_key)
        
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = "https://api.anthropic.com/v1"
    
    def chat(self, messages: List[Dict], model: str = "claude-sonnet", **kwargs) -> LLMResponse:
        import time
        start = time.time()
        
        if not self.api_key:
            return LLMResponse(success=False, error="Anthropic API key required")
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": kwargs.get("max_tokens", 4000),
                    "messages": messages,
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                model_info = self.MODELS.get(model, {"cost": 0.003})
                
                return LLMResponse(
                    success=True,
                    content=result["content"][0]["text"],
                    model=model,
                    provider="anthropic",
                    tokens_used=result.get("usage", {}).get("input_tokens", 0),
                    cost=result.get("usage", {}).get("input_tokens", 0) * model_info["cost"] / 1000,
                    execution_time_ms=(time.time() - start) * 1000
                )
            else:
                return LLMResponse(
                    success=False,
                    error=f"Anthropic error: {response.status_code}"
                )
        except Exception as e:
            return LLMResponse(success=False, error=str(e))


class LLMManager:
    """
    Main LLM manager with BYOK support.
    
    Enterprise Features:
    - Multi-provider support
    - Subscription tier enforcement
    - API key encryption
    - Usage tracking
    - Audit logging
    """
    
    def __init__(self, db=None):
        self.db = db or get_db()
        self.usage_tracker = UsageTracker(self.db)
        self.encryption = EncryptionManager()
        
        # Provider instances
        self.providers = {
            Provider.OLLAMA: OllamaProvider(),
        }
    
    def get_provider(self, user_id: str = None, model: str = None) -> tuple:
        """Get appropriate provider based on user tier and model."""
        # Default to Ollama for free tier
        if not user_id:
            return self.providers[Provider.OLLAMA], "ollama", 0.0
        
        # Get user tier
        user = self.db.get_user(user_id)
        tier = Tier(user.get("subscription", "free")) if user else Tier.FREE
        config = TIER_CONFIG[tier]
        
        # Determine provider based on model
        if model in ["phi3", "llama3", "mistral"]:
            return self.providers[Provider.OLLAMA], "ollama", 0.0
        
        elif model in ["gpt-4o", "gpt-4o-mini"]:
            if tier == Tier.FREE:
                return None, None, 0.0  # Not available on free
            
            # Get API key (encrypted for pro)
            api_keys = user.get("api_keys", "{}") if user else "{}"
            try:
                api_keys = json.loads(api_keys) if isinstance(api_keys, str) else api_keys
            except:
                api_keys = {}
            
            encrypted_key = api_keys.get("openrouter_encrypted")
            provider = OpenRouterProvider(encrypted_key=encrypted_key)
            return provider, "openrouter", 0.01  # Estimated cost
        
        elif model in ["claude-sonnet", "claude-opus"]:
            if tier == Tier.FREE:
                return None, None, 0.0
            
            api_keys = user.get("api_keys", "{}") if user else "{}"
            try:
                api_keys = json.loads(api_keys) if isinstance(api_keys, str) else api_keys
            except:
                api_keys = {}
            
            encrypted_key = api_keys.get("anthropic_encrypted")
            provider = AnthropicProvider(encrypted_key=encrypted_key)
            return provider, "anthropic", 0.003
        
        # Default to Ollama
        return self.providers[Provider.OLLAMA], "ollama", 0.0
    
    def chat(self, user_id: str, messages: List[Dict], model: str = None, **kwargs) -> LLMResponse:
        """Send chat message to LLM."""
        # Determine model
        if not model:
            user = self.db.get_user(user_id) if user_id else None
            model = user.get("active_model", "llama3") if user else "llama3"
        
        # Get provider
        provider, provider_name, estimated_cost = self.get_provider(user_id, model)
        
        if not provider:
            return LLMResponse(
                success=False,
                error=f"Model {model} not available on your tier"
            )
        
        # Check usage limits
        if user_id:
            tier = Tier(self.db.get_user(user_id).get("subscription", "free")) if self.db.get_user(user_id) else Tier.FREE
            allowed, message = self.usage_tracker.check_limit(user_id, tier)
            if not allowed:
                return LLMResponse(success=False, error=message)
        
        # Make request
        response = provider.chat(messages, model, **kwargs)
        
        # Record usage
        if user_id and response.success:
            self.usage_tracker.record_usage(
                user_id, response.tokens_used, response.cost,
                model=response.model, provider=response.provider
            )
        
        return response
    
    def encrypt_api_key(self, user_id: str, provider: str, api_key: str) -> bool:
        """Encrypt and store API key for user."""
        encrypted = self.encryption.encrypt(api_key)
        
        user = self.db.get_user(user_id)
        if not user:
            return False
        
        api_keys = user.get("api_keys", "{}")
        try:
            if isinstance(api_keys, str):
                api_keys = json.loads(api_keys)
        except:
            api_keys = {}
        
        api_keys[f"{provider}_encrypted"] = encrypted
        
        self.db.update_user(user_id, api_keys=api_keys)
        logger.info(f"API key encrypted for user {user_id} ({provider})")
        return True
    
    def get_available_models(self, user_id: str = None) -> Dict:
        """Get available models for user tier."""
        tier = Tier.FREE
        if user_id:
            user = self.db.get_user(user_id)
            if user:
                tier = Tier(user.get("subscription", "free"))
        
        config = TIER_CONFIG[tier]
        return {
            "tier": tier.value,
            "models": config["models"],
            "providers": [p.value for p in config["providers"]],
            "features": config["features"]
        }


# Global instance
_llm_manager = None

def get_llm_manager(db=None) -> LLMManager:
    """Get LLM manager singleton."""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager(db)
    return _llm_manager
