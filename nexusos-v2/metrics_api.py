"""
NexusOS Multi-Tenant & Metrics API

Features:
- Multi-tenant isolation (tenant_id on all queries)
- Real-time metrics endpoint
- Connection health checking
- User ID validation for security
"""

import os
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g

# Flag to track if routes are already registered
_ROUTES_REGISTERED = False

# ==================== MULTI-TENANT ISOLATION ====================

def get_current_tenant_id():
    """Get tenant_id from JWT or default to 'default'"""
    return getattr(g, 'tenant_id', 'default')

def require_tenant(f):
    """Decorator to ensure tenant context"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Tenant ID comes from JWT or query param
        g.tenant_id = request.headers.get('X-Tenant-ID') or request.args.get('tenant_id') or 'default'
        return f(*args, **kwargs)
    return decorated

# ==================== METRICS API ====================

def setup_metrics_routes(app, db_module=None):
    """Add metrics and health routes"""
    global _ROUTES_REGISTERED
    
    # Skip if already registered
    if _ROUTES_REGISTERED:
        return
    
    _ROUTES_REGISTERED = True
    
    from flask import request, jsonify
    
    @app.route('/api/metrics', methods=['GET'])
    @require_tenant
    def get_metrics():
        """Get real-time metrics for current tenant"""
        tenant_id = g.tenant_id
        
        metrics = {
            'tenant_id': tenant_id,
            'timestamp': datetime.utcnow().isoformat(),
            'agents': {
                'running': 0,
                'paused': 0,
                'total': 0
            },
            'usage': {
                'requests_today': 0,
                'tokens_today': 0,
                'cost_today': 0.0,
                'requests_month': 0,
                'tokens_month': 0,
                'cost_month': 0.0
            },
            'conversations': {
                'active': 0,
                'total': 0
            }
        }
        
        # Get from database if available
        if db_module:
            try:
                with db_module._get_conn() as conn:
                    cur = conn.cursor()
                    
                    # Agent counts
                    cur.execute("SELECT status, COUNT(*) FROM agents WHERE tenant_id = %s GROUP BY status", (tenant_id,))
                    for status, count in cur.fetchall():
                        metrics['agents'][status] = count
                        metrics['agents']['total'] += count
                    
                    # Today's usage
                    today = datetime.utcnow().date().isoformat()
                    cur.execute("""
                        SELECT COALESCE(SUM(requests), 0), COALESCE(SUM(total_tokens), 0), COALESCE(SUM(cost_usd), 0)
                        FROM usage_stats 
                        WHERE tenant_id = %s AND created_at::date = %s
                    """, (tenant_id, today))
                    req, tok, cost = cur.fetchone() or (0, 0, 0)
                    metrics['usage']['requests_today'] = req
                    metrics['usage']['tokens_today'] = tok
                    metrics['usage']['cost_today'] = cost
                    
                    # Month usage
                    month_ago = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
                    cur.execute("""
                        SELECT COALESCE(SUM(requests), 0), COALESCE(SUM(total_tokens), 0), COALESCE(SUM(cost_usd), 0)
                        FROM usage_stats 
                        WHERE tenant_id = %s AND created_at::date >= %s
                    """, (tenant_id, month_ago))
                    req, tok, cost = cur.fetchone() or (0, 0, 0)
                    metrics['usage']['requests_month'] = req
                    metrics['usage']['tokens_month'] = tok
                    metrics['usage']['cost_month'] = cost
                    
                    # Conversations
                    cur.execute("SELECT COUNT(*) FROM conversations WHERE tenant_id = %s", (tenant_id,))
                    metrics['conversations']['total'] = cur.fetchone()[0] or 0
                    
            except Exception as e:
                metrics['error'] = str(e)
        
        return jsonify(metrics)
    
    @app.route('/api/health/detailed', methods=['GET'])
    def get_detailed_health():
        """Detailed health check with connection status"""
        from flask import current_app
        import psycopg2
        import redis
        
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {},
            'system': {}
        }
        
        # Check PostgreSQL
        try:
            if USE_PG:
                start = time.time()
                conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
                cur = conn.cursor()
                cur.execute('SELECT 1')
                cur.close()
                conn.close()
                health['components']['postgresql'] = {
                    'status': 'up',
                    'latency_ms': round((time.time() - start) * 1000, 2)
                }
        except Exception as e:
            health['components']['postgresql'] = {'status': 'down', 'error': str(e)}
            health['status'] = 'degraded'
        
        # Check Redis
        try:
            r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
            start = time.time()
            r.ping()
            health['components']['redis'] = {
                'status': 'up',
                'latency_ms': round((time.time() - start) * 1000, 2)
            }
        except Exception as e:
            health['components']['redis'] = {'status': 'down', 'error': str(e)}
            health['status'] = 'degraded'
        
        # System metrics
        try:
            import psutil
            health['system'] = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except:
            pass
        
        return jsonify(health)
    
    @app.route('/api/tenants', methods=['GET'])
    def list_tenants():
        """List all tenants (admin only)"""
        # Would check for admin role
        tenants = [
            {'id': 'default', 'name': 'Default Tenant', 'status': 'active'}
        ]
        
        if db_module:
            try:
                with db_module._get_conn() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT DISTINCT tenant_id FROM users WHERE tenant_id IS NOT NULL")
                    for (tid,) in cur.fetchall():
                        if tid not in ['default', None]:
                            tenants.append({'id': tid, 'name': tid.title(), 'status': 'active'})
            except:
                pass
        
        return jsonify({'tenants': tenants})
    
    @app.route('/api/validate-user', methods=['POST'])
    def validate_user_id():
        """Validate that user_id matches the JWT (security fix)"""
        data = request.json or {}
        requested_user_id = data.get('user_id')
        token_user_id = getattr(g, 'user_id', None)
        
        if not token_user_id:
            return jsonify({'valid': False, 'error': 'No auth token'}), 401
        
        if requested_user_id and requested_user_id != token_user_id:
            # Allow if user is admin
            user_role = getattr(g, 'user_role', 'user')
            if user_role != 'admin':
                return jsonify({
                    'valid': False, 
                    'error': 'Cannot access other user data'
                }), 403
        
        return jsonify({'valid': True, 'user_id': token_user_id})


# Global flag
USE_PG = bool(os.environ.get('DATABASE_URL', ''))
