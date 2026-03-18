"""
Audit Log Retention Module
==========================
Manages audit log retention policies
"""
import os
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List


class AuditLogManager:
    """
    Manage audit log retention and cleanup
    """
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.environ.get('DATABASE_URL')
    
    def get_log_counts(self) -> Dict:
        """Get current audit log counts"""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM audit_log")
        total = cursor.fetchone()[0]
        
        # Count by age ranges
        now = datetime.utcnow()
        cursor.execute("""
            SELECT COUNT(*) FROM audit_log 
            WHERE created_at > %s
        """, (now - timedelta(days=7),))
        last_7_days = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM audit_log 
            WHERE created_at BETWEEN %s AND %s
        """, (now - timedelta(days=30), now - timedelta(days=7)))
        last_7_to_30 = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM audit_log 
            WHERE created_at < %s
        """, (now - timedelta(days=30),))
        older_than_30 = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total": total,
            "last_7_days": last_7_days,
            "last_7_to_30_days": last_7_to_30,
            "older_than_30_days": older_than_30
        }
    
    def apply_retention_policy(self, retention_days: int = 90) -> Dict:
        """
        Apply retention policy
        
        Default: Keep 90 days, archive before that
        """
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        # Archive old logs (move to archive table or export)
        try:
            # Create archive table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log_archive (
                    LIKE audit_log INCLUDING ALL
                )
            """)
            
            # Move old logs to archive
            cursor.execute("""
                INSERT INTO audit_log_archive
                SELECT * FROM audit_log
                WHERE created_at < %s
            """, (cutoff,))
            
            archived_count = cursor.rowcount
            
            # Delete from main table
            cursor.execute("""
                DELETE FROM audit_log
                WHERE created_at < %s
            """, (cutoff,))
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            
            result = {
                "status": "success",
                "archived": archived_count,
                "deleted": deleted_count,
                "retention_days": retention_days,
                "cutoff_date": cutoff.isoformat()
            }
            
        except Exception as e:
            conn.rollback()
            result = {
                "status": "error",
                "error": str(e)
            }
        
        conn.close()
        return result
    
    def get_storage_stats(self) -> Dict:
        """Get audit log storage statistics"""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        # Table size
        cursor.execute("""
            SELECT pg_size_pretty(pg_total_relation_size('audit_log'))
        """)
        table_size = cursor.fetchone()[0]
        
        # Index size
        cursor.execute("""
            SELECT pg_size_pretty(pg_indexes_size('audit_log'))
        """)
        index_size = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "table_size": table_size,
            "index_size": index_size
        }
    
    def run_maintenance(self) -> Dict:
        """Run full audit log maintenance"""
        return {
            "counts": self.get_log_counts(),
            "retention": self.apply_retention_policy(90),
            "storage": self.get_storage_stats()
        }


def run_audit_maintenance():
    """Entry point for cron job"""
    manager = AuditLogManager()
    result = manager.run_maintenance()
    import json
    print(json.dumps(result, default=str))
    return result