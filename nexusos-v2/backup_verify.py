"""
Backup Verification Module
==========================
Automated backup verification and retention policies
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List


class BackupVerifier:
    """
    Verify backups and enforce retention policies
    """
    
    def __init__(self, db_url: str = None, redis_url: str = None):
        self.db_url = db_url or os.environ.get('DATABASE_URL')
        self.redis_url = redis_url or os.environ.get('REDIS_URL')
    
    def verify_postgres_backup(self) -> Dict:
        """Verify PostgreSQL backup exists and is recent"""
        try:
            import psycopg2
            
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Check last backup timestamp (stored in a table)
            cursor.execute("""
                SELECT backup_id, created_at 
                FROM system_backups 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                backup_id, created_at = result
                age_hours = (datetime.utcnow() - created_at).total_seconds() / 3600
                
                return {
                    "status": "ok" if age_hours < 24 else "stale",
                    "backup_id": str(backup_id),
                    "age_hours": round(age_hours, 1),
                    "last_backup": created_at.isoformat()
                }
            
            return {"status": "no_backup", "message": "No backups found"}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def verify_redis_backup(self) -> Dict:
        """Verify Redis persistence"""
        try:
            import redis
            r = redis.from_url(self.redis_url)
            
            # Check RDB persistence
            info = r.info('persistence')
            
            return {
                "status": "ok" if info.get('rdb_bgsave_in_progress') == False else "saving",
                "rdb_changes_since_last_save": info.get('rdb_changes_since_last_save'),
                "last_save_time": info.get('rdb_last_save_time')
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def cleanup_old_backups(self, retention_days: int = 30) -> Dict:
        """Clean up old backup files"""
        import subprocess
        
        cleanup_results = []
        
        # Define backup locations
        backup_dirs = [
            '/backups',
            '/app/backups',
            '/data/backups'
        ]
        
        cutoff = time.time() - (retention_days * 86400)
        
        for backup_dir in backup_dirs:
            try:
                # Find and remove old files
                result = subprocess.run(
                    f'find {backup_dir} -type f -mtime +{retention_days} -delete 2>/dev/null',
                    shell=True,
                    capture_output=True
                )
                cleanup_results.append(f"{backup_dir}: cleaned")
            except Exception as e:
                cleanup_results.append(f"{backup_dir}: {e}")
        
        return {
            "status": "completed",
            "retention_days": retention_days,
            "results": cleanup_results
        }
    
    def verify_all(self) -> Dict:
        """Run all backup verifications"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "postgres": self.verify_postgres_backup(),
            "redis": self.verify_redis_backup(),
            "cleanup": self.cleanup_old_backups()
        }


def run_backup_verification():
    """Entry point for cron job"""
    verifier = BackupVerifier()
    result = verifier.verify_all()
    
    # Log result to audit
    print(json.dumps(result))
    
    return result


# Run if called directly
if __name__ == "__main__":
    run_backup_verification()