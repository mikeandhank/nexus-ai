"""
Usage Dashboard API
===================
Beautiful, user-first usage statistics.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UsageDashboard:
    """
    Apple-style Usage Dashboard
    
    Shows users their stats beautifully:
    - Current balance & usage
    - Token consumption by agent
    - Historical trends
    - Cost projections
    - Quota remaining
    """
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.environ.get('DATABASE_URL',
            'postgresql://nexusos:nexusos@localhost:5432/nexusos')
    
    def _get_conn(self):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    # ========== MAIN DASHBOARD ==========
    
    def get_dashboard(self, user_id: str) -> Dict:
        """
        Get full dashboard for user.
        Shows their usage, balance, and quota - beautifully.
        """
        
        balance = self.get_balance(user_id)
        usage = self.get_usage_summary(user_id)
        agents = self.get_agent_usage(user_id)
        trends = self.get_usage_trends(user_id)
        quota = self.get_quota_status(user_id)
        
        return {
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat(),
            
            # Balance & Money
            "balance": balance,
            
            # This period's usage
            "this_period": {
                "requests": usage["total_requests"],
                "tokens": usage["total_tokens"],
                "cost": usage["total_cost"],
                "period": usage["period"]
            },
            
            # Agent breakdown
            "by_agent": agents,
            
            # Historical
            "trends": trends,
            
            # Quota
            "quota": quota
        }
    
    # ========== BALANCE ==========
    
    def get_balance(self, user_id: str) -> Dict:
        """Get user's current balance"""
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT balance, total_spent, total_reloaded 
            FROM user_balances 
            WHERE user_id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {
                "current": 0.0,
                "total_spent": 0.0,
                "total_reloaded": 0.0,
                "currency": "USD"
            }
        
        return {
            "current": float(row[0] or 0),
            "total_spent": float(row[1] or 0),
            "total_reloaded": float(row[2] or 0),
            "currency": "USD"
        }
    
    def calculate_reload_amount(self, user_id: str, desired_balance: float) -> Dict:
        """
        Calculate total to charge for desired balance.
        Adds 5.5% fee transparently.
        
        User wants $100 → Pay $105.50
        """
        
        fee_rate = 0.055  # 5.5%
        
        # Calculate what they need to add
        current_balance = self.get_balance(user_id)["current"]
        needed = desired_balance - current_balance
        
        if needed <= 0:
            return {
                "desired_balance": desired_balance,
                "current_balance": current,
                "amount_to_add": 0,
                "fee": 0,
                "total_charge": 0
            }
        
        # Add fee
        fee = round(needed * fee_rate, 2)
        total = needed + fee
        
        return {
            "desired_balance": desired_balance,
            "current_balance": current_balance,
            "amount_to_add": round(needed, 2),
            "fee": fee,
            "fee_percent": "5.5%",
            "total_charge": round(total, 2),
            "currency": "USD"
        }
    
    def reload_balance(self, user_id: str, amount: float, payment_method: str = "card") -> Dict:
        """
        Reload user balance. Charge includes 5.5% fee.
        
        If user adds $100, they pay $105.50, balance increases $100
        """
        
        fee_rate = 0.055
        fee = round(amount * fee_rate, 2)
        total_charge = amount + fee
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Update balance
        cursor.execute("""
            INSERT INTO user_balances (user_id, balance, total_reloaded, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                balance = user_balances.balance + %s,
                total_reloaded = user_balances.total_reloaded + %s,
                updated_at = NOW()
        """, (user_id, amount, amount, amount, amount))
        
        # Record the reload with fee
        cursor.execute("""
            INSERT INTO api_reloads (reload_id, user_id, amount, fee, total_charged, payment_method)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (f"reload_{uuid.uuid4().hex[:12]}", user_id, amount, fee, total_charge, payment_method))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "amount_added": amount,
            "fee": fee,
            "total_charged": total_charge,
            "new_balance": self.get_balance(user_id)["current"]
        }
    
    # ========== USAGE SUMMARY ==========
    
    def get_usage_summary(self, user_id: str, days: int = 30) -> Dict:
        """Get usage summary for period"""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_requests,
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(cost_usd), 0) as total_cost
            FROM api_usage
            WHERE user_id = %s AND created_at >= %s
        """, (user_id, since))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "total_requests": row[0] or 0,
            "input_tokens": row[1] or 0,
            "output_tokens": row[2] or 0,
            "total_tokens": (row[1] or 0) + (row[2] or 0),
            "total_cost": round(float(row[3] or 0), 4),
            "period": f"last {days} days"
        }
    
    # ========== AGENT USAGE ==========
    
    def get_agent_usage(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get usage breakdown by agent"""
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                agent_id,
                COUNT(*) as runs,
                COALESCE(SUM(input_tokens), 0) + COALESCE(SUM(output_tokens), 0) as tokens,
                COALESCE(SUM(cost_usd), 0) as cost
            FROM api_usage
            WHERE user_id = %s
            GROUP BY agent_id
            ORDER BY runs DESC
            LIMIT %s
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        total_cost = sum(float(r[3] or 0) for r in rows) or 1
        
        return [
            {
                "agent_id": r[0] or "direct",
                "runs": r[1],
                "tokens": int(r[2] or 0),
                "cost": round(float(r[3] or 0), 4),
                "cost_percent": round(float(r[3] or 0) / total_cost * 100, 1)
            }
            for r in rows
        ]
    
    # ========== TRENDS ==========
    
    def get_usage_trends(self, user_id: str, days: int = 7) -> List[Dict]:
        """Get daily usage trends"""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                DATE(created_at) as day,
                COUNT(*) as requests,
                COALESCE(SUM(input_tokens), 0) + COALESCE(SUM(output_tokens), 0) as tokens,
                COALESCE(SUM(cost_usd), 0) as cost
            FROM api_usage
            WHERE user_id = %s AND created_at >= %s
            GROUP BY DATE(created_at)
            ORDER BY day DESC
        """, (user_id, since))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "date": str(r[0]),
                "requests": r[1],
                "tokens": int(r[2] or 0),
                "cost": round(float(r[3] or 0), 4)
            }
            for r in rows
        ]
    
    # ========== QUOTA ==========
    
    def get_quota_status(self, user_id: str) -> Dict:
        """Get user's quota status"""
        
        balance = self.get_balance(user_id)
        usage = self.get_usage_summary(user_id)
        
        # Assume monthly quota based on tier
        # TODO: Get from user_tiers table
        monthly_quota = 10000  # $100 worth
        
        used_percent = (usage["total_cost"] / monthly_quota * 100) if monthly_quota > 0 else 0
        remaining = max(0, monthly_quota - usage["total_cost"])
        
        return {
            "monthly_limit": monthly_quota,
            "used": round(usage["total_cost"], 2),
            "remaining": round(remaining, 2),
            "used_percent": round(min(used_percent, 100), 1),
            "reset_at": self._next_month_start()
        }
    
    def _next_month_start(self) -> str:
        """Get first day of next month"""
        now = datetime.utcnow()
        if now.month == 12:
            return datetime(now.year + 1, 1, 1).isoformat()
        return datetime(now.year, now.month + 1, 1).isoformat()
    
    # ========== PROJECTIONS ==========
    
    def get_cost_projection(self, user_id: str) -> Dict:
        """Project monthly cost based on current usage"""
        
        usage = self.get_usage_summary(user_id, days=7)
        
        # Days in current month
        now = datetime.utcnow()
        days_in_month = 31
        days_passed = now.day
        days_remaining = days_in_month - days_passed
        
        # Project
        daily_avg = usage["total_cost"] / max(days_passed, 1)
        projected = daily_avg * days_in_month
        projected_remaining = daily_avg * days_remaining
        
        return {
            "daily_average": round(daily_avg, 4),
            "projected_this_month": round(projected, 2),
            "projected_remaining": round(projected_remaining, 2),
            "as_of": now.isoformat()
        }


# Singleton
_dashboard = None

def get_usage_dashboard() -> UsageDashboard:
    global _dashboard
    if _dashboard is None:
        _dashboard = UsageDashboard()
    return _dashboard
