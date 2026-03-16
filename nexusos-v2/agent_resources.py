"""
Agent Resource Limits - CPU, Memory, Disk, Rate Limits
===================================================
Enterprise-grade resource governance per agent.
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits for an agent"""
    cpu_percent: int = 100      # Max CPU %
    memory_mb: int = 512         # Max memory MB
    disk_io_mb: int = 100      # Max disk I/O MB/s
    requests_per_minute: int = 60  # API rate limit
    network_egress_mb: int = 50 # Max network egress MB


class AgentResourceManager:
    """
    Manages resource limits per agent.
    
    Features:
    - Per-agent CPU limits
    - Per-agent memory limits  
    - Per-agent disk I/O limits
    - Per-agent rate limiting
    - Per-agent network limits
    """
    
    # Default limits per tier
    TIER_LIMITS = {
        "free": ResourceLimits(
            cpu_percent=25,
            memory_mb=128,
            disk_io_mb=10,
            requests_per_minute=10,
            network_egress_mb=5
        ),
        "basic": ResourceLimits(
            cpu_percent=50,
            memory_mb=256,
            disk_io_mb=50,
            requests_per_minute=60,
            network_egress_mb=25
        ),
        "pro": ResourceLimits(
            cpu_percent=100,
            memory_mb=512,
            disk_io_mb=100,
            requests_per_minute=300,
            network_egress_mb=100
        ),
        "enterprise": ResourceLimits(
            cpu_percent=200,  # Can use 2 cores
            memory_mb=2048,
            disk_io_mb=500,
            requests_per_minute=1000,
            network_egress_mb=1000
        )
    }
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.environ.get('DATABASE_URL',
            'postgresql://nexusos:nexusos@localhost:5432/nexusos')
        self._init_db()
        
        # In-memory rate limiting
        self._rate_limits = {}  # {agent_id: [timestamps]}
    
    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def _init_db(self):
        """Initialize resource tracking tables"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Agent resource limits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_resources (
                agent_id TEXT PRIMARY KEY,
                cpu_percent INTEGER DEFAULT 100,
                memory_mb INTEGER DEFAULT 512,
                disk_io_mb INTEGER DEFAULT 100,
                requests_per_minute INTEGER DEFAULT 60,
                network_egress_mb INTEGER DEFAULT 50,
                current_cpu_percent REAL DEFAULT 0,
                current_memory_mb INTEGER DEFAULT 0,
                current_disk_io_mb REAL DEFAULT 0,
                requests_last_minute INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Resource usage history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_usage_log (
                id SERIAL PRIMARY KEY,
                agent_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW(),
                cpu_percent REAL,
                memory_mb INTEGER,
                disk_io_mb REAL,
                requests_count INTEGER,
                network_egress_mb REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def set_limits(self, agent_id: str, limits: ResourceLimits) -> Dict:
        """Set resource limits for an agent"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_resources 
            (agent_id, cpu_percent, memory_mb, disk_io_mb, requests_per_minute, network_egress_mb)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (agent_id) DO UPDATE SET
                cpu_percent = EXCLUDED.cpu_percent,
                memory_mb = EXCLUDED.memory_mb,
                disk_io_mb = EXCLUDED.disk_io_mb,
                requests_per_minute = EXCLUDED.requests_per_minute,
                network_egress_mb = EXCLUDED.network_egress_mb,
                updated_at = NOW()
        """, (agent_id, limits.cpu_percent, limits.memory_mb, limits.disk_io_mb,
              limits.requests_per_minute, limits.network_egress_mb))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Set resource limits for agent {agent_id}: CPU={limits.cpu_percent}%, Mem={limits.memory_mb}MB")
        return {"success": True, "agent_id": agent_id, "limits": limits.__dict__}
    
    def get_limits(self, agent_id: str) -> ResourceLimits:
        """Get resource limits for an agent"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM agent_resources WHERE agent_id = %s
        """, (agent_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ResourceLimits(
                cpu_percent=row['cpu_percent'],
                memory_mb=row['memory_mb'],
                disk_io_mb=row['disk_io_mb'],
                requests_per_minute=row['requests_per_minute'],
                network_egress_mb=row['network_egress_mb']
            )
        
        # Default limits
        return self.TIER_LIMITS["free"]
    
    def apply_tier_limits(self, agent_id: str, tier: str) -> Dict:
        """Apply predefined tier limits to an agent"""
        if tier not in self.TIER_LIMITS:
            tier = "free"
        
        return self.set_limits(agent_id, self.TIER_LIMITS[tier])
    
    def check_rate_limit(self, agent_id: str) -> Dict:
        """
        Check if agent is within rate limits.
        Uses sliding window approach.
        """
        limits = self.get_limits(agent_id)
        now = time.time()
        window = 60  # 1 minute window
        
        # Initialize if needed
        if agent_id not in self._rate_limits:
            self._rate_limits[agent_id] = []
        
        # Clean old timestamps
        self._rate_limits[agent_id] = [
            ts for ts in self._rate_limits[agent_id]
            if now - ts < window
        ]
        
        # Check limit
        current_count = len(self._rate_limits[agent_id])
        allowed = current_count < limits.requests_per_minute
        
        if allowed:
            self._rate_limits[agent_id].append(now)
        
        return {
            "allowed": allowed,
            "current": current_count,
            "limit": limits.requests_per_minute,
            "reset_seconds": window - (now - self._rate_limits[agent_id][0]) if self._rate_limits[agent_id] else 0
        }
    
    def record_usage(self, agent_id: str, cpu_percent: float = 0, 
                    memory_mb: int = 0, disk_io_mb: float = 0,
                    requests_count: int = 0, network_egress_mb: float = 0):
        """Record current resource usage for an agent"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Update current usage
        cursor.execute("""
            UPDATE agent_resources SET
                current_cpu_percent = %s,
                current_memory_mb = %s,
                current_disk_io_mb = %s,
                requests_last_minute = %s,
                updated_at = NOW()
            WHERE agent_id = %s
        """, (cpu_percent, memory_mb, disk_io_mb, requests_count, agent_id))
        
        # Log to history
        cursor.execute("""
            INSERT INTO resource_usage_log 
            (agent_id, cpu_percent, memory_mb, disk_io_mb, requests_count, network_egress_mb)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (agent_id, cpu_percent, memory_mb, disk_io_mb, requests_count, network_egress_mb))
        
        conn.commit()
        conn.close()
    
    def get_usage(self, agent_id: str) -> Dict:
        """Get current resource usage for an agent"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM agent_resources WHERE agent_id = %s
        """, (agent_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"error": "Agent not found"}
        
        limits = self.get_limits(agent_id)
        
        return {
            "agent_id": agent_id,
            "limits": {
                "cpu_percent": limits.cpu_percent,
                "memory_mb": limits.memory_mb,
                "disk_io_mb": limits.disk_io_mb,
                "requests_per_minute": limits.requests_per_minute,
                "network_egress_mb": limits.network_egress_mb
            },
            "current": {
                "cpu_percent": row['current_cpu_percent'],
                "memory_mb": row['current_memory_mb'],
                "disk_io_mb": row['current_disk_io_mb'],
                "requests_last_minute": row['requests_last_minute']
            },
            "utilization": {
                "cpu": (row['current_cpu_percent'] / limits.cpu_percent * 100) if limits.cpu_percent > 0 else 0,
                "memory": (row['current_memory_mb'] / limits.memory_mb * 100) if limits.memory_mb > 0 else 0
            }
        }
    
    def get_all_agents_usage(self) -> List[Dict]:
        """Get usage for all agents"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM agent_resources ORDER BY updated_at DESC
        """)
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results


# Singleton
_resource_manager = None

def get_resource_manager(db_url: str = None) -> AgentResourceManager:
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = AgentResourceManager(db_url)
    return _resource_manager