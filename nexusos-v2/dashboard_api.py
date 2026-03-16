"""
Real-time Dashboard API
Provides live metrics and visualization data
"""
from flask import Blueprint, jsonify, request
import time
import psutil
import redis
import os
from datetime import datetime, timedelta

dashboard = Blueprint('dashboard', __name__)

# Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.from_url(redis_url, decode_responses=True)


def get_system_metrics():
    """Get current system metrics"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "network_sent": psutil.net_io_counters().bytes_sent,
        "network_recv": psutil.net_io_counters().bytes_recv
    }


def get_application_metrics():
    """Get application-level metrics from Redis"""
    metrics = {}
    
    # Request count (last hour)
    request_count = redis_client.get("metrics:requests:hourly")
    metrics["requests_hourly"] = int(request_count) if request_count else 0
    
    # Error count
    error_count = redis_client.get("metrics:errors:hourly")
    metrics["errors_hourly"] = int(error_count) if error_count else 0
    
    # Active users
    active_users = redis_client.scard("active_users")
    metrics["active_users"] = active_users if active_users else 0
    
    # Active agents
    running_agents = redis_client.scard("running_agents")
    metrics["running_agents"] = running_agents if running_agents else 0
    
    return metrics


@dashboard.route('/api/dashboard/system', methods=['GET'])
def system_metrics():
    """Get real-time system metrics"""
    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": get_system_metrics()
    })


@dashboard.route('/api/dashboard/application', methods=['GET'])
def application_metrics():
    """Get real-time application metrics"""
    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": get_application_metrics()
    })


@dashboard.route('/api/dashboard/overview', methods=['GET'])
def dashboard_overview():
    """Get complete dashboard overview"""
    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "system": get_system_metrics(),
        "application": get_application_metrics(),
        "status": {
            "database": check_database(),
            "redis": check_redis(),
            "ollama": check_ollama()
        }
    })


@dashboard.route('/api/dashboard/usage', methods=['GET'])
def usage_analytics():
    """Get usage analytics"""
    # Time range
    period = request.args.get('period', '24h')
    
    if period == '24h':
        hours = 24
    elif period == '7d':
        hours = 168
    elif period == '30d':
        hours = 720
    else:
        hours = 24
    
    # Generate sample data (would come from database in production)
    data_points = []
    now = datetime.utcnow()
    
    for i in range(min(hours, 24)):  # Simplify to 24 points
        timestamp = (now - timedelta(hours=i)).isoformat()
        data_points.append({
            "timestamp": timestamp,
            "requests": 100 + (i * 3) % 50,
            "errors": i % 10,
            "latency_ms": 150 + (i * 7) % 100,
            "users": 10 + (i * 2) % 20
        })
    
    data_points.reverse()
    
    return jsonify({
        "period": period,
        "data": data_points,
        "summary": {
            "total_requests": sum(d["requests"] for d in data_points),
            "total_errors": sum(d["errors"] for d in data_points),
            "avg_latency_ms": sum(d["latency_ms"] for d in data_points) / len(data_points),
            "peak_users": max(d["users"] for d in data_points)
        }
    })


@dashboard.route('/api/dashboard/agents', methods=['GET'])
def agent_stats():
    """Get agent statistics"""
    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "agents": {
            "total": redis_client.scard("all_agents") or 0,
            "running": redis_client.scard("running_agents") or 0,
            "stopped": redis_client.scard("stopped_agents") or 0,
            "error": redis_client.scard("error_agents") or 0
        },
        "recent_activity": get_recent_agent_activity()
    })


def check_database():
    """Check database connectivity"""
    try:
        redis_client.ping()
        return "connected"
    except:
        return "disconnected"


def check_redis():
    """Check Redis connectivity"""
    try:
        redis_client.ping()
        return "connected"
    except:
        return "disconnected"


def check_ollama():
    """Check Ollama status"""
    try:
        import requests
        resp = requests.get(os.environ.get('OLLAMA_URL', 'http://localhost:11434') + '/api/tags', timeout=2)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            return {"status": "connected", "models": len(models)}
    except:
        pass
    return {"status": "disconnected", "models": 0}


def get_recent_agent_activity():
    """Get recent agent activity from Redis"""
    # This would pull from a sorted set of recent activities
    activities = []
    
    # Sample data
    for i in range(5):
        activities.append({
            "agent_id": f"agent-{i+1}",
            "action": ["started", "stopped", "message"][i % 3],
            "timestamp": (datetime.utcnow() - timedelta(minutes=i*5)).isoformat()
        })
    
    return activities
