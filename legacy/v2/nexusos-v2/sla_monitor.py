"""
SLA Monitoring Module
Tracks and reports on service level agreements
"""
import time
import redis
import os
from datetime import datetime, timedelta
from collections import defaultdict


class SLAMonitor:
    """
    Monitors and reports SLA metrics
    """
    
    def __init__(self, redis_url: str = None):
        self.redis = redis.from_url(redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        self.metrics_key = "sla:metrics:"
        self.incidents_key = "sla:incidents:"
        
    def record_request(self, endpoint: str, status_code: int, latency_ms: float):
        """Record a request for SLA tracking"""
        now = int(time.time())
        hour_key = f"{self.metrics_key}{endpoint}:{now // 3600}"
        
        pipe = self.redis.pipeline()
        pipe.hincrby(hour_key, "total", 1)
        
        if status_code >= 500:
            pipe.hincrby(hour_key, "errors", 1)
        elif status_code >= 400:
            pipe.hincrby(hour_key, "client_errors", 1)
            
        pipe.hincrbyfloat(hour_key, "latency_sum", latency_ms)
        pipe.expire(hour_key, 86400 * 31)  # Keep 31 days
        
        pipe.execute()
        
        # Check SLA breach
        if status_code >= 500:
            self._check_sla_breach(endpoint)
    
    def _check_sla_breach(self, endpoint: str):
        """Check if SLA is being breached"""
        # Get error rate for last 5 minutes
        now = int(time.time())
        errors = 0
        total = 0
        
        for i in range(5):
            key = f"{self.metrics_key}{endpoint}:{(now - i*60) // 3600}"
            data = self.redis.hgetall(key)
            errors += int(data.get("errors", 0))
            total += int(data.get("total", 0))
        
        if total > 0 and errors / total > 0.05:  # >5% error rate
            self._create_incident(endpoint, "error_rate", errors/total)
    
    def _create_incident(self, endpoint: str, incident_type: str, severity: float):
        """Create an incident record"""
        incident_id = f"{endpoint}:{int(time.time())}"
        self.redis.hset(f"{self.incidents_key}{incident_id}", mapping={
            "endpoint": endpoint,
            "type": incident_type,
            "severity": str(severity),
            "created_at": str(int(time.time())),
            "status": "open"
        })
        self.redis.expire(f"{self.incidents_key}{incident_id}", 86400 * 30)
    
    def get_uptime(self, endpoint: str, hours: int = 24) -> float:
        """Calculate uptime percentage"""
        now = int(time.time())
        total_requests = 0
        total_errors = 0
        
        for i in range(hours):
            key = f"{self.metrics_key}{endpoint}:{(now - i*3600) // 3600}"
            data = self.redis.hgetall(key)
            total_requests += int(data.get("total", 0))
            total_errors += int(data.get("errors", 0))
        
        if total_requests == 0:
            return 100.0
        
        return ((total_requests - total_errors) / total_requests) * 100
    
    def get_avg_latency(self, endpoint: str, hours: int = 24) -> float:
        """Get average latency"""
        now = int(time.time())
        total_latency = 0
        total_requests = 0
        
        for i in range(hours):
            key = f"{self.metrics_key}{endpoint}:{(now - i*3600) // 3600}"
            data = self.redis.hgetall(key)
            total_latency += float(data.get("latency_sum", 0))
            total_requests += int(data.get("total", 0))
        
        if total_requests == 0:
            return 0.0
        
        return total_latency / total_requests
    
    def get_sla_report(self) -> dict:
        """Generate SLA report"""
        endpoints = ["/api/chat", "/api/agents", "/api/status", "/api/auth/login"]
        
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "period": "24h",
            "endpoints": []
        }
        
        for endpoint in endpoints:
            uptime = self.get_uptime(endpoint, 24)
            latency = self.get_avg_latency(endpoint, 24)
            
            # Determine status based on SLA targets
            if uptime >= 99.9:
                status = "healthy"
            elif uptime >= 99.0:
                status = "degraded"
            else:
                status = "critical"
            
            report["endpoints"].append({
                "endpoint": endpoint,
                "uptime_percent": round(uptime, 3),
                "avg_latency_ms": round(latency, 2),
                "status": status
            })
        
        # Calculate overall
        overall_uptime = sum(e["uptime_percent"] for e in report["endpoints"]) / len(report["endpoints"])
        report["overall"] = {
            "uptime_percent": round(overall_uptime, 3),
            "status": "healthy" if overall_uptime >= 99.9 else "degraded" if overall_uptime >= 99.0 else "critical"
        }
        
        return report
    
    def get_incidents(self, hours: int = 24) -> list:
        """Get recent incidents"""
        incidents = []
        now = int(time.time())
        
        for key in self.redis.scan_iter(f"{self.incidents_key}*"):
            data = self.redis.hgetall(key)
            created = int(data.get("created_at", 0))
            
            if now - created < hours * 3600:
                incidents.append({
                    "id": key.replace(self.incidents_key, ""),
                    "endpoint": data.get("endpoint"),
                    "type": data.get("type"),
                    "severity": float(data.get("severity", 0)),
                    "status": data.get("status"),
                    "created_at": datetime.fromtimestamp(created).isoformat()
                })
        
        return sorted(incidents, key=lambda x: x["created_at"], reverse=True)


# SLA Targets
SLA_TARGETS = {
    "uptime": 99.9,  # 99.9% uptime
    "latency_p50": 200,  # 200ms p50
    "latency_p99": 1000,  # 1s p99
    "error_rate": 0.1  # 0.1% error rate
}
