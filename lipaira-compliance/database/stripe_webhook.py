"""
A-08: Stripe Webhook Audit
Store raw Stripe webhook payloads for dispute/reconciliation
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from enum import Enum
import json


# SQL Migration
STRIPE_WEBHOOK_SQL = """
-- A-08: Stripe Webhook Audit Table
-- Stores raw webhook payloads before any processing

CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Stripe identifiers
    stripe_event_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_event_type VARCHAR(255) NOT NULL,
    stripe_webhook_id VARCHAR(255),
    
    -- Timing
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Processing status
    processing_status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (
        processing_status IN ('pending', 'processing', 'completed', 'failed', 'duplicate')
    ),
    processing_error TEXT,
    
    -- Raw payload storage
    raw_payload JSONB NOT NULL,
    
    -- Links to other tables
    customer_id UUID,
    transaction_id UUID,
    
    -- Indexes
    CONSTRAINT unique_stripe_event UNIQUE (stripe_event_id)
);

CREATE INDEX idx_stripe_webhook_received 
    ON stripe_webhook_events(received_at DESC);
CREATE INDEX idx_stripe_webhook_status 
    ON stripe_webhook_events(processing_status, received_at);
CREATE INDEX idx_stripe_webhook_customer 
    ON stripe_webhook_events(customer_id) 
    WHERE customer_id IS NOT NULL;
"""


class WebhookStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class StripeWebhookStore:
    """A-08: Stripe webhook audit storage"""
    
    def __init__(self, db_pool):
        self.db = db_pool
    
    async def store_raw(self, stripe_event_id: str, event_type: str, 
                        payload: dict, stripe_webhook_id: str = None) -> dict:
        """Store raw webhook payload before processing"""
        
        # Check for duplicates
        existing = await self.get_by_stripe_id(stripe_event_id)
        if existing:
            return {
                "stored": False,
                "duplicate": True,
                "id": existing['id']
            }
        
        query = """
            INSERT INTO stripe_webhook_events (
                stripe_event_id, stripe_event_type, stripe_webhook_id,
                raw_payload, processing_status
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                query,
                stripe_event_id,
                event_type,
                stripe_webhook_id,
                json.dumps(payload),
                WebhookStatus.PENDING.value
            )
        
        return {
            "stored": True,
            "duplicate": False,
            "id": str(result['id'])
        }
    
    async def update_status(
        self, 
        stripe_event_id: str, 
        status: WebhookStatus,
        error: str = None,
        customer_id: str = None,
        transaction_id: str = None
    ):
        """Update processing status after handling"""
        
        query = """
            UPDATE stripe_webhook_events
            SET processing_status = $1,
                processing_error = $2,
                customer_id = $3,
                transaction_id = $4,
                processed_at = NOW()
            WHERE stripe_event_id = $5
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                status.value,
                error,
                customer_id,
                transaction_id,
                stripe_event_id
            )
    
    async def get_by_stripe_id(self, stripe_event_id: str) -> Optional[dict]:
        """Retrieve webhook by Stripe event ID"""
        
        query = """
            SELECT * FROM stripe_webhook_events
            WHERE stripe_event_id = $1
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(query, stripe_event_id)
        return dict(result) if result else None
    
    async def get_raw_payload(self, stripe_event_id: str) -> Optional[dict]:
        """Get raw payload for dispute evidence"""
        
        query = """
            SELECT raw_payload FROM stripe_webhook_events
            WHERE stripe_event_id = $1
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(query, stripe_event_id)
        return result['raw_payload'] if result else None


# Stripe webhook handler integration
STRIPE_WEBHOOK_HANDLER = '''
import stripe
from .webhook_store import StripeWebhookStore

stripe_webhook_store = StripeWebhookStore(db_pool)

@webhook_router.post("/webhook")
async def handle_stripe_webhook(request: Request):
    """A-08: Store raw webhook before processing"""
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except ValueError:
        return JSONResponse({"error": "Invalid payload"}, status_code=400)
    except stripe.error.SignatureVerificationError:
        return JSONResponse({"error": "Invalid signature"}, status_code=400)
    
    # A-08: Store raw webhook first (before any processing)
    await stripe_webhook_store.store_raw(
        stripe_event_id=event["id"],
        event_type=event["type"],
        payload=event["data"]["object"],
        stripe_webhook_id=event.get("webhook_id")
    )
    
    # Then process the event
    await process_stripe_event(event)
    
    return JSONResponse({"received": True})

async def process_stripe_event(event):
    """Process stored webhook event"""
    
    event_type = event["type"]
    data = event["data"]["object"]
    
    if event_type == "payment_intent.succeeded":
        # Handle successful payment
        await stripe_webhook_store.update_status(
            stripe_event_id=event["id"],
            status=WebhookStatus.COMPLETED,
            customer_id=data.get("metadata", {}).get("customer_id")
        )
    
    elif event_type == "charge.refunded":
        # Handle refund
        await stripe_webhook_store.update_status(
            stripe_event_id=event["id"],
            status=WebhookStatus.COMPLETED
        )
    
    # ... handle other event types
'''
