"""
C-07: Terms of Service Version Control
Store all ToS versions with versioning
"""

import hashlib
from datetime import datetime
from typing import Optional
from uuid import uuid4


# ToS Storage Schema
TOS_SQL = """
-- C-07: Terms of Service Version Control
CREATE TABLE IF NOT EXISTS tos_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(50) NOT NULL UNIQUE,
    content_hash VARCHAR(64) NOT NULL,  -- SHA-256 of content
    content_text TEXT NOT NULL,
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    
    CONSTRAINT unique_version UNIQUE (version)
);

-- C-08: ToS Acceptance Logging
CREATE TABLE IF NOT EXISTS tos_acceptance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    tos_version VARCHAR(50) NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    acceptance_method VARCHAR(50) DEFAULT 'web',  -- web, api, email
    
    CONSTRAINT fk_tos_version FOREIGN KEY (tos_version) 
        REFERENCES tos_versions(version)
);

CREATE INDEX idx_tos_acceptance_customer 
    ON tos_acceptance(customer_id, accepted_at DESC);
"""


class ToSManager:
    """C-07 & C-08: ToS version control and acceptance tracking"""
    
    def __init__(self, db_pool, s3_client=None, bucket_name="lipaira-legal"):
        self.db = db_pool
        self.s3_client = s3_client
        self.bucket_name = bucket_name
    
    async def publish_version(
        self,
        version: str,
        content: str,
        effective_date: datetime
    ) -> dict:
        """Publish a new ToS version"""
        
        # Calculate hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Store in database
        query = """
            INSERT INTO tos_versions (version, content_hash, content_text, effective_date)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (version) DO UPDATE SET
                content_hash = EXCLUDED.content_hash,
                content_text = EXCLUDED.content_text,
                effective_date = EXCLUDED.effective_date,
                created_at = NOW()
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                query, version, content_hash, content, effective_date
            )
        
        # Also store in S3 for immutable audit trail
        if self.s3_client:
            s3_key = f"tos/{version}/content.txt"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content.encode(),
                ContentType="text/plain",
                Metadata={
                    "version": version,
                    "hash": content_hash,
                    "effective_date": effective_date.isoformat()
                }
            )
        
        return dict(result)
    
    async def set_active_version(self, version: str) -> bool:
        """Set a version as active (deactivate others)"""
        
        # Deactivate all
        query1 = "UPDATE tos_versions SET is_active = FALSE"
        # Activate target
        query2 = "UPDATE tos_versions SET is_active = TRUE WHERE version = $1"
        
        async with self.db.acquire() as conn:
            await conn.execute(query1)
            await conn.execute(query2, version)
        
        return True
    
    async def get_active_version(self) -> Optional[dict]:
        """Get currently active ToS version"""
        
        query = """
            SELECT * FROM tos_versions
            WHERE is_active = TRUE
            LIMIT 1
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(query)
        
        return dict(result) if result else None
    
    async def accept_tos(
        self,
        customer_id: str,
        version: str,
        ip_address: str = None,
        user_agent: str = None,
        method: str = "web"
    ) -> dict:
        """Log customer's ToS acceptance"""
        
        query = """
            INSERT INTO tos_acceptance (
                customer_id, tos_version, ip_address, user_agent, acceptance_method
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT DO NOTHING
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                query, customer_id, version, ip_address, user_agent, method
            )
        
        return dict(result) if result else {"accepted": True}
    
    async def has_accepted_latest(self, customer_id: str) -> bool:
        """Check if customer has accepted the latest ToS"""
        
        active = await self.get_active_version()
        if not active:
            return True  # No ToS published yet
        
        query = """
            SELECT accepted_at FROM tos_acceptance
            WHERE customer_id = $1 AND tos_version = $2
            ORDER BY accepted_at DESC
            LIMIT 1
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                query, customer_id, active['version']
            )
        
        return result is not None


# Example ToS content structure
TOS_TEMPLATE = {
    "version": "1.0.0",
    "sections": [
        {"id": "1", "title": "Acceptance of Terms", "content": "..."},
        {"id": "2", "title": "Description of Service", "content": "..."},
        {"id": "3", "title": "User Accounts", "content": "..."},
        {"id": "4", "title": "Token Credits", "content": "..."},
        {"id": "5", "title": "Payment and Refunds", "content": "..."},
        {"id": "6", "title": "Acceptable Use", "content": "..."},
        {"id": "7", "title": "Limitation of Liability", "content": "..."},
        {"id": "8", "title": "Privacy", "content": "..."},
        {"id": "9", "title": "Termination", "content": "..."},
        {"id": "10", "title": "Governing Law", "content": "..."},
    ],
    "effective_date": "2026-03-19T00:00:00Z"
}
