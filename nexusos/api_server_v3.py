"""
NexusOS API - Subscription Model + Inner Life Integration

Features:
- Subscription tiers (Free, Basic, Pro)
- Inner life integration (affect, socratic, patterns)
- Per-user memory
- Multi-LLM support
"""

from flask import Flask, request, jsonify, session, render_template_string
import hashlib
import uuid
import json
import os
from datetime import datetime, timedelta
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('NEXUSOS_SECRET', 'nexusos-secret-change-in-production')

# Paths
USERS_DIR = '/opt/nexusos-api/users'
MEMORIES_DIR = '/opt/nexusos-api/memories'

os.makedirs(USERS_DIR, exist_ok=True)
os.makedirs(MEMORIES_DIR, exist_ok=True)

# Subscription Tiers
SUBSCRIPTION_TIERS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'models': ['ollama'],
        'features': ['basic_chat', 'local_memory']
    },
    'basic': {
        'name': 'Basic',
        'price': 9.99,
        'models': ['ollama', 'openai'],
        'model_limits': {'gpt-4o-mini': 1000},  # messages per month
        'features': ['basic_chat', 'local_memory', 'long_context']
    },
    'pro': {
        'name': 'Pro',
        'price': 29.99,
        'models': ['ollama', 'openai', 'anthropic'],
        'model_limits': {'gpt-4o': 500, 'gpt-4o-mini': 2000, 'claude-sonnet': 500},
        'features': ['basic_chat', 'local_memory', 'long_context', 'priority_support', 'inner_life']
    }
}

# LLM Backends
LLM_BACKENDS = {
    'ollama': {'type': 'local', 'base_url': 'http://127.0.0.1:11435', 'models': ['phi3'], 'free': True},
    'openai': {'type': 'api', 'base_url': 'https://api.openai.com/v1', 'models': ['gpt-4o', 'gpt-4o-mini'], 'free': False},
    'anthropic': {'type': 'api', 'base_url': 'https://api.anthropic.com/v1', 'models': ['claude-sonnet-4-20250514'], 'free': False}
}

# Blank slate template
BLANK_SLATE = {
    "version": "1.0", "created_at": None, "user_id": None, "name": "", "email": "",
    "subscription": "free", "subscription_expires": None,
    "api_keys": {}, "active_model": "ollama",
    "conversation_history": [], "message_count": 0,
    "identity": {"name": "", "role": "", "goals": [], "values": []},
    "preferences": {"communication_style": "brief"},
    "knowledge": {"products": [], "customers": [], "domain_expertise": []},
    "memory": {"lessons_learned": [], "successful_patterns": [], "failure_modes": []}
}


def get_user(user_id):
    user_file = os.path.join(USERS_DIR, f'{user_id}.json')
    if os.path.exists(user_file):
        return json.load(open(user_file))
    return None


def save_user(user_id, user_data):
    user_file = os.path.join(USERS_DIR, f'{user_id}.json')
    with open(user_file, 'w') as f:
        json.dump(user_data, f, indent=2)


def create_user(user_id, name=None, email=None):
    user = BLANK_SLATE.copy()
    user['created_at'] = datetime.now().isoformat()
    user['user_id'] = user_id
    user['name'] = name or ""
    user['email'] = email or ""
    save_user(user_id, user)
    return user


def generate_token():
    return hashlib.sha256(f"{uuid.uuid4()}{datetime.now()}".encode()).hexdigest()[:32]


# Inner Life: Affect Analysis
def analyze_affect(message):
    """Analyze message for affect signals"""
    msg = message.lower()
    signals = {}
    
    # Urgency
    if any(w in msg for w in ['urgent', 'asap', 'immediately', 'now']):
        signals['urgency'] = 0.9
    elif any(w in msg for w in ['today', 'tonight', 'deadline']):
        signals['urgency'] = 0.7
    else:
        signals['urgency'] = 0.1
    
    # Novelty (simple check)
    known = ['hello', 'hi', 'help', 'what', 'how', 'why', 'nexus', 'os']
    signals['novelty'] = 0.3 if any(w in msg for w in known) else 0.7
    
    # Threat (failure modes)
    signals['threat'] = 0.1
    
    # Confidence
    uncertain = ['maybe', 'perhaps', 'think', 'might', 'could']
    signals['confidence'] = 0.4 if any(w in msg for w in uncertain) else 0.8
    
    # Value (revenue/goal related)
    signals['value'] = 0.5
    if any(w in msg for w in ['revenue', 'money', 'customer', 'sale', 'pay']):
        signals['value'] = 0.9
    
    return signals


