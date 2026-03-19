"""
A-10: OpenRouter Consumption Logging
Log every API call for COGS tracking
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
import json


# SQL Migration for OpenRouter Logging
OPENROUTER_LOG_SQL = """
-- A-10: OpenRouter Consumption Logging (COGS Evidence)
-- Stores every API call for cost tracking and reconciliation

CREATE TABLE IF NOT EXISTS openrouter_request_logs (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Customer & API key
    customer_id UUID NOT NULL,
    api_key_id VARCHAR(255) NOT NULL,
    
    -- Request details
    model VARCHAR(255) NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    
    -- Cost tracking (in cents)
    cost_usd DECIMAL(10, 6) NOT NULL DEFAULT 0,
    
    -- OpenRouter identifiers
    openrouter_request_id VARCHAR(255) UNIQUE,
    openrouter_model_id VARCHAR(255),
    
    -- Performance
    latency_ms INTEGER,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    error_message TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'
);

-- Indexes for common queries
CREATE INDEX idx_openrouter_customer 
    ON openrouter_request_logs(customer_id, timestamp DESC);
CREATE INDEX idx_openrouter_model 
    ON openrouter_request_logs(model, timestamp DESC);
CREATE INDEX idx_openrouter_date 
    ON openrouter_request_logs(timestamp DATE);
CREATE INDEX idx_openrouter_or_request 
    ON openrouter_request_logs(openrouter_request_id);
"""


# S3 Parquet schema for data lake
OPENROUTER_S3_PARTITIONING = """
-- Partitioned by date and customer for Athena queries
-- s3://lipaira-datalake/openrouter/YYYY/MM/DD/
-- Format: Parquet
"""


class OpenRouterLogger:
    """A-10: OpenRouter consumption logging"""
    
    def __init__(self, db_pool, s3_client=None):
        self.db = db_pool
        self.s3_client = s3_client
    
    async def log_request(
        self,
        customer_id: str,
        api_key_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
        latency_ms: int,
        status: str = "success",
        openrouter_request_id: str = None,
        openrouter_model_id: str = None,
        error_message: str = None,
        metadata: dict = None
    ) -> str:
        """Log an OpenRouter API request"""
        
        query = """
            INSERT INTO openrouter_request_logs (
                customer_id, api_key_id, model,
                prompt_tokens, completion_tokens, total_tokens,
                cost_usd, latency_ms, status,
                openrouter_request_id, openrouter_model_id,
                error_message, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                query,
                customer_id,
                api_key_id,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cost_usd,
                latency_ms,
                status,
                openrouter_request_id,
                openrouter_model_id,
                error_message,
                metadata or {}
            )
        
        return str(result['id'])
    
    async def get_customer_cogs(
        self, 
        customer_id: str, 
        start_date: datetime = None,
        end_date: datetime = None
    ) -> dict:
        """Get total COGS for a customer in a period"""
        
        query = """
            SELECT 
                COUNT(*) as request_count,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost_usd
            FROM openrouter_request_logs
            WHERE customer_id = $1
            AND status = 'success'
        """
        
        params = [customer_id]
        
        if start_date:
            query += " AND timestamp >= $2"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= $3"
            params.append(end_date)
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(query, *params)
        
        return {
            "request_count": result['request_count'],
            "total_prompt_tokens": result['total_prompt_tokens'] or 0,
            "total_completion_tokens": result['total_completion_tokens'] or 0,
            "total_tokens": result['total_tokens'] or 0,
            "total_cost_usd": float(result['total_cost_usd'] or 0)
        }
    
    async def get_daily_cogs(self, date: datetime = None) -> list:
        """Get COGS breakdown by model for a specific date"""
        
        date = date or datetime.utcnow()
        
        query = """
            SELECT 
                model,
                COUNT(*) as request_count,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost_usd
            FROM openrouter_request_logs
            WHERE timestamp::DATE = $1
            AND status = 'success'
            GROUP BY model
            ORDER BY total_cost_usd DESC
        """
        
        async with self.db.acquire() as conn:
            results = await conn.fetch(query, date.date())
        
        return [dict(r) for r in results]


# Middleware for automatic logging
OPENROUTER_MIDDLEWARE = '''
import time
import httpx
from .openrouter_logger import OpenRouterLogger

logger = OpenRouterLogger(db_pool)

class OpenRouterLoggedClient:
    """Wrapper that auto-logs all OpenRouter requests"""
    
    def __init__(self, api_key: str, customer_id: str, api_key_id: str):
        self.client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        self.customer_id = customer_id
        self.api_key_id = api_key_id
    
    async def chat_completions_create(self, model: str, messages: list, **kwargs):
        """Call OpenRouter with automatic logging"""
        
        start_time = time.time()
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json={"model": model, "messages": messages, **kwargs}
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract usage
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            # Calculate cost (in production, use OpenRouter's cost API)
            cost_usd = calculate_cost(model, prompt_tokens, completion_tokens)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # A-10: Log the request
            await logger.log_request(
                customer_id=self.customer_id,
                api_key_id=self.api_key_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status="success",
                openrouter_request_id=data.get("id")
            )
            
            return data
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log failed request
            await logger.log_request(
                customer_id=self.customer_id,
                api_key_id=self.api_key_id,
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0,
                latency_ms=latency_ms,
                status="error",
                error_message=str(e)
            )
            raise
'''
