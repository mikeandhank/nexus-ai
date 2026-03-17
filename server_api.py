"""
Nexus Server API - Cloud Backend for NexusOS Client
Handles: Authentication, LLM Routing, Billing, User Management
"""

import os
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g
import logging

# Import our modules
from database import get_db
from llm_integration import get_llm_manager, LLMResponse
from billing import get_credit_manager, get_usage_tracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('NEXUSOS_SECRET_KEY', secrets.token_hex(32))

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_db_connection():
    """Get database connection."""
    db = get_db()
    return db.db

def row_to_dict(cursor, row):
    """Convert database row to dict."""
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))

# ============================================================================
# API KEY AUTHENTICATION
# ============================================================================

def require_nexus_key(f):
    """Decorator to require valid Nexus API key."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-Nexus-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'Missing X-Nexus-Key header'}), 401
        
        # Validate API key
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Hash the key for lookup
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        cursor.execute(
            "SELECT user_id, is_active FROM api_keys WHERE key_hash = ? AND is_active = true",
            (key_hash,)
        )
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'error': 'Invalid API key'}), 401
        
        user_id = row[0]
        
        # Get user info
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            return jsonify({'error': 'User not found'}), 401
        
        user = row_to_dict(cursor, user_row)
        
        # Update last used
        cursor.execute(
            "UPDATE api_keys SET last_used = ? WHERE key_hash = ?",
            (datetime.now().isoformat(), key_hash)
        )
        conn.commit()
        
        g.user = user
        g.user_id = user_id
        
        return f(*args, **kwargs)
    
    return decorated

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', email.split('@')[0])
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if email exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create user
    user_id = str(uuid.uuid4())
    password_hash = hashlib.sha256(password.encode()).hexdigest()  # In production, use bcrypt
    
    cursor.execute("""
        INSERT INTO users (id, email, password_hash, name, credits, subscription_tier)
        VALUES (?, ?, ?, ?, ?, 'free')
    """, (user_id, email, password_hash, name, 1000))  # 1000 free credits
    
    # Generate Nexus API key
    api_key = f"sk-nexus-{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    cursor.execute("""
        INSERT INTO api_keys (id, user_id, key_hash, name)
        VALUES (?, ?, ?, ?)
    """, (str(uuid.uuid4()), user_id, key_hash, 'Default Key'))
    
    conn.commit()
    
    return jsonify({
        'user_id': user_id,
        'email': email,
        'api_key': api_key,
        'credits': 1000,
        'message': 'Account created successfully'
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login and get API key."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    cursor.execute("""
        SELECT id, email, name, credits, subscription_tier 
        FROM users WHERE email = ? AND password_hash = ?
    """, (email, password_hash))
    
    row = cursor.fetchone()
    
    if not row:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user = {
        'id': row[0],
        'email': row[1],
        'name': row[2],
        'credits': row[3],
        'subscription_tier': row[4]
    }
    
    # Get or create API key
    cursor.execute("SELECT key_prefix || key_hash FROM api_keys WHERE user_id = ? AND is_active = true LIMIT 1", (user['id'],))
    key_row = cursor.fetchone()
    
    if key_row:
        api_key = key_row[0]
    else:
        # Create new key
        api_key = f"sk-nexus-{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO api_keys (id, user_id, key_hash, name)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), user['id'], key_hash, 'Default Key'))
        conn.commit()
    
    return jsonify({
        'user': user,
        'api_key': api_key
    })


# ============================================================================
# CONFIG ENDPOINTS
# ============================================================================

@app.route('/api/config', methods=['GET'])
@require_nexus_key
def get_config():
    """Get user's LLM configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT provider, model, fallback_provider, fallback_model, is_default
        FROM user_llm_config WHERE user_id = ? AND is_default = true
    """, (g.user_id,))
    
    row = cursor.fetchone()
    
    if row:
        config = {
            'provider': row[0],
            'model': row[1],
            'fallback_provider': row[2],
            'fallback_model': row[3],
            'is_default': row[4]
        }
    else:
        # Default config
        config = {
            'provider': 'openai',
            'model': 'gpt-4o-mini',
            'fallback_provider': None,
            'fallback_model': None,
            'is_default': True
        }
    
    return jsonify(config)


@app.route('/api/config', methods=['PUT'])
@require_nexus_key
def update_config():
    """Update user's LLM configuration."""
    data = request.get_json() or {}
    
    provider = data.get('provider', 'openai')
    model = data.get('model', 'gpt-4o-mini')
    fallback_provider = data.get('fallback_provider')
    fallback_model = data.get('fallback_model')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Upsert config
    cursor.execute("""
        INSERT INTO user_llm_config (id, user_id, provider, model, fallback_provider, fallback_model, is_default)
        VALUES (?, ?, ?, ?, ?, ?, true)
        ON CONFLICT(user_id) DO UPDATE SET
            provider = excluded.provider,
            model = excluded.model,
            fallback_provider = excluded.fallback_provider,
            fallback_model = excluded.fallback_model,
            updated_at = CURRENT_TIMESTAMP
    """, (str(uuid.uuid4()), g.user_id, provider, model, fallback_provider, fallback_model))
    
    conn.commit()
    
    return jsonify({'message': 'Configuration updated'})


@app.route('/api/models', methods=['GET'])
@require_nexus_key
def get_models():
    """Get available models for user."""
    # Return available models
    models = {
        'openai': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
        'anthropic': ['claude-sonnet-4-20250514', 'claude-opus-4-20250514'],
        'google': ['gemini-2.0-flash', 'gemini-pro'],
        'ollama': ['phi3', 'llama3', 'mistral']
    }
    
    user_tier = g.user.get('subscription_tier', 'free')
    
    # Free tier limited models
    if user_tier == 'free':
        return jsonify({
            'tier': 'free',
            'models': {
                'openai': ['gpt-4o-mini'],
                'ollama': ['phi3', 'llama3', 'mistral']
            }
        })
    
    return jsonify({
        'tier': user_tier,
        'models': models
    })


# ============================================================================
# CHAT ENDPOINT (MAIN)
# ============================================================================

@app.route('/api/chat', methods=['POST'])
@require_nexus_key
def chat():
    """\n    Main chat endpoint - routes to LLM and tracks usage.\n    \n    Request:\n        {\n            "message": "Hello",  // or messages: [...]\n            "model": "optional override",\n            "stream": false\n        }\n    \n    Response:\n        {\n            "content": "Response text",\n            "model": "gpt-4o-mini",\n            "provider": "openai",\n            "usage": { "input": 10, "output": 50, "cost": 0.0001 }\n        }\n    """
    data = request.get_json() or {}
    
    message = data.get('message', '')
    messages = data.get('messages', [])
    model_override = data.get('model')
    stream = data.get('stream', False)
    
    if message:
        messages = [{'role': 'user', 'content': message}]
    
    if not messages:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get user config
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT provider, model, fallback_provider, fallback_model
        FROM user_llm_config WHERE user_id = ? AND is_default = true
    """, (g.user_id,))
    
    row = cursor.fetchone()
    
    if row:
        provider_name = model_override or row[0]
        model = model_override or row[1]
        fallback_provider = row[2]
        fallback_model = row[3]
    else:
        provider_name = model_override or 'openai'
        model = model_override or 'gpt-4o-mini'
        fallback_provider = None
        fallback_model = None
    
    # Get credits
    cursor.execute("SELECT credits FROM users WHERE id = ?", (g.user_id,))
    credits_row = cursor.fetchone()
    user_credits = float(credits_row[0]) if credits_row else 0
    
    if user_credits < 0.001:  # Minimum threshold
        return jsonify({'error': 'Insufficient credits'}), 402
    
    # Get LLM manager and make request
    llm_manager = get_llm_manager()
    provider, p_name, estimated_cost = llm_manager.get_provider(g.user_id, model)
    
    if not provider:
        # Try fallback
        if fallback_provider:
            provider, p_name, estimated_cost = llm_manager.get_provider(g.user_id, fallback_model)
            model = fallback_model
        else:
            return jsonify({'error': f'Model {model} not available on your tier'}), 403
    
    # Make the request
    response = provider.chat(messages, model)
    
    if not response.success:
        # Try fallback
        if fallback_provider:
            provider, p_name, _ = llm_manager.get_provider(g.user_id, fallback_model)
            response = provider.chat(messages, fallback_model)
            model = fallback_model
        
        if not response.success:
            return jsonify({'error': response.error}), 500
    
    # Record usage and deduct credits
    try:
        usage_tracker = get_usage_tracker()
        usage_record = usage_tracker.record_usage(
            user_id=g.user_id,
            provider=p_name,
            model=model,
            input_tokens=response.tokens_used // 2,
            output_tokens=response.tokens_used // 2,
            mode='we_bill',
            request_id=str(uuid.uuid4())
        )
    except Exception as e:
        logger.error(f"Usage tracking error: {e}")
    
    return jsonify({
        'content': response.content,
        'model': model,
        'provider': p_name,
        'usage': {
            'input': response.tokens_used // 2,
            'output': response.tokens_used // 2,
            'total': response.tokens_used,
            'cost': response.cost
        }
    })


# ============================================================================
# BILLING ENDPOINTS
# ============================================================================

@app.route('/api/credits', methods=['GET'])
@require_nexus_key
def get_credits():
    """Get user's credit balance."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT credits FROM users WHERE id = ?", (g.user_id,))
    row = cursor.fetchone()
    
    credits = float(row[0]) if row else 0
    
    return jsonify({
        'credits': credits,
        'user_id': g.user_id
    })


