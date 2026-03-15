"""
NexusOS Observability Module
=============================
Real-time metrics, health checks, and alerting for enterprise monitoring.
"""

import os
import time
import psutil
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

observability_bp = Blueprint('observability', __name__)

# Thresholds for alerting
ALERT_THRESHOLDS = {
    'cpu_percent': 80.0,
    'memory_percent': 85.0,
    'disk_percent': 90.0,
}

def get_system_metrics():
    """Collect current system metrics"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    network = psutil.net_io_counters()
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'cpu': {
            'percent': cpu_percent,
            'count': psutil.cpu_count(),
            'alert': cpu_percent > ALERT_THRESHOLDS['cpu_percent']
        },
        'memory': {
            'total_mb': memory.total / (1024 * 1024),
            'available_mb': memory.available / (1024 * 1024),
            'used_mb': memory.used / (1024 * 1024),
            'percent': memory.percent,
            'alert': memory.percent > ALERT_THRESHOLDS['memory_percent']
        },
        'disk': {
            'total_gb': disk.total / (1024 * 1024 * 1024),
            'used_gb': disk.used / (1024 * 1024 * 1024),
            'free_gb': disk.free / (1024 * 1024 * 1024),
            'percent': disk.percent,
            'alert': disk.percent > ALERT_THRESHOLDS['disk_percent']
        },
        'network': {
            'bytes_sent': network.bytes_sent,
            'bytes_recv': network.bytes_recv,
            'packets_sent': network.packets_sent,
            'packets_recv': network.packets_recv
        },
        'uptime_seconds': time.time() - psutil.boot_time()
    }

def get_process_metrics():
    """Get metrics for NexusOS process"""
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
        try:
            if 'python' in proc.info['name'].lower() or 'gunicorn' in proc.info['name'].lower():
                pinfo = proc.info
                return {
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': pinfo['cpu_percent'],
                    'memory_percent': pinfo['memory_percent'],
                    'create_time': pinfo['create_time'],
                    'uptime_seconds': time.time() - pinfo['create_time']
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

# ==================== ROUTES ====================

@observability_bp.route('/api/observability/metrics', methods=['GET'])
def get_metrics():
    """Get full system observability metrics"""
    return jsonify({
        'system': get_system_metrics(),
        'process': get_process_metrics(),
        'alerts': get_active_alerts()
    })

@observability_bp.route('/api/observability/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    metrics = get_system_metrics()
    
    # Determine health status
    health = 'healthy'
    if metrics['cpu']['alert'] or metrics['memory']['alert'] or metrics['disk']['alert']:
        health = 'degraded'
    if metrics['cpu']['percent'] > 95 or metrics['memory']['percent'] > 95:
        health = 'unhealthy'
    
    return jsonify({
        'status': health,
        'timestamp': metrics['timestamp'],
        'checks': {
            'database': check_database(),
            'redis': check_redis(),
            'ollama': check_ollama()
        }
    })

@observability_bp.route('/api/observability/alerts', methods=['GET'])
def get_alerts():
    """Get active alerts"""
    return jsonify(get_active_alerts())

def get_active_alerts():
    """Get all active system alerts"""
    metrics = get_system_metrics()
    alerts = []
    
    if metrics['cpu']['alert']:
        alerts.append({
            'severity': 'warning',
            'metric': 'cpu_percent',
            'value': metrics['cpu']['percent'],
            'threshold': ALERT_THRESHOLDS['cpu_percent'],
            'message': f"CPU usage at {metrics['cpu']['percent']}%"
        })
    
    if metrics['memory']['alert']:
        alerts.append({
            'severity': 'warning',
            'metric': 'memory_percent',
            'value': metrics['memory']['percent'],
            'threshold': ALERT_THRESHOLDS['memory_percent'],
            'message': f"Memory usage at {metrics['memory']['percent']}%"
        })
    
    if metrics['disk']['alert']:
        alerts.append({
            'severity': 'warning',
            'metric': 'disk_percent',
            'value': metrics['disk']['percent'],
            'threshold': ALERT_THRESHOLDS['disk_percent'],
            'message': f"Disk usage at {metrics['disk']['percent']}%"
        })
    
    return alerts

def check_database():
    """Check database connectivity"""
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://nexusos:nexusos@localhost:5432/nexusos'))
        conn.close()
        return 'ok'
    except Exception as e:
        return f'error: {str(e)[:50]}'

def check_redis():
    """Check Redis connectivity"""
    try:
        import redis
        r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        r.ping()
        return 'ok'
    except Exception as e:
        return f'error: {str(e)[:50]}'

def check_ollama():
    """Check Ollama connectivity"""
    try:
        import requests
        ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        resp = requests.get(f"{ollama_url}/api/tags", timeout=2)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            return {'status': 'ok', 'models': len(models)}
        return 'error'
    except Exception as e:
        return f'error: {str(e)[:50]}'

# Integration: Add these routes to your Flask app
# from observability import observability_bp
# app.register_blueprint(observability_bp)
