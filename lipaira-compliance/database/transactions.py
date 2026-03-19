"""
A-07: Transaction Ledger Table
Append-only PostgreSQL table for financial transactions
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from enum import Enum


# SQL Migration Script
MIGRATION_UP = """
-- A-07: Transaction Ledger Table
-- Append-only, no UPDATE or DELETE for application roles

-- Enable row-level security for insert-only
ALTER TABLE transaction_ledger ENABLE ROW LEVEL SECURITY;

-- Create the table
CREATE TABLE IF NOT EXISTS transaction_ledger (
    -- Primary identification
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Customer reference
    customer_id UUID NOT NULL,
    
    -- Event type
    event_type VARCHAR(50) NOT NULL CHECK (
        event_type IN (
            'purchase', 
            'refund', 
            'dispute', 
            'payout',
            'credit_consumption'
            -- Note: credit_expiry removed - credits NEVER expire (policy 2026-03-19)
        )
    ),
    
    -- Amount (in cents)
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Credit tracking (2026-03-19 pricing model)
    credits_delta INTEGER NOT NULL DEFAULT 0,
    credits_received INTEGER NOT NULL DEFAULT 0,  -- What customer gets
    running_balance INTEGER NOT NULL DEFAULT 0,
    
    -- Payment references
    stripe_payment_intent_id VARCHAR(255),
    stripe_charge_id VARCHAR(255),
    openrouter_request_id VARCHAR(255),
    
    -- Fee tracking (5.5% service fee - non-refundable)
    service_fee_cents INTEGER NOT NULL DEFAULT 0,
    
    -- Actor
    actor VARCHAR(50) NOT NULL DEFAULT 'system',
    actor_id VARCHAR(255),
    
    -- Metadata (JSONB for flexibility)
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT positive_amount CHECK (amount_cents >= 0)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_transaction_customer 
    ON transaction_ledger(customer_id);
CREATE INDEX IF NOT EXISTS idx_transaction_created 
    ON transaction_ledger(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transaction_stripe 
    ON transaction_ledger(stripe_payment_intent_id) 
    WHERE stripe_payment_intent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_transaction_type 
    ON transaction_ledger(event_type, created_at DESC);

-- Create function to prevent updates/deletes
CREATE OR REPLACE FUNCTION prevent_transaction_update()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'UPDATE and DELETE operations are prohibited on transaction_ledger';
END;
$$ LANGUAGE plpgsql;

-- Apply trigger (comment out to allow migrations, enable for production)
-- DROP TRIGGER IF EXISTS no_update_transaction ON transaction_ledger;
-- CREATE TRIGGER no_update_transaction
--     BEFORE UPDATE OR DELETE ON transaction_ledger
--     EXECUTE FUNCTION prevent_transaction_update();

-- Insert-only policy for app role
CREATE POLICY transaction_insert_only
    ON transaction_ledger
    FOR INSERT
    TO app
    WITH CHECK (true);

-- Read policy for app role (for computing balances)
CREATE POLICY transaction_read_for_balance
    ON transaction_ledger
    FOR SELECT
    TO app
    USING (true);
"""

MIGRATION_DOWN = """
DROP TABLE IF EXISTS transaction_ledger CASCADE;
DROP FUNCTION IF EXISTS prevent_transaction_update();
"""


class TransactionEventType(str, Enum):
    PURCHASE = "purchase"
    REFUND = "refund"
    DISPUTE = "dispute"
    PAYOUT = "payout"
    CREDIT_CONSUMPTION = "credit_consumption"
    # Note: Credit expiry removed - credits NEVER expire (policy 2026-03-19)


class TransactionLedger:
    """Python interface for transaction ledger operations"""
    
    def __init__(self, db_pool):
        self.db = db_pool
    
    async def add_transaction(
        self,
        customer_id: str,
        event_type: TransactionEventType,
        amount_cents: int,
        token_credits_delta: int = 0,
        stripe_payment_intent_id: str = None,
        stripe_charge_id: str = None,
        openrouter_request_id: str = None,
        actor: str = "system",
        actor_id: str = None,
        metadata: dict = None
    ) -> dict:
        """Add a new transaction (append-only)"""
        
        # Get current running balance
        current_balance = await self.get_balance(customer_id)
        running_balance = current_balance + token_credits_delta
        
        query = """
            INSERT INTO transaction_ledger (
                customer_id, event_type, amount_cents, 
                stripe_payment_intent_id, stripe_charge_id,
                openrouter_request_id, token_credits_delta,
                running_balance, actor, actor_id, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                query,
                customer_id,
                event_type.value,
                amount_cents,
                stripe_payment_intent_id,
                stripe_charge_id,
                openrouter_request_id,
                token_credits_delta,
                running_balance,
                actor,
                actor_id,
                metadata or {}
            )
        
        return dict(result)
    
    async def get_balance(self, customer_id: str) -> int:
        """Get current token credit balance for customer"""
        query = """
            SELECT COALESCE(SUM(token_credits_delta), 0) as balance
            FROM transaction_ledger
            WHERE customer_id = $1
        """
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(query, customer_id)
        return result['balance']
    
    async def get_transactions(
        self, 
        customer_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """Get transaction history for customer"""
        query = """
            SELECT * FROM transaction_ledger
            WHERE customer_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        async with self.db.acquire() as conn:
            results = await conn.fetch(query, customer_id, limit, offset)
        return [dict(r) for r in results]
    
    async def get_by_stripe_payment(self, stripe_payment_intent_id: str) -> dict:
        """Find transaction by Stripe payment intent"""
        query = """
            SELECT * FROM transaction_ledger
            WHERE stripe_payment_intent_id = $1
            LIMIT 1
        """
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(query, stripe_payment_intent_id)
        return dict(result) if result else None


# Example: Event sourcing for credit ledger (A-09)
# Each credit event is an immutable row, balance computed by summing
CREDIT_LEDGER_EXAMPLE = """
-- Event-sourced credit ledger (A-09)
-- Never store a mutable balance - always compute from events

CREATE TABLE credit_ledger_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- purchase, consumption, refund, expiry
    credits_delta INTEGER NOT NULL,  -- + or - 
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    stripe_payment_id VARCHAR(255),
    openrouter_request_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'
);

-- Current balance is always: SELECT SUM(credits_delta) FROM credit_ledger_events WHERE customer_id = $1
"""
