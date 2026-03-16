"""
NexusOS Memory Consolidation System - PostgreSQL Version

Handles:
1. Consolidation - distills memories into importance scores
2. Memory profile - what the agent knows about you
3. Timeline - chronological view
"""

import os
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

# Use PostgreSQL via psycopg2
DB_URL = os.environ.get('DATABASE_URL', '')

class ConsolidationJob:
    """Background job for memory consolidation"""
    
    def __init__(self):
        self._running = False
        self._thread = None
    
    def _get_conn(self):
        import psycopg2
        return psycopg2.connect(DB_URL)
    
    def run_consolidation(self, user_id: str = None) -> Dict:
        """Run memory consolidation for user(s)"""
        results = {'consolidated': 0, 'forgotten': 0}
        
        with self._get_conn() as conn:
            conn.autocommit = True
            c = conn.cursor()
            
            # Get users to process
            if user_id:
                users = [(user_id,)]
            else:
                c.execute("SELECT DISTINCT user_id FROM memory WHERE memory_type = 'conversation'")
                users = c.fetchall()
            
            for (uid,) in users:
                # Score importance of recent memories
                self._score_importance(c, uid)
                results['consolidated'] += 1
                
                # Forget old low-importance memories
                forgotten = self._forget_memories(c, uid)
                results['forgotten'] += forgotten
        
        return results
    
    def _score_importance(self, c, uid: str):
        """Score importance of recent memories based on content analysis"""
        c.execute("""
            SELECT id, content FROM memory 
            WHERE user_id = %s AND memory_type = 'conversation'
            AND created_at > NOW() - INTERVAL '24 hours'
            LIMIT 100
        """, (uid,))
        
        memories = c.fetchall()
        for mid, content in memories:
            # Simple heuristic scoring
            importance = 0.5
            content_lower = content.lower() if content else ''
            
            # High importance signals
            important_keywords = ['remember', 'important', 'never', 'always', 'hate', 'love', 'decision', 'worry', 'preference']
            if any(kw in content_lower for kw in important_keywords):
                importance = 0.8
            elif len(content or '') > 200:
                importance = 0.7
    def _forget_memories(self, c, uid: str) -> int:
        """Remove old memories (simple version - just log)"""
        # For now, we don't actually delete - just return 0
        # In production, would delete old low-importance memories
        return 0


class MemoryVisualizer:
    """API for users to see what the agent knows about them"""
    
    def __init__(self):
        self._db_url = DB_URL
    
    def _get_conn(self):
        import psycopg2
        return psycopg2.connect(self._db_url)
    
    def get_user_memory_profile(self, uid: str) -> Dict:
        """Get complete memory profile for user"""
        with self._get_conn() as conn:
            conn.autocommit = True
            c = conn.cursor()
            
            # Get memory counts by type
            c.execute("""
                SELECT memory_type, COUNT(*) 
                FROM memory 
                WHERE user_id = %s 
                GROUP BY memory_type
            """, (uid,))
            
            type_counts = {row[0]: row[1] for row in c.fetchall()}
            
            # Get recent memories
            c.execute("""
                SELECT memory_type, content, created_at
                FROM memory 
                WHERE user_id = %s 
                ORDER BY created_at DESC LIMIT 20
            """, (uid,))
            
            recent = [
                {'type': r[0], 'content': r[1][:200] if r[1] else '', 'created_at': str(r[2])}
                for r in c.fetchall()
            ]
            
            # Get total count
            c.execute("SELECT COUNT(*) FROM memory WHERE user_id = %s", (uid,))
            total = c.fetchone()[0]
            
            return {
                'memory_types': type_counts,
                'recent_memories': recent,
                'total_memories': total,
                'user_id': uid
            }
    
    def get_memory_timeline(self, uid: str, days: int = 7) -> List[Dict]:
        """Get chronological timeline of memories"""
        with self._get_conn() as conn:
            conn.autocommit = True
            c = conn.cursor()
            
            c.execute("""
                SELECT memory_type, content, created_at
                FROM memory 
                WHERE user_id = %s AND created_at > NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
            """, (uid, days))
            
            return [
                {'type': r[0], 'content': r[1], 'timestamp': str(r[2])}
                for r in c.fetchall()
            ]


# Global instance
_consolidation: Optional[ConsolidationJob] = None
_visualizer: Optional[MemoryVisualizer] = None

def get_consolidation() -> ConsolidationJob:
    global _consolidation
    if _consolidation is None:
        _consolidation = ConsolidationJob()
    return _consolidation

def get_memory_visualizer() -> MemoryVisualizer:
    global _visualizer
    if _visualizer is None:
        _visualizer = MemoryVisualizer()
    return _visualizer