def get_directive(signals):
    """Get processing directive from affect signals"""
    if signals.get('urgency', 0) > 0.7:
        return 'PRIORITIZE_ACTION'
    if signals.get('threat', 0) > 0.5:
        return 'ADVERSARIAL_SELF_TEST'
    if signals.get('novelty', 0) > 0.6:
        return 'DEEP_ANALYSIS'
    if signals.get('confidence', 0) < 0.5:
        return 'FLAG_UNCERTAINTY'
    if signals.get('value', 0) > 0.8:
        return 'MAX_EFFORT'
    return 'STANDARD'


# Inner Life: Socratic Dialogue (simplified)
def socratic_check(message):
    """Check if message needs adversarial reasoning"""
    significant = ['should', 'will', 'decide', 'commit', 'build', 'launch', 'send', 'create', 'delete', 'change']
    msg = message.lower()
    return any(w in msg for w in significant)


def call_llm(user_id, message, system_prompt=None):
    user = get_user(user_id)
    if not user:
        return {'error': 'User not found'}
    
    # Check subscription
    tier = user.get('subscription', 'free')
    tier_config = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
    
    backend_name = user.get('active_model', 'ollama')
    backend = LLM_BACKENDS.get(backend_name, LLM_BACKENDS['ollama'])
    
    # Check if model allowed in tier
    if backend_name not in tier_config['models']:
        return {'error': f'{backend_name} not available on {tier} tier'}
    
    # Inner Life: Get directive
    affect = analyze_affect(message)
    directive = get_directive(affect)
    
    # Inner Life: Socratic check
    socratic_needed = socratic_check(message)
    socratic_note = ""
    if socratic_needed and tier == 'pro':
        socratic_note = "\n\n[Inner Life: Consider both sides before responding.]"
    
    # Build system prompt with inner life
    inner_life_prompt = f"""You are {user.get('name', 'an AI assistant')}.
Directive: {directive}
Style: {user.get('preferences', {}).get('communication_style', 'brief')}
{socratic_note}"""
    
    if system_prompt:
        inner_life_prompt += "\n" + system_prompt
    
    # Build messages
    messages = [{'role': 'system', 'content': inner_life_prompt}]
    for conv in user.get('conversation_history', [])[-5:]:
        messages.append({'role': 'user', 'content': conv['message']})
        messages.append({'role': 'assistant', 'content': conv['response']})
    messages.append({'role': 'user', 'content': message})
    
    payload = {'model': backend['models'][0], 'messages': messages, 'stream': False}
    
    # Make API call
    try:
        if backend['type'] == 'local':
            r = requests.post(f"{backend['base_url']}/api/chat", json=payload, timeout=120)
            result = r.json()
            response = result.get('message', {}).get('content', '')
        else:
            api_key = user.get('api_keys', {}).get(backend_name)
            if not api_key:
                return {'error': f'API key required for {backend_name}'}
            
            headers = {'Authorization': f'Bearer {api_key}'}
            if backend_name == 'anthropic':
                headers['anthropic-version'] = '2023-06-01'
            
            r = requests.post(f"{backend['base_url']}/chat/completions", json=payload, headers=headers, timeout=120)
            result = r.json()
            response = result['choices'][0]['message']['content']
        
        # Update message count
        user['message_count'] = user.get('message_count', 0) + 1
        save_user(user_id, user)
        
        # Save conversation
        conv_entry = {'timestamp': datetime.now().isoformat(), 'message': message, 
                     'response': response, 'model_used': backend_name, 'directive': directive}
        user['conversation_history'].append(conv_entry)
        user['conversation_history'] = user['conversation_history'][-100:]
        save_user(user_id, user)
        
        return {'response': response, 'directive': directive, 'tier': tier}
    
    except Exception as e:
        return {'error': str(e)}


HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>NexusOS</title>
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #0a0a0a; color: #e0e0e0; }
        h1 { color: #00ff88; }
        .card { background: #1a1a1a; padding: 20px; border-radius: 8px; margin: 15px 0; }
        .btn { background: #00ff88; color: #000; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn:hover { background: #00cc6a; }
        input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; background: #2a2a2a; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; }
        .chat { max-height: 400px; overflow-y: auto; margin: 20px 0; }
        .msg { padding: 10px 15px; margin: 5px 0; border-radius: 8px; }
        .user { background: #0044aa; margin-left: 20%; }
        .bot { background: #1a1a1a; margin-right: 20%; border: 1px solid #333; }
        .tier { display: inline-block; padding: 10px 20px; margin: 5px; border-radius: 8px; background: #2a2a2a; }
        .tier.selected { border: 2px solid #00ff88; }
        .tier.free { border-color: #666; }
        .tier.basic { border-color: #00aaff; }
        .tier.pro { border-color: #ff00ff; }
        .badge { padding: 3px 8px; border-radius: 4px; font-size: 12px; }
        .badge-free { background: #666; }
        .badge-basic { background: #00aaff; }
        .badge-pro { background: #ff00ff; }
    </style>
</head>
<body>
    <h1>🤖 NexusOS</h1>
    
    {% if not session.get('user_id') %}
    <div class="card">
        <h2>Welcome to NexusOS</h2>
        <p>AI with Inner Life</p>
        <form method="POST" action="/login">
            <input type="text" name="name" placeholder="Your name" required>
            <input type="email" name="email" placeholder="Email (optional)">
            <button type="submit" class="btn">Get Started - Free</button>
        </form>
    </div>
    {% else %}
    <div class="card">
        <p>Welcome, <strong>{{ user.name }}</strong> 
           <span class="badge badge-{{ user.subscription }}">{{ user.subscription|upper }}</span>
           | <a href="/logout" style="color:#ff6666">Logout</a></p>
        
        <h3>Subscription</h3>
        <div class="tier {% if user.subscription == 'free' %}selected{% endif %} free">
            <strong>Free</strong><br>$0/mo<br>Ollama only
        </div>
        <div class="tier {% if user.subscription == 'basic' %}selected{% endif %} basic">
            <strong>Basic</strong><br>$9.99/mo<br>GPT-4o mini
        </div>
        <div class="tier {% if user.subscription == 'pro' %}selected{% endif %} pro">
            <strong>Pro</strong><br>$29.99/mo<br>All models + Inner Life
        </div>
        
        <h3>LLM Settings</h3>
        <form method="POST" action="/settings">
            <label>Active Model:</label>
            <select name="model">
                <option value="ollama" {% if user.active_model == 'ollama' %}selected{% endif %}>Ollama (phi3) - Free</option>
                <option value="openai" {% if user.active_model == 'openai' %}selected{% endif %}>OpenAI GPT-4</option>
                <option value="anthropic" {% if user.active_model == 'anthropic' %}selected{% endif %}>Anthropic Claude</option>
            </select>
            <label>API Key (for OpenAI/Anthropic):</label>
            <input type="password" name="api_key" placeholder="sk-...">
            <button type="submit" class="btn">Save</button>
        </form>
    </div>
    
    <div class="card">
        <h3>Chat {% if user.subscription == 'pro' %}<span class="badge badge-pro">Inner Life Active</span>{% endif %}</h3>
        <div class="chat">
            {% for conv in user.conversation_history[-10:] %}
            <div class="msg user">{{ conv.message }}</div>
            <div class="msg bot">{{ conv.response }}</div>
            {% endfor %}
        </div>
        <form method="POST" action="/chat">
            <textarea name="message" placeholder="Ask anything..."></textarea>
            <button type="submit" class="btn">Send</button>
        </form>
    </div>
    
    <div class="card">
        <h3>Stats</h3>
        <p>Messages: {{ user.message_count }} | Conversations: {{ user.conversation_history|length }}</p>
    </div>
    {% endif %}
</body>
</html>
'''


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return render_template_string(HTML, user=None, session=session)
    
    user = get_user(session['user_id'])
    if not user:
        session.pop('user_id', None)
        return render_template_string(HTML, user=None, session=session)
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        if action == 'login' or not user:
            name = request.form.get('name', 'User')
            email = request.form.get('email', '')
            user_id = generate_token()
            create_user(user_id, name, email)
            session['user_id'] = user_id
            user = get_user(user_id)
        
        elif action == 'settings':
            user['active_model'] = request.form.get('model', 'ollama')
            api_key = request.form.get('api_key', '').strip()
            if api_key:
                user['api_keys'][user['active_model']] = api_key
            save_user(session['user_id'], user)
        
        elif action == 'chat':
            message = request.form.get('message', '')
            if message:
                result = call_llm(session['user_id'], message)
                if 'error' in result:
                    # Show error in chat
                    user['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': message,
                        'response': f"Error: {result['error']}",
                        'model_used': user.get('active_model', 'ollama'),
                        'directive': 'ERROR'
                    })
                user = get_user(session['user_id'])
    
    return render_template_string(HTML, user=user, session=session)


@app.route('/login', methods=['POST'])
def login():
    name = request.form.get('name', 'User')
    email = request.form.get('email', '')
    user_id = generate_token()
    create_user(user_id, name, email)
    session['user_id'] = user_id
    return {'status': 'ok', 'user_id': user_id}


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return {'status': 'ok'}


@app.route('/api/subscription', methods=['GET'])
def get_subscription():
    return jsonify({'tiers': SUBSCRIPTION_TIERS})


@app.route('/api/models', methods=['GET'])
def list_models():
    return jsonify({'backends': LLM_BACKENDS, 'tiers': SUBSCRIPTION_TIERS})


@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json or {}
    user_id = data.get('user_id') or session.get('user_id')
    message = data.get('message', '')
    
    if not user_id or not message:
        return jsonify({'error': 'user_id and message required'}), 400
    
    return jsonify(call_llm(user_id, message))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)