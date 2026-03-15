import os
import json
import time
import uuid
import hashlib
import sqlite3
import requests
from flask import Flask, request, jsonify, g, session, send_from_directory
from usage_analytics import usage_bp
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('NEXUSOS_SECRET', 'nexusos-v5-enterprise')

# Database path
db_path = os.environ.get('NEXUSOS_DB', '/opt/nexusos-data/nexusos.db')

# PostgreSQL config
DATABASE_URL = os.environ.get('DATABASE_URL', '')
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    def get_pg_conn():
        return psycopg2.connect(DATABASE_URL)

# ==================== JWT AUTH ====================
import bcrypt
import jwt as pyjwt

JWT_SECRET = os.environ.get('NEXUSOS_SECRET', 'nexusos-v5-enterprise')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE = 3600

def hash_password(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw, h):
    return bcrypt.checkpw(pw.encode(), h.encode())

def create_access_token(user_id, role='user'):
    payload = {
        'user_id': user_id,
        'role': role,
        'type': 'access',
        'exp': datetime.utcnow() + datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRE),
        'iat': datetime.utcnow()
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id):
    payload = {
        'user_id': user_id,
        'type': 'refresh',
        'exp': datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.utcnow()
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token):
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Auth required'}), 401
        payload = verify_token(auth.replace('Bearer ', ''))
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        g.user_id = payload['user_id']
        g.user_role = payload.get('role', 'user')
        return f(*args, **kwargs)
    return decorated

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    
    if USE_PG:
        try:
            conn = get_pg_conn()
            cur = conn.cursor()
            cur.execute("INSERT INTO users (id, email, password_hash, name, role) VALUES (%s, %s, %s, %s, %s)",
                       (user_id, email, password_hash, name, 'user'))
            conn.commit()
            conn.close()
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)",
                       (user_id, email, password_hash, name))
            conn.commit()
        except Exception as e:
            conn.close()
            return jsonify({'error': str(e)}), 500
        conn.close()
    
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    
    return jsonify({'user_id': user_id, 'access_token': access, 'refresh_token': refresh, 'name': name})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    
    user = None
    if USE_PG:
        try:
            conn = get_pg_conn()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            conn.close()
        except:
            pass
    else:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()
    
    if not user or not verify_password(password, user.get('password_hash', '')):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    access = create_access_token(user['id'], user.get('role', 'user'))
    refresh = create_refresh_token(user['id'])
    
    return jsonify({
        'user_id': user['id'],
        'access_token': access,
        'refresh_token': refresh,
        'name': user.get('name', ''),
        'role': user.get('role', 'user')
    })

@app.route('/api/auth/refresh', methods=['POST'])
def refresh():
    data = request.json or {}
    refresh = data.get('refresh_token')
    if not refresh:
        return jsonify({'error': 'Refresh token required'}), 400
    
    payload = verify_token(refresh)
    if not payload or payload.get('type') != 'refresh':
        return jsonify({'error': 'Invalid refresh token'}), 401
    
    role = 'user'
    if USE_PG:
        try:
            conn = get_pg_conn()
            cur = conn.cursor()
            cur.execute("SELECT role FROM users WHERE id = %s", (payload['user_id'],))
            row = cur.fetchone()
            if row:
                role = row['role']
            conn.close()
        except:
            pass
    
    return jsonify({'access_token': create_access_token(payload['user_id'], role)})

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    return jsonify({'status': 'logged_out'})

# ==================== AGENT ROUTES ====================
from agent_routes import setup_agent_routes
setup_agent_routes(app)

# ==================== WEBHOOKS ====================
from webhooks import get_webhook_manager
from database import Database

# Initialize webhook manager with db
_db_instance = Database() if not USE_PG else None
_webhook_mgr = get_webhook_manager(_db_instance)

@app.route('/api/webhooks', methods=['POST'])
@require_auth
def create_webhook():
    """Register a new webhook"""
    data = request.json or {}
    event_type = data.get('event_type')
    url = data.get('url')
    
    if not event_type or not url:
        return jsonify({'error': 'event_type and url required'}), 400
    
    # Validate URL
    if not url.startswith('http://') and not url.startswith('https://'):
        return jsonify({'error': 'url must start with http:// or https://'}), 400
    
    webhook = _webhook_mgr.register_webhook(event_type, url, user_id=g.user_id)
    
    # Dispatch event for webhook creation
    _webhook_mgr.dispatch('webhook.created', {'webhook_id': webhook['id'], 'event_type': event_type})
    
    return jsonify({
        'id': webhook['id'],
        'event_type': event_type,
        'url': url,
        'enabled': True
    })

