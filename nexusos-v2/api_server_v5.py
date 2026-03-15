import os
import json
import time
import uuid
import hashlib
import sqlite3
import requests
from flask import Flask, request, jsonify, g, session
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
def chat():
    data = request.json or {}
    user_id = data.get('user_id') or request.headers.get('Authorization', '').replace('Bearer ', '')
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')
    
    if not user_id or not message:
        return jsonify({'error': 'user_id and message required'}), 400
    
    response = get_ollama_response(message)
    
    return jsonify({
        'response': response,
        'conversation_id': conversation_id or str(uuid.uuid4()),
        'tokens': len(response.split()),
        'cost': 0
    })

# ==================== STATUS ====================
@app.route('/api/status')
def status():
    return jsonify({
        'version': '5.0.0',
        'running': True,
        'enterprise': True,
        'components': {
            'database': True,
            'llm_manager': True
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
