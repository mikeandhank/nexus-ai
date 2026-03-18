"""
Observability Module
====================
Prometheus metrics, health dashboards, alerting
"""
import os
import time
import psutil
from functools import wraps
from datetime import datetime
from typing import Dict, Callable


class MetricsCollector:
    """
    Collect and export metrics for Prometheus/Grafana
    """
    
    def __init__(self):
        self.metrics = {
            "requests_total": 0,
            "requests_by_endpoint": {},
            "requests_by_status": {},
            "request_duration_sum": 0,
            "errors_total": 0,
            "active_connections": 0,
        }
        self.start_time = time.time()
    
    def record_request(self, endpoint: str, status: int, duration_ms: float):
        """Record API request"""
        self.metrics["requests_total"] += 1
        self.metrics["request_duration_sum"] += duration_ms
        
        # By endpoint
        if endpoint not in self.metrics["requests_by_endpoint"]:
            self.metrics["requests_by_endpoint"][endpoint] = 0
        self.metrics["requests_by_endpoint"][endpoint] += 1
        
        # By status
        status_bucket = f"{status // 100}xx"
        if status_bucket not in self.metrics["requests_by_status"]:
            self.metrics["requests_by_status"][status_bucket] = 0
        self.metrics["requests_by_status"][status_bucket] += 1
    
    def record_error(self, error_type: str):
        """Record error"""
        self.metrics["errors_total"] += 1
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        uptime_seconds = time.time() - self.start_time
        
        avg_duration = (
            self.metrics["request_duration_sum"] / 
            self.metrics["requests_total"] 
            if self.metrics["requests_total"] > 0 else 0
        )
        
        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "requests_total": self.metrics["requests_total"],
            "requests_per_second": round(
                self.metrics["requests_total"] / uptime_seconds, 2
            ) if uptime_seconds > 0 else 0,
            "average_duration_ms": round(avg_duration, 2),
            "errors_total": self.metrics["errors_total"],
            "error_rate": round(
                self.metrics["errors_total"] / self.metrics["requests_total"] * 100, 2
            ) if self.metrics["requests_total"] > 0 else 0,
            "by_endpoint": self.metrics["requests_by_endpoint"],
            "by_status": self.metrics["requests_by_status"],
            "system": self.get_system_metrics()
        }
    
    def get_system_metrics(self) -> Dict:
        """Get system-level metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "connections_established": len(psutil.net_connections())
        }
    
    def export_prometheus(self) -> str:
        """Export in Prometheus format"""
        metrics = self.get_metrics()
        lines = []
        
        # Core metrics
        lines.append(f'nexusos_requests_total {metrics["requests_total"]}')
        lines.append(f'nexusos_errors_total {metrics["errors_total"]}')
        lines.append(f'nexusos_uptime_seconds {metrics["uptime_seconds"]}')
        
        # System metrics
        sys = metrics["system"]
        lines.append(f'nexusos_cpu_percent {sys["cpu_percent"]}')
        lines.append(f'nexusos_memory_percent {sys["memory_percent"]}')
        lines.append(f'nexusos_disk_percent {sys["disk_percent"]}')
        
        return "\n".join(lines) + "\n"


# Decorator for automatic metrics
def track_metrics(f: Callable) -> Callable:
    """Decorator to track function metrics"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        start = time.time()
        try:
            result = f(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            
            # Record in metrics collector
            collector = get_metrics_collector()
            collector.record_request(
                endpoint=f.__name__,
                status=200,
                duration_ms=duration_ms
            )
            
            return result
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            
            collector = get_metrics_collector()
            collector.record_request(
                endpoint=f.__name__,
                status=500,
                duration_ms=duration_ms
            )
            collector.record_error(type(e).__name__)
            
            raise
    
    return wrapped


# Singleton
_metrics_collector = None

def get_metrics_collector() -> MetricsCollector:
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Prometheus metrics endpoint
def get_prometheus_metrics():
    """Return metrics in Prometheus format"""
    collector = get_metrics_collector()
    return collector.export_prometheus(), 200, {
        'Content-Type': 'text/plain; charset=utf-8'
    }