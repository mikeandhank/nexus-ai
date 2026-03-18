"""
Deep Health Check Module
========================
Comprehensive health checks for all dependencies
"""
import os
import time
from typing import Dict
from datetime import datetime


class HealthChecker:
    """
    Deep health checker for NexusOS
    """
    
    def __init__(self):
        self.checks = []
    
    def check_postgres(self) -> Dict:
        """Check PostgreSQL connectivity"""
        try:
            import psycopg2
            db_url = os.environ.get('DATABASE_URL', 
                'postgresql://nexusos:nexusos@nexusos-postgres:5432/nexusos')
            conn = psycopg2.connect(db_url, connect_timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            conn.close()
            
            return {"status": "healthy", "users": count}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def check_redis(self) -> Dict:
        """Check Redis connectivity"""
        try:
            import redis
            r = redis.from_url(
                os.environ.get('REDIS_URL', 'redis://nexusos-redis:6379/0'),
                socket_connect_timeout=5
            )
            r.ping()
            info = r.info()
            return {
                "status": "healthy",
                "connected_clients": info.get('connected_clients', 0),
                "used_memory": info.get('used_memory_human', 'N/A')
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def check_ollama(self) -> Dict:
        """Check Ollama connectivity and models"""
        try:
            import requests
            base_url = os.environ.get('OLLAMA_BASE_URL', 'http://nexusos-ollama:11434')
            
            # Check base connectivity
            resp = requests.get(f"{base_url}/api/tags", timeout=5)
            
            if resp.status_code == 200:
                models = resp.json().get('models', [])
                return {
                    "status": "healthy",
                    "models": [m.get('name') for m in models],
                    "model_count": len(models)
                }
            
            return {"status": "unhealthy", "error": f"Status {resp.status_code}"}
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def check_disk(self) -> Dict:
        """Check disk space"""
        try:
            import shutil
            stats = shutil.disk_usage("/")
            free_gb = stats.free / (1024**3)
            
            return {
                "status": "healthy" if free_gb > 1 else "warning",
                "free_gb": round(free_gb, 2),
                "total_gb": round(stats.total / (1024**3), 2),
                "percent_free": round(free_gb / (stats.total / (1024**3)) * 100, 1)
            }
        except Exception as e:
            return {"status": "unknown", "error": str(e)}
    
    def check_memory(self) -> Dict:
        """Check available memory"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            
            return {
                "status": "healthy" if mem.percent < 90 else "warning",
                "percent_used": mem.percent,
                "available_gb": round(mem.available / (1024**3), 2)
            }
        except Exception as e:
            return {"status": "unknown", "error": str(e)}
    
    def check_all(self) -> Dict:
        """Run all health checks"""
        checks = {
            "postgresql": self.check_postgres(),
            "redis": self.check_redis(),
            "ollama": self.check_ollama(),
            "disk": self.check_disk(),
            "memory": self.check_memory()
        }
        
        # Determine overall status
        statuses = [c.get("status") for c in checks.values()]
        
        if any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        elif any(s == "warning" for s in statuses):
            overall = "degraded"
        else:
            overall = "healthy"
        
        return {
            "status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    
    def get_readiness(self) -> bool:
        """Check if service is ready to accept traffic"""
        checks = self.check_all()
        
        # Service is ready if postgres and redis are healthy
        return (
            checks["checks"]["postgresql"]["status"] == "healthy" and
            checks["checks"]["redis"]["status"] == "healthy"
        )


# Singleton
_health_checker = None

def get_health_checker() -> HealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker