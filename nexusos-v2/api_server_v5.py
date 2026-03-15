"""
NexusOS v5 - API Server with LLM Integration

Enterprise Features:
- Multi-provider LLM support (Ollama, OpenRouter, Anthropic)
- BYOK model with encrypted API keys
- Subscription tier enforcement
- Usage tracking
- Audit logging
"""

import os
import sys
import json
import uuid
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, session, g
import logging

from database import init_db, get_db
from llm_integration import get_llm_manager, Provider, Tier, TIER_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('NEXUSOS_SECRET', 'nexusos-v5-enterprise-secret')

# Initialize components
DB_PATH = os.environ.get("NEXUSOS_DB", "/opt/nexusos-data/nexusos.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

db = init_db(DB_PATH)
llm_manager = get_llm_manager(db)


# ==================== MIDDLEWARE ====================

@app.before_request
def before_request():
    """Extract user from session or auth header."""
    g.user_id = None
    
    # Check session
    if 'user_id' in session:
        g.user_id = session['user_id']
        return
    
    # Check Authorization header (Bearer token)
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth[7:]
        # Simple token validation (in production, use JWT)
        user = db.get_user(token)
        if user:
            g.user_id = user['id']
            return
    
    # Check JSON body for user_id (for API clients)
    if request.is_json:
        data = request.json or {}
        if 'user_id' in data:
            g.user_id = data['user_id']


def require_auth(f):
    """Require authentication decorator."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.user_id:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


# ==================== AUTH ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user."""
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user_id = hashlib.sha256(f"{email}{datetime.now()}".encode()).hexdigest()[:32]
    
    try:
        user = db.create_user(user_id, email, password, name)
        session['user_id'] = user_id
        return jsonify({
            'user_id': user_id, 
            'email': email, 
            'name': name,
            'tier': user.get('subscription', 'free')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login with email/password or token."""
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    token = data.get('token')
    
    if token:
        # Token-based login
        user = db.get_user(token)
        if not user:
            return jsonify({'error': 'Invalid token'}), 401
    elif email and password:
        # Password-based login
        user = db.get_user_by_email(email)
        if not user or not db.verify_password(user['id'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
    else:
        return jsonify({'error': 'Email/password or token required'}), 400
    
    user_id = user['id']
    db.update_user(user_id, last_login=datetime.now().isoformat())
    session['user_id'] = user_id
    
    return jsonify({
        'user_id': user_id,
        'name': user.get('name'),
        'email': user.get('email'),
        'tier': user.get('subscription', 'free'),
        'token': user_id  # Return token for API use
    })


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'status': 'ok'})


# ==================== USER ====================

@app.route('/api/user', methods=['GET'])
@require_auth
def get_user():
    """Get current user."""
    user = db.get_user(g.user_id)
    if user:
        user.pop('password_hash', None)
        # Add available models
        user['available_models'] = llm_manager.get_available_models(g.user_id)
    return jsonify(user or {})


@app.route('/api/user', methods=['PUT'])
@require_auth
def update_user():
    """Update user settings."""
    data = request.json or {}
    updated = db.update_user(g.user_id, **data)
    if updated:
        updated.pop('password_hash', None)
    return jsonify(updated or {'error': 'Update failed'})


# ==================== API KEYS (BYOK) ====================

@app.route('/api/keys', methods=['GET'])
@require_auth
def list_keys():
    """List user's API keys (encrypted)."""
    user = db.get_user(g.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    api_keys = user.get('api_keys', '{}')
    try:
        if isinstance(api_keys, str):
            api_keys = json.loads(api_keys)
    except:
        api_keys = {}
    
    # Return only provider names, not actual keys
    return jsonify({
        'providers': list(api_keys.keys()),
        'encryption': TIER_CONFIG[Tier(user.get('subscription', 'free'))]['encryption']
    })


@app.route('/api/keys', methods=['POST'])
@require_auth
def add_key():
    """Add encrypted API key (BYOK)."""
    data = request.json or {}
    provider = data.get('provider')  # 'openrouter', 'anthropic', 'openai'
    api_key = data.get('api_key')
    
    if not provider or not api_key:
        return jsonify({'error': 'Provider and api_key required'}), 400
    
    user = db.get_user(g.user_id)
    tier = Tier(user.get('subscription', 'free'))
    
    # Check if tier supports encryption
    if not TIER_CONFIG[tier]['encryption']:
        return jsonify({'error': 'API key encryption requires Pro tier'}), 403
    
    # Encrypt and store
    success = llm_manager.encrypt_api_key(g.user_id, provider, api_key)
    
    if success:
        return jsonify({'status': 'ok', 'provider': provider})
    return jsonify({'error': 'Failed to store key'}), 500


# ==================== MODELS ====================

@app.route('/api/models', methods=['GET'])
def list_models():
    """List available models for user tier."""
    return jsonify(llm_manager.get_available_models(g.user_id))


# ==================== CHAT ====================

@app.route('/api/chat', methods=['POST'])
@require_auth
def chat():
    """Send chat message to LLM."""
    data = request.json or {}
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')
    model = data.get('model')
    system_prompt = data.get('system_prompt', 'You are a helpful AI assistant.')
    
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    # Get or create conversation
    if not conversation_id:
        conv = db.create_conversation(g.user_id, message[:50])
        conversation_id = conv['id']
    
    # Get conversation history
    messages_db = db.get_conversation_messages(conversation_id)
    
    # Build messages for LLM
    messages = [{'role': 'system', 'content': system_prompt}]
    for msg in messages_db:
        messages.append({'role': msg['role'], 'content': msg['content']})
    messages.append({'role': 'user', 'content': message})
    
    # Get user for model selection
    user = db.get_user(g.user_id)
    if not model:
        model = user.get('active_model', 'phi3') if user else 'phi3'
    
    # Call LLM
    response = llm_manager.chat(g.user_id, messages, model)
    
    if response.success:
        # Store messages
        db.add_message(conversation_id, 'user', message, model_used=model, directive='STANDARD')
        db.add_message(conversation_id, 'assistant', response.content, model_used=model, directive='STANDARD')
        
        return jsonify({
            'response': response.content,
            'model': response.model,
            'provider': response.provider,
            'conversation_id': conversation_id,
            'tokens': response.tokens_used,
            'cost': response.cost
        })
    else:
        return jsonify({'error': response.error}), 400


# ==================== CONVERSATIONS ====================

@app.route('/api/conversations', methods=['GET'])
@require_auth
def list_conversations():
    """List user conversations."""
    conversations = db.get_conversations(g.user_id)
    return jsonify(conversations)


@app.route('/api/conversations/<conv_id>', methods=['GET'])
@require_auth
def get_conversation(conv_id):
    """Get conversation with messages."""
    conv = db.get_conversation(conv_id)
    if not conv or conv.get('user_id') != g.user_id:
        return jsonify({'error': 'Not found'}), 404
    
    messages = db.get_conversation_messages(conv_id)
    return jsonify({'conversation': conv, 'messages': messages})


# ==================== TOOLS ====================

# Note: Tools require separate implementation - reusing from v2
# tools_endpoint = f"http://127.0.0.1:{int(os.environ.get('PORT', 8080))+1}/api/tools"  # Placeholder


# ==================== STATUS ====================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status."""
    return jsonify({
        'running': True,
        'version': '5.0.0',
        'enterprise': True,
        'components': {
            'database': db is not None,
            'llm_manager': llm_manager is not None,
        },
        'tiers': {
            'free': {'providers': [p.value for p in TIER_CONFIG[Tier.FREE]['providers']]},
            'basic': {'providers': [p.value for p in TIER_CONFIG[Tier.BASIC]['providers']]},
            'pro': {'providers': [p.value for p in TIER_CONFIG[Tier.PRO]['providers']]},
        }
    })


# ==================== HTML UI ====================

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>NexusOS v5 - Enterprise</title>
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #0a0a0a; color: #e0e0e0; }
        h1 { color: #00ff88; }
        .card { background: #1a1a1a; padding: 20px; border-radius: 8px; margin: 15px 0; }
        .btn { background: #00ff88; color: #000; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; background: #2a2a2a; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; }
        .tier { display: inline-block; padding: 10px 20px; margin: 5px; border-radius: 8px; background: #2a2a2a; }
        .tier.free { border: 1px solid #666; }
        .tier.basic { border: 1px solid #00aaff; }
        .tier.pro { border: 1px solid #ff00ff; }
        .badge { padding: 3px 8px; border-radius: 4px; font-size: 12px; background: #333; }
        .api-key { font-family: monospace; background: #222; padding: 2px 6px; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>🤖 NexusOS v5 - Enterprise</h1>
    
    <div class="card">
        <h2>Enterprise Features</h2>
        <p>✅ BYOK Model (Bring Your Own Key)</p>
        <p>✅ API Key Encryption (Pro tier)</p>
        <p>✅ Multi-Provider (Ollama, OpenRouter, Anthropic)</p>
        <p>✅ Usage Tracking & Rate Limiting</p>
        <p>✅ Subscription Tiers (Free/Basic/Pro)</p>
    </div>
    
    <div class="card">
        <h2>Tiers</h2>
        <div class="tier free">
            <strong>Free</strong><br>
            Ollama only<br>
            Unlimited local
        </div>
        <div class="tier basic">
            <strong>Basic</strong><br>
            BYOK + credits<br>
            OpenRouter
        </div>
        <div class="tier pro">
            <strong>Pro</strong><br>
            Encrypted keys<br>
            All providers
        </div>
    </div>
    
    <div class="card">
        <h2>API Endpoints</h2>
        <ul>
            <li><code>POST /api/auth/register</code> - Register</li>
            <li><code>POST /api/auth/login</code> - Login</li>
            <li><code>GET /api/models</code> - List models</li>
            <li><code>POST /api/chat</code> - Chat with LLM</li>
            <li><code>GET /api/keys</code> - List API keys</li>
            <li><code>POST /api/keys</code> - Add encrypted key</li>
        </ul>
    </div>
    
    <div class="card">
        <h2>Quick Test</h2>
        <pre>curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <user_id>" \
  -d '{"message": "Hello, NexusOS!"}'</pre>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, threaded=True)

# ==================== MCP (Model Context Protocol) ====================

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    """MCP protocol endpoint."""
    from mcp_server import MCPServer
    mcp = MCPServer(g.user_id)
    message = request.json or {}
    response = mcp.handle_message(message)
    return jsonify(response)


@app.route('/mcp/tools', methods=['GET'])
def mcp_list_tools():
    """List MCP tools."""
    from mcp_server import MCPTools, MCPServer
    mcp = MCPServer(g.user_id)
    return jsonify({"tools": mcp.tools.list()})


@app.route('/mcp/resources', methods=['GET'])
def mcp_list_resources():
    """List MCP resources."""
    from mcp_server import MCPServer
    mcp = MCPServer(g.user_id)
    return jsonify({"resources": mcp.resources.list()})


@app.route('/mcp/initialize', methods=['POST'])
def mcp_initialize():
    """MCP initialize."""
    from mcp_server import MCPServer
    mcp = MCPServer(g.user_id)
    return jsonify(mcp.server_info)


@app.route('/mcp/chat', methods=['POST'])
@require_auth
def mcp_chat():
    """Chat with LLM using MCP format."""
    data = request.json or {}
    
    # MCP-style message
    messages = data.get('messages', [])
    max_tokens = data.get('maxTokens', 4000)
    
    if not messages:
        return jsonify({'error': 'Messages required'}), 400
    
    # Build system prompt
    system_prompt = data.get('systemPrompt', 'You are NexusOS, an AI assistant.')
    
    llm_messages = [{'role': 'system', 'content': system_prompt}]
    for msg in messages:
        llm_messages.append({'role': msg.get('role', 'user'), 'content': msg.get('content', '')})
    
    # Call LLM
    response = llm_manager.chat(g.user_id, llm_messages)
    
    if response.success:
        # Track usage for analytics (input_tokens estimate based on message count)
        input_tokens_est = sum(len(m.get('content', '')) // 4 for m in messages) + len(system_prompt) // 4
        db.track_usage(g.user_id, response.model, response.provider, input_tokens_est, response.tokens_used or 0)
        
        return jsonify({
            'content': response.content,
            'model': response.model,
            'provider': response.provider,
            'usage': {
                'inputTokens': input_tokens_est,
                'outputTokens': response.tokens_used or 0
            }
        })
    else:
        return jsonify({'error': response.error}), 400


# Webhook System for Enterprise Integration
import requests
import threading

webhooks = {}  # {user_id: [webhook_urls]}

@app.route('/api/webhooks', methods=['POST'])
def create_webhook():
    """Register a webhook URL"""
    data = request.json or {}
    user_id = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not user_id:
        return jsonify({'error': 'Auth required'}), 401
    
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    # Validate URL
    try:
        response = requests.get(url, timeout=5)
    except:
        return jsonify({'error': 'Invalid URL'}), 400
    
    if user_id not in webhooks:
        webhooks[user_id] = []
    
    webhook_id = len(webhooks[user_id]) + 1
    webhooks[user_id].append({'id': webhook_id, 'url': url, 'active': True})
    
    return jsonify({'webhook_id': webhook_id, 'url': url})

@app.route('/api/webhooks', methods=['GET'])
def list_webhooks():
    """List user's webhooks"""
    user_id = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not user_id:
        return jsonify({'error': 'Auth required'}), 401
    
    return jsonify({'webhooks': webhooks.get(user_id, [])})

@app.route('/api/webhooks/<int:webhook_id>', methods=['DELETE'])
def delete_webhook(webhook_id):
    """Delete a webhook"""
    user_id = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not user_id:
        return jsonify({'error': 'Auth required'}), 401
    
    if user_id in webhooks:
        webhooks[user_id] = [w for w in webhooks[user_id] if w['id'] != webhook_id]
    
    return jsonify({'status': 'deleted'})

# ==================== USAGE ANALYTICS ====================

@app.route('/api/analytics/usage', methods=['GET'])
@require_auth
def get_usage_analytics():
    """Get usage analytics for the authenticated user."""
    days = request.args.get('days', 30, type=int)
    usage = db.get_user_usage(g.user_id, days)
    summary = db.get_usage_summary(g.user_id)
    return jsonify({
        'period_days': days,
        'summary': summary,
        'by_model': usage
    })

@app.route('/api/analytics/usage/today', methods=['GET'])
@require_auth
def get_today_usage():
    """Get today's usage summary."""
    usage = db.get_user_usage(g.user_id, days=1)
    return jsonify({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'usage': usage
    })

def trigger_webhook(user_id, event_type, data):
    """Trigger webhooks in background"""
    if user_id not in webhooks:
        return
    
    def _trigger():
        for webhook in webhooks[user_id]:
            if webhook['active']:
                try:
                    requests.post(webhook['url'], json={
                        'event': event_type,
                        'data': data
                    }, timeout=5)
                except:
                    pass
    
    threading.Thread(target=_trigger).start()
