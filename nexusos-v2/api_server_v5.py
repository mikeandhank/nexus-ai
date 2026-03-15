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

# Import Message Bus for Inter-Agent Communication
from message_bus import get_message_bus, AgentCoordinator, setup_message_bus_routes

app = Flask(__name__)
app.secret_key = os.environ.get('NEXUSOS_SECRET', 'nexusos-v5-enterprise')

# CORS Configuration - Security hardening
# Only allow requests from trusted origins
ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '*').split(',')

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses"""
    origin = request.headers.get('Origin', '')
    
    # In production, be more restrictive
    if os.environ.get('FLASK_ENV') == 'production':
        # Only allow specific origins in production
        if origin in ALLOWED_ORIGINS or origin == '':
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Tenant-ID'
            response.headers['Access-Control-Max-Age'] = '3600'
    else:
        # Allow all in development
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Tenant-ID'
    
    return response

@app.route('/api/options', methods=['OPTIONS'])
def cors_preflight():
    """Handle CORS preflight requests"""
    return '', 204

# Database path
db_path = os.environ.get('NEXUSOS_DB', '/opt/nexusos-data/nexusos.db')

# PostgreSQL config
DATABASE_URL = os.environ.get('DATABASE_URL', '')
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    def get_pg_conn():
        return psycopg2.connect(DATABASE_URL)
    
    # Ensure users table exists (critical for auth)
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default',
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                role TEXT DEFAULT 'user',
                subscription TEXT DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                api_keys TEXT,
                preferences TEXT,
                active_model TEXT DEFAULT 'ollama'
            )
        """)
        
        # Add tenant_id column if not exists (for existing DBs)
        try:
            cur.execute("ALTER TABLE users ADD COLUMN tenant_id TEXT DEFAULT 'default'")
        except:
            pass
        
        # Ensure conversations table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default',
                user_id TEXT NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        try:
            cur.execute("ALTER TABLE conversations ADD COLUMN tenant_id TEXT DEFAULT 'default'")
        except:
            pass
        
        # Ensure messages table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model_used TEXT,
                directive TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Ensure webhooks table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS webhooks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                url TEXT NOT NULL,
                secret TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Database table initialization error: {e}")
        pass  # Tables may already exist
    
    # Ensure usage_stats table exists
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                model TEXT,
                provider TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                requests INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Create default admin user if not exists
        import uuid
        default_email = 'admin@nexusos.local'
        cur.execute("SELECT id FROM users WHERE email = %s", (default_email,))
        if not cur.fetchone():
            import bcrypt
            default_password_hash = bcrypt.hashpw('nexusos2026'.encode(), bcrypt.gensalt()).decode()
            cur.execute("""INSERT INTO users (id, email, password_hash, name, role, subscription)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                       (str(uuid.uuid4()), default_email, default_password_hash, 'Admin', 'admin', 'pro'))
            print(f"Created default admin user: {default_email} / nexusos2026")
        
        conn.commit()
        conn.close()
    except:
        pass  # Table may already exist

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
            # Check if user exists first
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                conn.close()
                return jsonify({'error': 'Email already registered'}), 400
            # Insert with all required fields
            cur.execute("""INSERT INTO users (id, email, password_hash, name, role, subscription) 
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON CONFLICT (email) DO NOTHING""",
                       (user_id, email, password_hash, name, 'user', 'free'))
            conn.commit()
            conn.close()
        except Exception as e:
            import traceback
            return jsonify({'code': 'REGISTRATION_FAILED', 'error': 'Registration temporarily unavailable'}), 500
    else:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            # Check if user exists first
            cur.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cur.fetchone():
                conn.close()
                return jsonify({'error': 'Email already registered'}), 400
            cur.execute("INSERT INTO users (id, email, password_hash, name, role) VALUES (?, ?, ?, ?, ?)",
                       (user_id, email, password_hash, name, 'user'))
            conn.commit()
        except Exception as e:
            conn.close()
            return jsonify({'code': 'REGISTRATION_FAILED', 'error': 'Registration temporarily unavailable'}), 500
        conn.close()
    
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    
    return jsonify({'user_id': user_id, 'access_token': access, 'refresh_token': refresh, 'name': name})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user = None
    user_id = None
    user_name = ''
    user_role = 'user'
    password_hash = ''
    
    if USE_PG:
        try:
            import psycopg2.extras
            conn = get_pg_conn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT id, email, password_hash, name, role FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            conn.close()
            if row:
                user_id = row.get('id')
                user_name = row.get('name', '')
                user_role = row.get('role', 'user')
                password_hash = row.get('password_hash', '')
        except Exception as e:
            # Log but don't expose details
            print(f"Login DB error: {e}")
            pass
    else:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, email, password_hash, name, role FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()
        if row:
            user_id = row.get('id')
            user_name = row.get('name', '')
            user_role = row.get('role', 'user')
            password_hash = row.get('password_hash', '')
    
    if not user_id:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not verify_password(password, password_hash):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    try:
        access = create_access_token(user_id, user_role)
        refresh = create_refresh_token(user_id)
        
        return jsonify({
            'user_id': user_id,
            'access_token': access,
            'refresh_token': refresh,
            'name': user_name,
            'role': user_role
        })
    except Exception as e:
        print(f"Login token error: {e}")
        return jsonify({'error': 'Login failed', 'code': 'LOGIN_FAILED'}), 500

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

# ==================== USER MANAGEMENT ROUTES ====================
from user_routes import setup_user_routes
setup_user_routes(app)

# ==================== WEBHOOKS ====================
from webhooks import get_webhook_manager
from database_compat import DatabaseCompat as Database

# Initialize webhook manager with db (DatabaseCompat handles both SQLite and PostgreSQL)
_db_instance = Database()
# Ensure database tables exist (creates users, conversations, messages, etc.)
if USE_PG:
    _db_instance._init_db()
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
@require_auth
def get_usage():
    """Get current user's usage stats"""
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
    model = data.get('model', 'phi3')  # Allow model selection
    
    if not message:
        return jsonify({'error': 'message required'}), 400
    
    # user_id is now validated from JWT via @require_auth decorator
    user_id = g.user_id
    
    response = get_ollama_response(message, model=model)
    
    # Track usage - estimate tokens from message/response length
    # Rough approximation: 1 token ≈ 4 chars, so divide by 4
    input_tokens = max(1, len(message) // 4)
    output_tokens = max(1, len(response) // 4)
    total_tokens = input_tokens + output_tokens
    
    # Record usage to database
    if USE_PG:
        try:
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO usage_stats 
                    (user_id, model, provider, input_tokens, output_tokens, total_tokens, requests, cost_usd)
                    VALUES (%s, %s, 'ollama', %s, %s, %s, 1, %s)
                """, (
                    user_id, model, input_tokens, output_tokens, total_tokens,
                    round(total_tokens / 1000 * 0.001, 6)
                ))
                conn.commit()
        except:
            pass  # Fail silently on usage tracking errors
    
    return jsonify({
        'response': response,
        'conversation_id': conversation_id or str(uuid.uuid4()),
        'tokens': total_tokens,
        'cost': round(total_tokens / 1000 * 0.001, 6),
        'model': model,
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
    
    # Get usage stats if available
    usage_summary = None
    try:
        if USE_PG:
            try:
                conn = get_pg_conn()
                cur = conn.cursor()
                cur.execute("""
                    SELECT COALESCE(SUM(total_tokens), 0) as total_tokens,
                           COALESCE(SUM(cost_usd), 0) as total_cost,
                           COALESCE(SUM(requests), 0) as total_requests,
                           COUNT(*) as record_count
                    FROM usage_stats
                """)
                row = cur.fetchone()
                usage_summary = {
                    'total_tokens': row[0] or 0,
                    'total_cost_usd': round(float(row[1] or 0), 4),
                    'total_requests': row[2] or 0,
                    'records': row[3] or 0
                }
                conn.close()
            except:
                usage_summary = None
    except:
        pass
    
    response = {
        'version': '6.0.0',
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
    }
    
    if usage_summary:
        response['usage'] = usage_summary
    
    return jsonify(response)

# ==================== HEALTH CHECK ====================
@app.route('/api/health')
def health_check():
    """Comprehensive health check - no auth required"""
    import time
    import psutil
    
    # Check PostgreSQL connectivity
    db_status = False
    db_latency = None
    if USE_PG:
        try:
            start = time.time()
            conn = get_pg_conn()
            conn.close()
            db_latency = round((time.time() - start) * 1000, 2)
            db_status = True
        except Exception as e:
            db_status = False
    
    # Check Redis connectivity
    redis_status = False
    redis_latency = None
    try:
        import redis
        r = redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379/0'))
        start = time.time()
        r.ping()
        redis_latency = round((time.time() - start) * 1000, 2)
        redis_status = True
    except Exception as e:
        redis_status = False
    
    # Check Ollama
    ollama_status = False
    ollama_latency = None
    try:
        ollama_url = os.environ.get('OLLAMA_URL', 'http://nexusos-ollama:11434')
        import requests
        start = time.time()
        resp = requests.get(f"{ollama_url}/api/tags", timeout=2)
        ollama_latency = round((time.time() - start) * 1000, 2)
        ollama_status = resp.status_code == 200
    except:
        ollama_status = False
    
    # System metrics
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        system_info = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_mb': round(memory.available / 1024 / 1024, 1),
            'disk_percent': disk.percent,
            'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 1)
        }
    except:
        system_info = None
    
    # Overall health - only fail if core infrastructure (DB/Redis) is down
    # Ollama is optional since cloud LLM providers can substitute
    core_healthy = db_status and redis_status
    all_healthy = core_healthy and ollama_status
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'dependencies': {
            'postgresql': {
                'status': 'up' if db_status else 'down',
                'latency_ms': db_latency
            },
            'redis': {
                'status': 'up' if redis_status else 'down',
                'latency_ms': redis_latency
            },
            'ollama': {
                'status': 'up' if ollama_status else 'down',
                'latency_ms': ollama_latency
            }
        },
        'system': system_info
    }), 200 if core_healthy else 503

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

# Initialize Message Bus (Inter-Agent Communication)
REDIS_URL = os.environ.get('REDIS_URL', '')
message_bus = get_message_bus(REDIS_URL)
coordinator = AgentCoordinator(message_bus)
setup_message_bus_routes(app, message_bus, coordinator)
if REDIS_URL:
    print("[NexusOS] Message Bus initialized with Redis")
else:
    print("[NexusOS] Message Bus initialized (in-memory fallback)")

# Initialize Structured Logging & Kill Switches
from structured_logging import (
    get_logger, get_kill_switches, get_rate_limiter,
    setup_logging_routes, EventType
)
nexus_logger = get_logger()
kill_switches = get_kill_switches()
rate_limiter = get_rate_limiter()

# Add logging routes
setup_logging_routes(app, nexus_logger, kill_switches, rate_limiter)
print("[NexusOS] Structured Logging & Kill Switches initialized")

# Initialize Semantic Memory (Qdrant)
from semantic_memory import get_semantic_memory, MemoryType
from metrics_api import setup_metrics_routes

semantic_memory = get_semantic_memory()
setup_metrics_routes(app, _db_instance)

# Setup backup routes
try:
    from backup_api import setup_backup_routes
    setup_backup_routes(app)
except Exception as e:
    print(f"[NexusOS] Backup routes not available: {e}")

# Setup plugin system
try:
    from plugin_system import setup_plugin_routes
    setup_plugin_routes(app)
except Exception as e:
    print(f"[NexusOS] Plugin system not available: {e}")

# Multi-Tenant Isolation
@app.route('/api/tenants', methods=['GET'])
@require_auth
def get_tenants():
    """List tenants (admin only)"""
    if g.user_role != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT tenant_id FROM users WHERE tenant_id IS NOT NULL")
        tenants = [row[0] for row in cur.fetchall()]
        conn.close()
        return jsonify({'tenants': tenants})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tenants/<tenant_id>/users', methods=['GET'])
@require_auth
def list_tenant_users(tenant_id):
    """List users in a tenant"""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, role FROM users WHERE tenant_id = %s", (tenant_id,))
        users = []
        for row in cur.fetchall():
            users.append({'id': row[0], 'email': row[1], 'name': row[2], 'role': row[3]})
        conn.close()
        return jsonify({'users': users})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

print("[NexusOS] Multi-tenant routes enabled")

# Setup metrics and multi-tenant routes
db_module = None  # Will be set after Database is defined
setup_metrics_routes(app, db_module)
print("[NexusOS] Semantic Memory initialized")

# ==================== SEMANTIC MEMORY ROUTES ====================
@app.route('/api/memory', methods=['POST'])
@require_auth
def add_memory():
    """Add a memory to semantic store"""
    data = request.json or {}
    content = data.get('content')
    memory_type = data.get('type', 'conversation')
    
    if not content:
        return jsonify({'error': 'content required'}), 400
    
    try:
        mem_type = MemoryType(memory_type)
    except:
        mem_type = MemoryType.CONVERSATION
    
    memory_id = semantic_memory.add(
        content=content,
        memory_type=mem_type,
        user_id=g.user_id,
        agent_id=data.get('agent_id'),
        metadata=data.get('metadata')
    )
    
    return jsonify({'id': memory_id, 'status': 'added'})

@app.route('/api/memory/search', methods=['GET'])
@require_auth
def search_memory():
    """Semantic search across memories"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 5, type=int)
    
    if not query:
        return jsonify({'error': 'query required'}), 400
    
    results = semantic_memory.search(query, user_id=g.user_id, limit=limit)
    
    return jsonify({
        'results': [
            {
                'id': r.get('id'),
                'content': r.get('content'),
                'type': r.get('memory_type'),
                'score': r.get('score', 0),
                'created_at': r.get('created_at')
            }
            for r in results
        ]
    })

@app.route('/api/memory', methods=['GET'])
@require_auth
def list_memory():
    """List user's memories"""
    limit = request.args.get('limit', 50, type=int)
    memories = semantic_memory.get_by_user(g.user_id, limit=limit)
    
    return jsonify({
        'memories': [
            {
                'id': m.get('id'),
                'content': m.get('content')[:200],
                'type': m.get('memory_type'),
                'created_at': m.get('created_at')
            }
            for m in memories
        ]
    })

# ==================== ERROR HANDLING ====================
@app.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad request', 'code': 'BAD_REQUEST'}), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

@app.errorhandler(403)
def forbidden(e):
    return jsonify({'error': 'Access forbidden', 'code': 'FORBIDDEN'}), 403

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found', 'code': 'NOT_FOUND'}), 404

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({'error': 'Rate limit exceeded', 'code': 'RATE_LIMITED'}), 429

@app.errorhandler(500)
def internal_error(e):
    # Don't leak internal errors
    return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

# ==================== REQUEST LOGGING ====================
@app.before_request
def log_request():
    """Log all API requests"""
    if request.path.startswith('/api/'):
        # Rate limit check
        key = f"{g.get('user_id', 'anonymous')}:{request.endpoint}"
        if not rate_limiter.check(key):
            return jsonify({'error': 'Rate limit exceeded', 'code': 'RATE_LIMITED'}), 429
        
        # Log the request
        nexus_logger.info(
            event_type=EventType.API_REQUEST.value,
            message=f"{request.method} {request.path}",
            user_id=g.get('user_id'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