@app.route('/api/credits/purchase', methods=['POST'])
@require_nexus_key
def purchase_credits():
    """Purchase credits (Stripe integration placeholder)."""
    data = request.get_json() or {}
    amount = data.get('amount', 10.0)  # dollars
    
    if amount < 5:
        return jsonify({'error': 'Minimum purchase is '}), 400
    
    # Calculate credits (OpenRouter-style: we take 5.5%)
    fee = max(amount * 0.055, 0.80)
    credits = (amount - fee) * 1.058  # Rough calculation
    
    # In production: Create Stripe payment intent
    # For now: Just add credits
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET credits = credits + ? WHERE id = ?",
        (credits, g.user_id)
    )
    
    # Record purchase
    cursor.execute("""
        INSERT INTO credit_purchases (id, user_id, amount_paid, credits_added, our_fee, provider, status)
        VALUES (?, ?, ?, ?, ?, 'stripe', 'completed')
    """, (str(uuid.uuid4()), g.user_id, amount, credits, fee))
    
    conn.commit()
    
    return jsonify({
        'credits_added': credits,
        'amount_paid': amount,
        'our_fee': fee,
        'new_balance': credits
    })


@app.route('/api/usage', methods=['GET'])
@require_nexus_key
def get_usage():
    """Get user's usage history."""
    days = request.args.get('days', 30, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT provider, model, input_tokens, output_tokens, provider_cost, our_fee, created_at
        FROM llm_usage 
        WHERE user_id = ? AND created_at > NOW() - INTERVAL '1 day' * ?
        ORDER BY created_at DESC
        LIMIT 100
    """, (g.user_id, days))
    
    rows = cursor.fetchall()
    
    usage = []
    for row in rows:
        usage.append({
            'provider': row[0],
            'model': row[1],
            'input_tokens': row[2],
            'output_tokens': row[3],
            'cost': row[4],
            'fee': row[5],
            'created_at': row[6].isoformat() if row[6] else None
        })
    
    return jsonify({'usage': usage})


@app.route('/api/usage/summary', methods=['GET'])
@require_nexus_key
def get_usage_summary():
    """Get usage summary."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_requests,
            COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
            COALESCE(SUM(provider_cost), 0) as total_cost,
            COALESCE(SUM(our_fee), 0) as total_fee
        FROM llm_usage 
        WHERE user_id = ? AND created_at > NOW() - INTERVAL '30 days'
    """, (g.user_id,))
    
    row = cursor.fetchone()
    
    return jsonify({
        'period_days': 30,
        'total_requests': row[0],
        'total_tokens': row[1],
        'total_cost': row[2],
        'total_our_fee': row[3]
    })


# ============================================================================
# HEALTH
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'nexus-server'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
