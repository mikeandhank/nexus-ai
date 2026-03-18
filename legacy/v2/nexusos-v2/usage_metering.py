"""
Usage Metering - Simplified Pricing
==================================
5.5% service fee on API reloads - just like OpenRouter.

Model:
- Free: Local LLMs (phi3, llama3, mistral, codellama) - $0
- Premium: OpenAI, Anthropic - Cost + 5.5% service fee

No tiers - all features available to everyone.
Enterprise users naturally use more expensive models.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Model pricing (wholesale - these are our costs)
MODEL_PRICING = {
    # Free local models
    "phi3": {"input": 0, "output": 0, "provider": "local"},
    "llama3": {"input": 0, "output": 0, "provider": "local"},
    "mistral": {"input": 0, "output": 0, "provider": "local"},
    "codellama": {"input": 0, "output": 0, "provider": "local"},
    
    # OpenAI (wholesale prices)
    "gpt-4o-mini": {"input": 0.0003, "output": 0.0012, "provider": "openai"},  # $0.30/1M in, $1.20/1M out
    "gpt-4o": {"input": 0.005, "output": 0.015, "provider": "openai"},  # $5/1M in, $15/1M out
    "gpt-4-turbo": {"input": 0.01, "output": 0.03, "provider": "openai"},
    "gpt-4": {"input": 0.03, "output": 0.06, "provider": "openai"},
    
    # Anthropic (wholesale prices)
    "claude-sonnet": {"input": 0.003, "output": 0.015, "provider": "anthropic"},  # $3/1M in, $15/1M out
    "claude-opus": {"input": 0.015, "output": 0.075, "provider": "anthropic"},  # $15/1M in, $75/1M out
    "claude-haiku": {"input": 0.00025, "output": 0.00125, "provider": "anthropic"},  # $0.25/1M in, $1.25/1M out
    
    # Google
    "gemini-pro": {"input": 0.00125, "output": 0.005, "provider": "google"},
}

SERVICE_FEE = 0.055  # 5.5%


class SimpleMeter:
    """
    Simple usage metering - 5.5% service fee on premium models.
    """
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.environ.get('DATABASE_URL',
            'postgresql://nexusos:nexusos@localhost:5432/nexusos')
        self._init_db()
    
    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def _init_db(self):
        """Initialize tables"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Usage records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW(),
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_wholesale REAL DEFAULT 0,
                cost_plus_fee REAL DEFAULT 0,
                provider TEXT
            )
        """)
        
        # User balances (for API reloads)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_balances (
                user_id TEXT PRIMARY KEY,
                balance_usd REAL DEFAULT 0,
                total_spent REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Reload transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_reloads (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount_usd REAL NOT NULL,
                fee_55 REAL DEFAULT 0,
                credits_added REAL NOT NULL,
                payment_method TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_usage_user 
            ON api_usage(user_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def record_usage(self, user_id: str, model: str, tokens_in: int, tokens_out: int) -> Dict:
        """Record API usage and calculate cost"""
        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0, "provider": "unknown"})
        
        # Calculate wholesale cost
        cost_wholesale = (
            (tokens_in / 1_000_000) * pricing["input"] +
            (tokens_out / 1_000_000) * pricing["output"]
        )
        
        # Add 5.5% service fee for premium models
        if pricing["provider"] != "local":
            cost_plus_fee = cost_wholesale * (1 + SERVICE_FEE)
        else:
            cost_plus_fee = 0  # Free
        
        # Save to DB
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO api_usage (user_id, model, tokens_in, tokens_out, cost_wholesale, cost_plus_fee, provider)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, model, tokens_in, tokens_out, cost_wholesale, cost_plus_fee, pricing["provider"]))
        
        conn.commit()
        conn.close()
        
        return {
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_wholesale": cost_wholesale,
            "service_fee": cost_wholesale * SERVICE_FEE if pricing["provider"] != "local" else 0,
            "total_cost": cost_plus_fee
        }
    
    def get_user_usage(self, user_id: str, days: int = 30) -> Dict:
        """Get user's usage summary"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_requests,
                COALESCE(SUM(tokens_in), 0) as tokens_in,
                COALESCE(SUM(tokens_out), 0) as tokens_out,
                COALESCE(SUM(cost_wholesale), 0) as cost_wholesale,
                COALESCE(SUM(cost_plus_fee), 0) as cost_total,
                ARRAY_AGG(DISTINCT model) as models_used
            FROM api_usage
            WHERE user_id = %s AND timestamp >= %s
        """, (user_id, datetime.utcnow() - timedelta(days=days)))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_requests": row["total_requests"],
            "tokens_in": row["tokens_in"],
            "tokens_out": row["tokens_out"],
            "cost_wholesale": row["cost_wholesale"],
            "cost_plus_fee": row["cost_total"],
            "models_used": row["models_used"] or []
        }
    
    def get_balance(self, user_id: str) -> Dict:
        """Get user's API credits balance"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM user_balances WHERE user_id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "user_id": user_id,
                "balance_usd": row["balance_usd"],
                "total_spent": row["total_spent"]
            }
        
        return {"user_id": user_id, "balance_usd": 0, "total_spent": 0}
    
    def add_credits(self, user_id: str, amount_usd: float, payment_method: str = "stripe") -> Dict:
        """Add API credits (API reload)"""
        # 5.5% fee
        fee = amount_usd * SERVICE_FEE
        credits = amount_usd - fee  # User gets full amount, we take fee
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Update balance
        cursor.execute("""
            INSERT INTO user_balances (user_id, balance_usd, total_spent)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                balance_usd = user_balances.balance_usd + %s,
                total_spent = user_balances.total_spent + %s,
                updated_at = NOW()
        """, (user_id, credits, amount_usd, credits, amount_usd))
        
        # Record transaction
        cursor.execute("""
            INSERT INTO api_reloads (user_id, amount_usd, fee_55, credits_added, payment_method)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, amount_usd, fee, credits, payment_method))
        
        conn.commit()
        conn.close()
        
        return {
            "amount_added": amount_usd,
            "service_fee": fee,
            "credits_to_account": credits,
            "payment_method": payment_method
        }
    
    def use_credits(self, user_id: str, amount: float) -> Dict:
        """Use credits for API call"""
        balance = self.get_balance(user_id)
        
        if balance["balance_usd"] < amount:
            return {
                "success": False,
                "error": "Insufficient balance",
                "balance": balance["balance_usd"],
                "required": amount
            }
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_balances 
            SET balance_usd = balance_usd - %s, updated_at = NOW()
            WHERE user_id = %s
        """, (amount, user_id))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "amount_used": amount}
    
    def get_available_models(self) -> List[Dict]:
        """Get all available models with pricing"""
        models = []
        for name, pricing in MODEL_PRICING.items():
            models.append({
                "model": name,
                "provider": pricing["provider"],
                "input_per_1m": f"${pricing['input']:.4f}",
                "output_per_1m": f"${pricing['output']:.4f}",
                "price_per_1m": f"${(pricing['input'] + pricing['output']):.4f}",
                "service_fee": "5.5%" if pricing["provider"] != "local" else "0%",
                "is_free": pricing["provider"] == "local"
            })
        return models
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top users by spend"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT user_id, total_spent
            FROM user_balances
            ORDER BY total_spent DESC
            LIMIT %s
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]


# Singleton
_meter = None

def get_meter(db_url: str = None) -> SimpleMeter:
    global _meter
    if _meter is None:
        _meter = SimpleMeter(db_url)
    return _meter