"""
NexusOS Usage Metering System
Tracks detailed usage per API key, per model
"""
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import redis
import os


class UsageMetering:
    """
    Tracks and reports usage metrics for API keys and models
    """
    
    def __init__(self, redis_url: str = None):
        self.redis = redis.from_url(redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        
        # Key prefixes
        self.prefix = "usage:"
        self.daily_prefix = "usage:daily:"
        self.monthly_prefix = "usage:monthly:"
        self.model_prefix = "usage:model:"
        self.key_prefix = "usage:key:"
    
    def record_request(
        self,
        api_key_id: str,
        user_id: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: float = 0
    ) -> Dict:
        """
        Record a single API request
        
        Returns:
            dict with usage stats
        """
        now = datetime.utcnow()
        date_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")
        hour_key = now.strftime("%Y-%m-%d-%H")
        
        pipe = self.redis.pipeline()
        
        # 1. Overall user usage
        user_key = f"{self.prefix}user:{user_id}"
        pipe.hincrby(user_key, "total_requests", 1)
        pipe.hincrby(user_key, "total_input_tokens", input_tokens)
        pipe.hincrby(user_key, "total_output_tokens", output_tokens)
        pipe.hincrbyfloat(user_key, "total_cost", cost)
        pipe.hset(user_key, "last_request", now.isoformat())
        
        # 2. Per-key usage
        key_key = f"{self.key_prefix}{api_key_id}"
        pipe.hincrby(key_key, "total_requests", 1)
        pipe.hincrby(key_key, "total_input_tokens", input_tokens)
        pipe.hincrby(key_key, "total_output_tokens", output_tokens)
        pipe.hincrbyfloat(key_key, "total_cost", cost)
        
        # 3. Per-model usage
        model_key = f"{self.model_prefix}{model}"
        pipe.zincrby(model_key, cost, f"{user_id}:{api_key_id}")
        
        # 4. Daily aggregation (for billing)
        daily_key = f"{self.daily_prefix}{user_id}:{date_key}"
        pipe.hincrby(daily_key, "requests", 1)
        pipe.hincrby(daily_key, "input_tokens", input_tokens)
        pipe.hincrby(daily_key, "output_tokens", output_tokens)
        pipe.hincrbyfloat(daily_key, "cost", cost)
        pipe.expire(daily_key, 90 * 86400)  # Keep 90 days
        
        # 5. Monthly aggregation
        monthly_key = f"{self.monthly_prefix}{user_id}:{month_key}"
        pipe.hincrby(monthly_key, "requests", 1)
        pipe.hincrby(monthly_key, "input_tokens", input_tokens)
        pipe.hincrby(monthly_key, "output_tokens", output_tokens)
        pipe.hincrbyfloat(monthly_key, "cost", cost)
        pipe.expire(monthly_key, 365 * 86400)  # Keep 1 year
        
        # 6. Provider aggregation
        provider_key = f"{self.prefix}provider:{provider}:{month_key}"
        pipe.hincrby(provider_key, "requests", 1)
        pipe.hincrby(provider_key, "input_tokens", input_tokens)
        pipe.hincrby(provider_key, "output_tokens", output_tokens)
        pipe.hincrbyfloat(provider_key, "cost", cost)
        
        # 7. Hourly stats (for analytics)
        hourly_key = f"{self.prefix}hourly:{hour_key}"
        pipe.hincrby(hourly_key, "requests", 1)
        pipe.hincrbyfloat(hourly_key, "cost", cost)
        pipe.expire(hourly_key, 7 * 86400)  # Keep 7 days
        
        pipe.execute()
        
        return self.get_user_summary(user_id)
    
    def get_user_summary(self, user_id: str) -> Dict:
        """Get usage summary for a user"""
        user_key = f"{self.prefix}user:{user_id}"
        data = self.redis.hgetall(user_key)
        
        return {
            "user_id": user_id,
            "total_requests": int(data.get("total_requests", 0)),
            "total_input_tokens": int(data.get("total_input_tokens", 0)),
            "total_output_tokens": int(data.get("total_output_tokens", 0)),
            "total_cost": float(data.get("total_cost", 0)),
            "last_request": data.get("last_request"),
        }
    
    def get_key_usage(self, api_key_id: str) -> Dict:
        """Get usage for a specific API key"""
        key_key = f"{self.key_prefix}{api_key_id}"
        data = self.redis.hgetall(key_key)
        
        return {
            "api_key_id": api_key_id,
            "total_requests": int(data.get("total_requests", 0)),
            "total_input_tokens": int(data.get("total_input_tokens", 0)),
            "total_output_tokens": int(data.get("total_output_tokens", 0)),
            "total_cost": float(data.get("total_cost", 0)),
        }
    
    def get_model_usage(self, model: str, limit: int = 10) -> List[Dict]:
        """Get top users for a model"""
        model_key = f"{self.model_prefix}{model}"
        
        # Get top users by spend
        top_users = self.redis.zrevrange(model_key, 0, limit - 1, withscores=True)
        
        return [
            {"user_key": user, "total_spend": round(score, 2)}
            for user, score in top_users
        ]
    
    def get_daily_usage(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get daily usage for the past N days"""
        now = datetime.now()
        usage = []
        
        for i in range(days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_key = f"{self.daily_prefix}{user_id}:{date}"
            data = self.redis.hgetall(daily_key)
            
            if data:
                usage.append({
                    "date": date,
                    "requests": int(data.get("requests", 0)),
                    "input_tokens": int(data.get("input_tokens", 0)),
                    "output_tokens": int(data.get("output_tokens", 0)),
                    "cost": float(data.get("cost", 0)),
                })
        
        return usage
    
    def get_current_month_usage(self, user_id: str) -> Dict:
        """Get current month's usage"""
        month_key = now = datetime.now().strftime("%Y-%m")
        monthly_key = f"{self.monthly_prefix}{user_id}:{month_key}"
        data = self.redis.hgetall(monthly_key)
        
        return {
            "month": month_key,
            "requests": int(data.get("requests", 0)),
            "input_tokens": int(data.get("input_tokens", 0)),
            "output_tokens": int(data.get("output_tokens", 0)),
            "cost": float(data.get("cost", 0)),
        }
    
    def get_billing_report(self, user_id: str, year: int, month: int) -> Dict:
        """Generate billing report for a specific month"""
        month_str = f"{year}-{month:02d}"
        monthly_key = f"{self.monthly_prefix}{user_id}:{month_str}"
        data = self.redis.hgetall(monthly_key)
        
        # Get daily breakdown
        days = []
        num_days = 31
        if month in [4, 6, 9, 11]:
            num_days = 30
        elif month == 2:
            num_days = 28
        
        for d in range(1, num_days + 1):
            date = f"{year}-{month:02d}-{d:02d}"
            daily_key = f"{self.daily_prefix}{user_id}:{date}"
            day_data = self.redis.hgetall(daily_key)
            
            if day_data:
                days.append({
                    "date": date,
                    "requests": int(day_data.get("requests", 0)),
                    "cost": float(day_data.get("cost", 0)),
                })
        
        return {
            "user_id": user_id,
            "billing_period": month_str,
            "total_requests": int(data.get("requests", 0)),
            "total_input_tokens": int(data.get("input_tokens", 0)),
            "total_output_tokens": int(data.get("output_tokens", 0)),
            "total_cost": float(data.get("cost", 0)),
            "daily_breakdown": days,
        }
    
    def get_system_stats(self) -> Dict:
        """Get system-wide usage statistics"""
        # Get hourly stats for last 24 hours
        now = datetime.now()
        hourly_keys = []
        for i in range(24):
            hour = (now - timedelta(hours=i)).strftime("%Y-%m-%d-%H")
            hourly_keys.append(f"{self.prefix}hourly:{hour}")
        
        total_requests = 0
        total_cost = 0
        
        for key in hourly_keys:
            data = self.redis.hgetall(key)
            total_requests += int(data.get("requests", 0))
            total_cost += float(data.get("cost", 0))
        
        # Get provider breakdown
        now = datetime.now()
        month_key = now.strftime("%Y-%m")
        
        providers = {}
        for key in self.redis.scan_iter(f"{self.prefix}provider:*:{month_key}"):
            provider = key.split(":")[-2]
            data = self.redis.hgetall(key)
            providers[provider] = {
                "requests": int(data.get("requests", 0)),
                "cost": float(data.get("cost", 0)),
            }
        
        return {
            "last_24h": {
                "requests": total_requests,
                "cost": round(total_cost, 2),
            },
            "providers": providers,
            "timestamp": now.isoformat(),
        }


# Global instance
_metering = None

def get_metering() -> UsageMetering:
    global _metering
    if _metering is None:
        _metering = UsageMetering()
    return _metering