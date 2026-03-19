"""
B-01: Revenue Event Stream
B-02: COGS Event Stream
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
import json


# SQL Tables for Revenue and COGS
REVENUE_COGS_SQL = """
-- B-01: Revenue Event Stream
CREATE TABLE IF NOT EXISTS revenue_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(100) UNIQUE NOT NULL,
    customer_id UUID NOT NULL,
    stripe_payment_intent_id VARCHAR(255),
    base_amount_cents INTEGER NOT NULL,
    service_fee_cents INTEGER NOT NULL,
    total_charged_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    tax_collected_cents INTEGER DEFAULT 0,
    tax_rate DECIMAL(5, 4) DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT positive_amount CHECK (base_amount_cents >= 0)
);

CREATE INDEX idx_revenue_customer ON revenue_events(customer_id, timestamp DESC);
CREATE INDEX idx_revenue_stripe ON revenue_events(stripe_payment_intent_id);

-- B-02: COGS Event Stream
CREATE TABLE IF NOT EXISTS cogs_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(100) UNIQUE NOT NULL,
    customer_id UUID NOT NULL,
    openrouter_request_id VARCHAR(255),
    model VARCHAR(255) NOT NULL,
    tokens_total INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_cogs_customer ON cogs_events(customer_id, timestamp DESC);
CREATE INDEX idx_cogs_model ON cogs_events(model, timestamp DESC);

-- B-03: Deferred Revenue Tracking (Materialized View)
CREATE MATERIALIZED VIEW deferred_revenue_summary AS
SELECT 
    customer_id,
    SUM(credits_purchased - credits_consumed) * credits_per_dollar as deferred_cents,
    SUM(credits_purchased) as total_credits_purchased,
    SUM(credits_consumed) as total_credits_consumed,
    COUNT(*) as transaction_count
FROM (
    SELECT 
        customer_id,
        SUM(CASE WHEN event_type = 'purchase' THEN credits_delta ELSE 0 END) as credits_purchased,
        SUM(CASE WHEN event_type = 'consumption' THEN ABS(credits_delta) ELSE 0 END) as credits_consumed,
        100.0 as credits_per_dollar
    FROM credit_ledger_events
    GROUP BY customer_id
) sub
GROUP BY customer_id;

-- B-04: Sales Tax Collection Ledger
CREATE TABLE IF NOT EXISTS tax_collection (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    jurisdiction VARCHAR(100) NOT NULL,  -- state/country
    taxable_amount_cents INTEGER NOT NULL,
    tax_rate DECIMAL(5, 4) NOT NULL,
    tax_collected_cents INTEGER NOT NULL,
    tax_period VARCHAR(7) NOT NULL,  -- YYYY-MM
    remittance_status VARCHAR(50) DEFAULT 'collected',  -- collected, remitted
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    remitted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_tax_jurisdiction ON tax_collection(jurisdiction, tax_period);
CREATE INDEX idx_tax_customer ON tax_collection(customer_id);

-- B-05: Refund & Dispute Tracking
CREATE TABLE IF NOT EXISTS refunds_and_disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_transaction_id UUID NOT NULL,
    dispute_type VARCHAR(50) NOT NULL,  -- refund, chargeback, reversal
    amount_cents INTEGER NOT NULL,
    reason_code VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    stripe_dispute_id VARCHAR(255),
    resolution TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refund_original ON refunds_and_disputes(original_transaction_id);
CREATE INDEX idx_refund_status ON refunds_and_disputes(status);
"""


class RevenueEventStream:
    """B-01: Revenue Event Pipeline"""
    
    def __init__(self, sqs_client=None, db_pool=None):
        self.sqs_client = sqs_client
        self.db = db_pool
        self.queue_url = "https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/lipaira-revenue-events"
    
    async def publish_revenue_event(
        self,
        customer_id: str,
        stripe_payment_intent_id: str,
        base_amount_cents: int,
        service_fee_cents: int,
        total_charged_cents: int,
        currency: str = "USD",
        tax_collected_cents: int = 0,
        tax_rate: float = 0
    ) -> str:
        """Publish revenue recognized event"""
        
        event = {
            "event_id": f"rev-{uuid4().hex[:16]}",
            "event_type": "revenue_recognized",
            "timestamp": datetime.utcnow().isoformat(),
            "customer_id": customer_id,
            "stripe_payment_intent_id": stripe_payment_intent_id,
            "base_amount_cents": base_amount_cents,
            "service_fee_cents": service_fee_cents,
            "total_charged_cents": total_charged_cents,
            "currency": currency,
            "tax_collected_cents": tax_collected_cents,
            "tax_rate": tax_rate
        }
        
        # Publish to SQS
        if self.sqs_client:
            self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(event)
            )
        
        # Also store in DB
        if self.db:
            await self._store_event(event)
        
        return event["event_id"]
    
    async def _store_event(self, event: dict):
        """Store revenue event in database"""
        
        query = """
            INSERT INTO revenue_events (
                event_id, customer_id, stripe_payment_intent_id,
                base_amount_cents, service_fee_cents, total_charged_cents,
                currency, tax_collected_cents, tax_rate
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                event["event_id"],
                event["customer_id"],
                event["stripe_payment_intent_id"],
                event["base_amount_cents"],
                event["service_fee_cents"],
                event["total_charged_cents"],
                event["currency"],
                event["tax_collected_cents"],
                event["tax_rate"]
            )


class COGSEventStream:
    """B-02: COGS Event Pipeline"""
    
    def __init__(self, sqs_client=None, db_pool=None):
        self.sqs_client = sqs_client
        self.db = db_pool
        self.queue_url = "https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/lipaira-cogs-events"
    
    async def publish_cogs_event(
        self,
        customer_id: str,
        openrouter_request_id: str,
        model: str,
        tokens_total: int,
        cost_usd: float
    ) -> str:
        """Publish COGS incurred event"""
        
        event = {
            "event_id": f"cogs-{uuid4().hex[:16]}",
            "event_type": "cogs_incurred",
            "timestamp": datetime.utcnow().isoformat(),
            "customer_id": customer_id,
            "openrouter_request_id": openrouter_request_id,
            "model": model,
            "tokens_total": tokens_total,
            "cost_usd": cost_usd
        }
        
        if self.sqs_client:
            self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(event)
            )
        
        if self.db:
            await self._store_event(event)
        
        return event["event_id"]
    
    async def _store_event(self, event: dict):
        """Store COGS event in database"""
        
        query = """
            INSERT INTO cogs_events (
                event_id, customer_id, openrouter_request_id,
                model, tokens_total, cost_usd
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                event["event_id"],
                event["customer_id"],
                event["openrouter_request_id"],
                event["model"],
                event["tokens_total"],
                event["cost_usd"]
            )


# Revenue recognition calculation
def calculate_revenue_recognized(
    credits_purchased: int,
    credits_consumed: int,
    purchase_price_cents: int
) -> dict:
    """Calculate recognized vs deferred revenue"""
    
    if credits_purchased == 0:
        return {"recognized": 0, "deferred": 0}
    
    consumption_ratio = credits_consumed / credits_purchased
    recognized = int(purchase_price_cents * consumption_ratio)
    deferred = purchase_price_cents - recognized
    
    return {
        "recognized": recognized,
        "deferred": deferred,
        "consumption_ratio": consumption_ratio
    }
