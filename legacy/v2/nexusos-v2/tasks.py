"""
NexusOS Celery Tasks
Background job processing for enterprise workloads
"""
import os
import json
import logging
from datetime import datetime, timedelta
from celery import Celery

logger = logging.getLogger(__name__)

# Initialize Celery
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
celery_app = Celery('nexusos', broker=redis_url, backend=redis_url)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 min soft limit
)

@celery_app.task(bind=True, name='nexusos.agent.run')
def run_agent_task(self, agent_id: str, user_id: str, input_data: dict):
    """Background agent execution task"""
    from agent_runtime import AgentRuntime
    
    logger.info(f"[Celery] Starting agent {agent_id} for user {user_id}")
    
    try:
        runtime = AgentRuntime()
        result = runtime.run_agent(agent_id, input_data)
        
        return {
            'status': 'completed',
            'agent_id': agent_id,
            'result': result,
            'completed_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[Celery] Agent {agent_id} failed: {e}")
        return {
            'status': 'failed',
            'agent_id': agent_id,
            'error': str(e)
        }

@celery_app.task(name='nexusos.usage.collect')
def collect_usage_stats():
    """Periodic task to collect usage statistics"""
    from database_compat import DatabaseCompat
    
    logger.info("[Celery] Collecting usage stats")
    
    try:
        db = DatabaseCompat()
        with db._get_conn() as conn:
            cur = conn.cursor()
            
            # Get today's stats
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(tokens),0), COALESCE(SUM(cost_usd),0)
                FROM usage_logs
                WHERE DATE(created_at) = DATE('now')
            """)
            row = cur.fetchone()
            
            stats = {
                'date': datetime.utcnow().date().isoformat(),
                'requests': row[0] or 0,
                'tokens': row[1] or 0,
                'cost_usd': row[2] or 0
            }
            
            return stats
    except Exception as e:
        logger.error(f"[Celery] Usage collection failed: {e}")
        return {'error': str(e)}

@celery_app.task(name='nexusos.webhook.dispatch')
def dispatch_webhook_async(event_type: str, payload: dict, webhook_urls: list):
    """Async webhook dispatch"""
    import requests
    import hmac
    import hashlib
    
    logger.info(f"[Celery] Dispatching {len(webhook_urls)} webhooks for {event_type}")
    
    results = []
    for url in webhook_urls:
        try:
            secret = os.environ.get('WEBHOOK_SECRET', '')
            data = {
                'event': event_type,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'data': payload
            }
            
            headers = {'Content-Type': 'application/json'}
            if secret:
                body = json.dumps(data)
                signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
                headers['X-NexusOS-Signature'] = f'sha256={signature}'
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            results.append({'url': url, 'status': response.status_code, 'success': True})
        except Exception as e:
            results.append({'url': url, 'error': str(e), 'success': False})
    
    return results

@celery_app.task(name='nexusos.cleanup.sessions')
def cleanup_stale_sessions():
    """Clean up stale sessions"""
    from database_compat import DatabaseCompat
    
    logger.info("[Celery] Cleaning up stale sessions")
    
    try:
        db = DatabaseCompat()
        with db._get_conn() as conn:
            cur = conn.cursor()
            
            # Delete sessions older than 7 days
            cur.execute("""
                DELETE FROM sessions 
                WHERE created_at < datetime('now', '-7 days')
            """)
            deleted = cur.rowcount
            
            return {'deleted_sessions': deleted}
    except Exception as e:
        return {'error': str(e)}

@celery_app.task(name='nexusos.health.check')
def scheduled_health_check():
    """Periodic health check"""
    import requests
    
    logger.info("[Celery] Running scheduled health check")
    
    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }
    
    # Check PostgreSQL
    try:
        from database_compat import DatabaseCompat
        db = DatabaseCompat()
        with db._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            results['checks']['postgresql'] = 'healthy'
    except Exception as e:
        results['checks']['postgresql'] = f'unhealthy: {e}'
    
    # Check Redis
    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        results['checks']['redis'] = 'healthy'
    except Exception as e:
        results['checks']['redis'] = f'unhealthy: {e}'
    
    # Check Ollama
    try:
        ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        results['checks']['ollama'] = 'healthy' if response.ok else 'unhealthy'
    except Exception as e:
        results['checks']['ollama'] = f'unhealthy: {e}'
    
    return results


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'usage-collect-every-hour': {
        'task': 'nexusos.usage.collect',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-sessions-daily': {
        'task': 'nexusos.cleanup.sessions', 
        'schedule': 86400.0,  # Every day
    },
    'health-check-every-5-min': {
        'task': 'nexusos.health.check',
        'schedule': 300.0,  # Every 5 minutes
    },
}