@app.route('/api/webhooks', methods=['GET'])
@require_auth
def list_webhooks():
    """List user's webhooks"""
    webhooks = _webhook_mgr.list_webhooks(user_id=g.user_id)
    return jsonify({'webhooks': webhooks})

@app.route('/api/webhooks/<webhook_id>', methods=['DELETE'])
@require_auth
def delete_webhook(webhook_id):
    """Delete a webhook"""
    success = _webhook_mgr.unregister_webhook(webhook_id, user_id=g.user_id)
    if success:
        return jsonify({'status': 'deleted'})
    return jsonify({'error': 'Not found'}), 404

# Available webhook events
WEBHOOK_EVENTS = [
    'agent.created', 'agent.started', 'agent.stopped', 'agent.paused', 'agent.resumed',
    'chat.message', 'chat.complete',
    'user.registered', 'user.login',
    'webhook.created', 'webhook.deleted',
    'usage.exceeded'
]

@app.route('/api/webhooks/events', methods=['GET'])
def list_webhook_events():
    """List available webhook events"""
    return jsonify({'events': WEBHOOK_EVENTS})

# ==================== USAGE ANALYTICS ====================

@app.route('/api/usage', methods=['GET'])
def get_usage():
    """Get current user's usage stats"""
    if not hasattr(g, 'user_id') or not g.user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    days = request.args.get('days', 30, type=int)
    
    try:
        if USE_PG:
            with get_pg_conn() as conn:
                with conn.cursor() as cur:
                    # Get summary
                    cur.execute("""
                        SELECT COALESCE(SUM(total_tokens), 0) as total_tokens,
                               COALESCE(SUM(requests), 0) as total_requests,
                               COALESCE(SUM(cost_usd), 0) as total_cost
                        FROM usage_stats 
                        WHERE user_id = %s AND created_at >= datetime('now', '-%s days')
                    """, (g.user_id, days))
                    row = cur.fetchone()
                    
                    # Get breakdown by model
                    cur.execute("""
                        SELECT model, provider,
                               SUM(total_tokens) as tokens,
                               SUM(requests) as requests,
                               SUM(cost_usd) as cost
                        FROM usage_stats 
                        WHERE user_id = %s AND created_at >= datetime('now', '-%s days')
                        GROUP BY model, provider
                        ORDER BY tokens DESC
                    """, (g.user_id, days))
                    breakdown = []
                    for r in cur.fetchall():
                        breakdown.append({
                            'model': r[0],
                            'provider': r[1],
                            'tokens': r[2],
                            'requests': r[3],
                            'cost': float(r[4])
                        })
                    
                    return jsonify({
                        'period_days': days,
                        'summary': {
                            'total_tokens': row[0] or 0,
                            'total_requests': row[1] or 0,
                            'total_cost': float(row[2]) if row[2] else 0
                        },
                        'by_model': breakdown
                    })
        else:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Get summary
            c.execute("""
                SELECT COALESCE(SUM(total_tokens), 0) as total_tokens,
                       COALESCE(SUM(requests), 0) as total_requests,
                       COALESCE(SUM(cost_usd), 0) as total_cost
                FROM usage_stats 
                WHERE user_id = ? AND created_at >= datetime('now', '-' || ? || ' days')
            """, (g.user_id, days))
            row = c.fetchone()
            
            # Get breakdown by model
            c.execute("""
                SELECT model, provider,
                       SUM(total_tokens) as tokens,
                       SUM(requests) as requests,
                       SUM(cost_usd) as cost
                FROM usage_stats 
                WHERE user_id = ? AND created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY model, provider
                ORDER BY tokens DESC
            """, (g.user_id, days))
            
            breakdown = []
            for r in c.fetchall():
                breakdown.append({
                    'model': r['model'],
                    'provider': r['provider'],
                    'tokens': r['tokens'],
                    'requests': r['requests'],
                    'cost': r['cost']
                })
            
            conn.close()
            
            return jsonify({
                'period_days': days,
                'summary': {
                    'total_tokens': row['total_tokens'],
                    'total_requests': row['total_requests'],
                    'total_cost': row['total_cost']
                },
                'by_model': breakdown
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== LLM ====================
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://nexusos-ollama:11434')

def get_ollama_response(prompt, model='phi3'):
    try:
        r = requests.post(f'{OLLAMA_URL}/api/generate', json={
            'model': model,
            'prompt': prompt,
            'stream': False
        }, timeout=120)
        return r.json().get('response', '')
    except Exception as e:
        return f'Error: {e}'

@app.route('/api/chat', methods=['POST'])
@require_auth
def chat():
    """Chat endpoint - requires valid JWT auth"""
    data = request.json or {}
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')
    
    if not message:
        return jsonify({'error': 'message required'}), 400
    
    # user_id is now validated from JWT via @require_auth decorator
    user_id = g.user_id
    
    response = get_ollama_response(message)
    
    return jsonify({
        'response': response,
        'conversation_id': conversation_id or str(uuid.uuid4()),
        'tokens': len(response.split()),
        'cost': 0,
        'user_id': user_id  # Echo back for confirmation
    })

# ==================== STATUS ====================
@app.route('/api/status')
def status():
    # Check PostgreSQL connectivity
    db_status = False
    if USE_PG:
        try:
            conn = get_pg_conn()
            conn.close()
            db_status = True
        except:
            db_status = False
    
    # Check Redis connectivity
    redis_status = False
    try:
        import redis
        r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        r.ping()
        redis_status = True
    except:
        redis_status = False
    
    return jsonify({
        'version': '5.0.0',
        'running': True,
        'enterprise': True,
        'components': {
            'database': db_status,
            'postgresql': USE_PG,
            'redis': redis_status,
            'llm_manager': True
        },
        'infrastructure': {
            'postgres': 'connected' if db_status else 'disconnected',
            'redis': 'connected' if redis_status else 'disconnected'
        },
        'tiers': {
            'free': {'providers': ['ollama']},
            'basic': {'providers': ['ollama', 'openrouter']},
            'pro': {'providers': ['ollama', 'openrouter', 'anthropic', 'openai']}
        }
    })

# ==================== MCP ====================
@app.route('/mcp/tools')
def mcp_tools():
    return jsonify({'tools': [
        {'name': 'file_read', 'description': 'Read a file'},
        {'name': 'file_write', 'description': 'Write to a file'},
        {'name': 'file_list', 'description': 'List directory'},
        {'name': 'process_run', 'description': 'Run a process'},
        {'name': 'http_get', 'description': 'HTTP GET request'},
        {'name': 'http_post', 'description': 'HTTP POST request'},
        {'name': 'system_info', 'description': 'Get system info'},
        {'name': 'search_files', 'description': 'Search files'}
    ]})

@app.route('/mcp/resources')
def mcp_resources():
    return jsonify({'resources': [
        {'uri': 'nexus://user/me', 'name': 'Current user'},
        {'uri': 'nexus://memories', 'name': 'User memories'}
    ]})

@app.route('/mcp/initialize')
def mcp_init():
    return jsonify({'name': 'NexusOS MCP Server', 'version': '1.0.0'})

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    return jsonify({'result': 'MCP endpoint ready'})

# ==================== RBAC ====================
ROLES = {
    'admin': {'permissions': ['read', 'write', 'delete', 'admin', 'manage_users']},
    'developer': {'permissions': ['read', 'write', 'manage_agents']},
    'user': {'permissions': ['read', 'write']},
    'viewer': {'permissions': ['read']}
}

@app.route('/api/roles')
def list_roles():
    return jsonify({'roles': ROLES})

@app.route('/api/permissions')
def list_perms():
    return jsonify({r: info['permissions'] for r, info in ROLES.items()})

# ==================== WEB UI ====================
from flask import send_from_directory
@app.route('/')
def index():
    return send_from_directory('/app/templates', 'index.html')

@app.route('/ui')
def web_ui():
    return send_from_directory('/app/templates', 'index.html')

# Register blueprints
app.register_blueprint(usage_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
