-- Migration: Add tenant_id to tables for multi-tenant support
-- Run this on the PostgreSQL database

-- Add tenant_id to agents table if it doesn't exist
ALTER TABLE agents ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

-- Add tenant_id to usage_stats table if it doesn't exist  
ALTER TABLE usage_stats ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

-- Add tenant_id to conversations table if it doesn't exist
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

-- Add index for faster tenant-based queries
CREATE INDEX IF NOT EXISTS idx_agents_tenant ON agents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_tenant ON usage_stats(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversations(tenant_id);
