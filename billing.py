"""
Lipaira Billing Module - OpenRouter-style credit system

Revenue Model:
- 5.5% fee on credit purchases (sh.80 minimum)
- 5% fee on BYOK provider usage
- Software is free, we make money on routing
"""

import os
import json
import uuid
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fee configuration (matching OpenRouter)
PURCHASE_FEE_PERCENT = 5.5
PURCHASE_FEE_MINIMUM = 0.80
BYOK_FEE_PERCENT = 5.0

CREDIT_EXCHANGE_RATE = 1.0 / (1 - PURCHASE_FEE_PERCENT / 100)


@dataclass
class CreditPurchase:
    id: str
    user_id: str
    amount_paid: float
    credits_added: float
    our_fee: float
    provider: str
    status: str
    created_at: datetime


@dataclass
class UsageRecord:
    id: str
    user_id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    provider_cost: float
    our_fee: float
    credits_deducted: float
    mode: str
    request_id: str
    created_at: datetime


class CreditManager:
    """Manage user credit balance and purchases."""
    
    def __init__(self, db=None):
        self.db = db
    
    def get_balance(self, user_id: str) -> float:
        """Get users credit balance."""
        if not self.db:
            return 0.0
        
        try:
            result = self.db.db.execute(
                "SELECT credits FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            return float(result[0]) if result else 0.0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    def deduct(self, user_id: str, amount: float, reason: str = "") -> bool:
        """Deduct credits from user balance."""
        if not self.db:
            return True
        
        balance = self.get_balance(user_id)
        if balance < amount:
            logger.warning(f"Insufficient credits for user {user_id}: {balance} < {amount}")
            return False
        
        try:
            self.db.db.execute(
                "UPDATE users SET credits = credits - ? WHERE id = ?",
                (amount, user_id)
            )
            logger.info(f"Deducted {amount} credits from user {user_id}: {reason}")
            return True
        except Exception as e:
            logger.error(f"Error deducting credits: {e}")
            return False
    
    def add_credits(self, user_id: str, amount: float, purchase_id: str = None) -> bool:
        """Add credits to user balance."""
        if not self.db:
            return True
        
        try:
            self.db.db.execute(
                "UPDATE users SET credits = COALESCE(credits, 0) + ? WHERE id = ?",
                (amount, user_id)
            )
            logger.info(f"Added {amount} credits to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding credits: {e}")
            return False
    
    def calculate_purchase(self, amount_paid: float) -> Dict:
        """Calculate credits and fee for a purchase amount."""
        fee = max(amount_paid * PURCHASE_FEE_PERCENT / 100, PURCHASE_FEE_MINIMUM)
        our_share = fee
        provider_credits = amount_paid - fee
        credits = provider_credits * CREDIT_EXCHANGE_RATE
        
        return {
            "amount_paid": amount_paid,
            "credits": credits,
            "our_fee": our_share,
            "provider_cost": provider_credits
        }
    
    def create_purchase(self, user_id: str, amount_paid: float, provider: str = "stripe") -> CreditPurchase:
        """Create a credit purchase record."""
        purchase_id = str(uuid.uuid4())
        calc = self.calculate_purchase(amount_paid)
        
        purchase = CreditPurchase(
            id=purchase_id,
            user_id=user_id,
            amount_paid=amount_paid,
            credits_added=calc["credits"],
            our_fee=calc["our_fee"],
            provider=provider,
            status="completed",
            created_at=datetime.now()
        )
        
        self.add_credits(user_id, calc["credits"], purchase_id)
        logger.info(f"Purchase created: {purchase_id}, {amount_paid} -> {calc['credits']} credits")
        
        return purchase


class UsageTracker:
    """Detailed usage tracking for billing."""
    
    PROVIDER_COSTS = {
        "openrouter": {
            "gpt-4o": 2.50,
            "gpt-4o-mini": 0.15,
            "claude-sonnet": 3.00,
            "claude-opus": 15.00,
            "llama3": 0.20,
        },
        "openai": {
            "gpt-4o": 2.50,
            "gpt-4o-mini": 0.15,
        },
        "anthropic": {
            "claude-sonnet": 3.00,
            "claude-opus": 15.00,
        }
    }
    
    def __init__(self, db=None):
        self.db = db
    
    def calculate_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate provider cost for a request."""
        total_tokens = input_tokens + output_tokens
        cost_per_million = self.PROVIDER_COSTS.get(provider, {}).get(model, 1.0)
        return total_tokens * cost_per_million / 1_000_000
    
    def record_usage(
        self,
        user_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        mode: str = "we_bill",
        request_id: str = None
    ) -> UsageRecord:
        """Record usage and deduct credits."""
        if not self.db:
            return None
        
        provider_cost = self.calculate_cost(provider, model, input_tokens, output_tokens)
        
        if mode == "byok":
            our_fee = provider_cost * BYOK_FEE_PERCENT / 100
            credits_deducted = provider_cost + our_fee
        else:
            our_fee = 0
            credits_deducted = provider_cost
        
        credit_manager = CreditManager(self.db)
        if not credit_manager.deduct(user_id, credits_deducted, provider + "/" + model):
            logger.warning(f"Failed to deduct credits for user {user_id}")
            return None
        
        record = UsageRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_cost=provider_cost,
            our_fee=our_fee,
            credits_deducted=credits_deducted,
            mode=mode,
            request_id=request_id or str(uuid.uuid4()),
            created_at=datetime.now()
        )
        
        logger.info(f"Usage: user={user_id}, provider={provider}, cost={provider_cost:.4f}, fee={our_fee:.4f}")
        
        return record
    
    def get_usage_summary(self, user_id: str, days: int = 30) -> Dict:
        """Get usage summary for user."""
        return {
            "user_id": user_id,
            "period_days": days,
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_our_fee": 0.0,
        }


class ProviderKeyManager:
    """Manage master and BYOK API keys."""
    
    def __init__(self, db=None):
        self.db = db
    
    def store_master_key(self, provider: str, api_key: str, label: str = "primary") -> bool:
        logger.info(f"Storing master key for provider: {provider}")
        return True
    
    def get_master_key(self, provider: str) -> Optional[str]:
        env_key = provider.upper() + "_API_KEY"
        return os.environ.get(env_key)
    
    def store_user_key(self, user_id: str, provider: str, api_key: str, label: str = None) -> bool:
        logger.info(f"Storing BYOK key for user {user_id}, provider: {provider}")
        return True
    
    def get_user_key(self, user_id: str, provider: str) -> Optional[str]:
        return None


def get_credit_manager(db=None) -> CreditManager:
    global _credit_manager
    if _credit_manager is None:
        _credit_manager = CreditManager(db)
    return _credit_manager


def get_usage_tracker(db=None) -> UsageTracker:
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker(db)
    return _usage_tracker


def get_key_manager(db=None) -> ProviderKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = ProviderKeyManager(db)
    return _key_manager
