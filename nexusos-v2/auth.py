"""
JWT Authentication for NexusOS
Real authentication with refresh tokens and API key scoping
"""
import os
import jwt
import bcrypt
import secrets
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g

# Configuration
JWT_SECRET = os.environ.get('NEXUSOS_SECRET', 'nexusos-v5-enterprise')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE = 3600  # 1 hour
REFRESH_TOKEN_EXPIRE = 604800  # 7 days

# Token blacklist (in production, use Redis)
token_blacklist = set()

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(user_id, role='user'):
    """Create JWT access token"""
    payload = {
        'user_id': user_id,
        'role': role,
        'type': 'access',
        'exp': datetime.utcnow() + timedelta(seconds=ACCESS_TOKEN_EXPIRE),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id):
    """Create JWT refresh token"""
    payload = {
        'user_id': user_id,
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(seconds=REFRESH_TOKEN_EXPIRE),
        'iat': datetime.utcnow(),
        'nonce': secrets.token_hex(8)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token, token_type='access'):
    """Verify JWT token and return payload"""
    try:
        # Check blacklist
        if token in token_blacklist:
            return None
        
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Verify token type
        if payload.get('type') != token_type:
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def refresh_access_token(refresh_token):
    """Get new access token from refresh token"""
    payload = verify_token(refresh_token, 'refresh')
    if not payload:
        return None
    
    # Get user role from database
    user_id = payload['user_id']
    role = get_user_role(user_id)
    
    return create_access_token(user_id, role)

def get_user_role(user_id):
    """Get user's role from database"""
    from database_v2 import get_db
    db = get_db()
    user = db.execute_one(
        "SELECT role FROM users WHERE id = %s",
        (user_id,)
    )
    return user['role'] if user else 'user'

def revoke_token(token):
    """Revoke a token (add to blacklist)"""
    token_blacklist.add(token)
    # Clean old tokens periodically
    if len(token_blacklist) > 1000:
        token_blacklist.clear()

def require_auth(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.replace('Bearer ', '')
        payload = verify_token(token, 'access')
        
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        g.user_id = payload['user_id']
        g.user_role = payload.get('role', 'user')
        
        return f(*args, **kwargs)
    return decorated

def require_role(*allowed_roles):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'user_role'):
                return jsonify({'error': 'Authentication required'}), 401
            
            if g.user_role not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

# API Key support
def create_api_key(user_id, name, scopes=None):
    """Create an API key for a user"""
    from database_v2 import get_db
    import json
    
    key = f"nxos_{secrets.token_hex(16)}"
    key_hash = hash_password(key)
    
    scopes = scopes or ['read']
    
    db = get_db()
    db.execute_write(
        """INSERT INTO api_keys (user_id, name, key_hash, scopes, created_at)
           VALUES (%s, %s, %s, %s, NOW())""",
        (user_id, name, key_hash, json.dumps(scopes))
    )
    
    return key

def verify_api_key(key):
    """Verify an API key"""
    from database_v2 import get_db
    import json
    
    if not key.startswith('nxos_'):
        return None
    
    db = get_db()
    keys = db.execute("SELECT * FROM api_keys WHERE name = %s", (key,))
    
    for row in keys:
        if row['key_hash'] and hash_password(key) == row['key_hash']:
            return {'user_id': row['user_id'], 'scopes': json.loads(row['scopes'])}
    
    return None
