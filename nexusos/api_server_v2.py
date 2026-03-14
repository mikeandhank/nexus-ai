"""
NexusOS API - Auth, User Memory, and Multi-LLM Support

Features:
- Simple token-based auth
- Per-user conversation memory
- Multi-LLM support (Ollama free, OpenAI/Anthropic BYOK)
- Template "blank slate" memory
"""

from flask import Flask, request, jsonify, session, render_template_string
import hashlib
import uuid
import json
import os
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('NEXUSOS_SECRET', 'change-in-production')

# Paths
USERS_DIR = '/opt/nexusos-api/users'
MEMORIES_DIR = '/opt/nexusos-api/memories'
TEMPLATES_DIR = '/opt/nexusos-api/templates'

# Ensure directories exist
os.makedirs(USERS_DIR, exist_ok=True)
os.makedirs(MEMORIES_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Multi-LLM Backend Config
LLM_BACKENDS = {
    'ollama': {
        'type': 'local',
        'base_url': 'http://127.0.0.1:11435',
        'models': ['phi3', 'llama2', 'mistral'],
        'free': True
    },
    'openai': {
        'type': 'api',
        'base_url': 'https://api.openai.com/v1',
        'models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
        'free': False
    },
    'anthropic': {
        'type': 'api', 
        'base_url': 'https://api.anthropic.com/v1',
        'models': ['claude-sonnet-4-20250514', 'claude-haiku-4-20250514'],
        'free': False
    }
}

# Template blank slate memory
BLANK_SLATE_TEMPLATE = {
    "version": "1.0",
    "created_at": None,
    "identity": {
        "name": "",
        "role": "",
        "goals": [],
        "values": []
    },
    "preferences": {
        "communication_style": "brief",
        "decision_framework": [],
        "trusted_sources": [],
        "avoid_patterns": []
    },
    "knowledge": {
        "products": [],
        "customers": [],
        "processes": [],
        "domain_expertise": []
    },
    "memory": {
        "lessons_learned": [],
        "successful_patterns": [],
        "failure_modes": [],
        "important_context": []
    },
    "conversations": []
}


def get_user(user_id):
    user_file = os.path.join(USERS_DIR, f'{user_id}.json')
    if os.path.exists(user_file):
        with open(user_file) as f:
            return json.load(f)
    return None


def save_user(user_id, user_data):
    user_file = os.path.join(USERS_DIR, f'{user_id}.json')
    with open(user_file, 'w') as f:
        json.dump(user_data, f, indent=2)


def create_user(user_id, name=None, email=None):
    user_data = BLANK_SLATE_TEMPLATE.copy()
    user_data['created_at'] = datetime.now().isoformat()
    user_data['user_id'] = user_id
    user_data['name'] = name or ""
    user_data['email'] = email or ""
    user_data['api_keys'] = {}
    user_data['active_model'] = 'ollama'
    user_data['conversation_history'] = []
    
    user_mem_dir = os.path.join(MEMORIES_DIR, user_id)
    os.makedirs(user_mem_dir, exist_ok=True)
    
    save_user(user_id, user_data)
    return user_data


def save_conversation(user_id, message, response):
    user = get_user(user_id)
    if not user:
        return
    
    conv_entry = {
        'timestamp': datetime.now().isoformat(),
        'message': message,
        'response': response,
        'model_used': user.get('active_model', 'ollama')
    }
    
    user['conversation_history'].append(conv_entry)
    user['conversation_history'] = user['conversation_history'][-100:]
    
    save_user(user_id, user)
    
    conv_file = os.path.join(MEMORIES_DIR, user_id, 'conversations.json')
    with open(conv_file, 'w') as f:
        json.dump(user['conversation_history'], f, indent=2)


def generate_token():
    return hashlib.sha256(f"{uuid.uuid4()}{datetime.now()}".encode()).hexdigest()[:32]


def call_llm(user_id, message, system_prompt=None):
    user = get_user(user_id)
    if not user:
        return {'error': 'User not found'}
    
    backend_name = user.get('active_model', 'ollama')
    backend = LLM_BACKENDS.get(backend_name, LLM_BACKENDS['ollama'])
    
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    
    for conv in user.get('conversation_history', [])[-5:]:
        messages.append({'role': 'user', 'content': conv['message']})
        messages.append({'role': 'assistant', 'content': conv['response']})
    
    messages.append({'role': 'user', 'content': message})
    
    payload = {
        'model': backend['models'][0] if backend['models'] else 'phi3',
        'messages': messages,
        'stream': False
    }
    
    if backend['type'] == 'local':
        try:
            r = requests.post(f"{backend['base_url']}/api/chat", json=payload, timeout=120)
            result = r.json()
            return {'response': result.get('message', {}).get('content', '')}
        except Exception as e:
            return {'error': str(e)}
    
    elif backend['type'] == 'api':
        api_key = user.get('api_keys', {}).get(backend_name)
        if not api_key:
            return {'error': f'API key required for {backend_name}'}
        
        headers = {'Authorization': f'Bearer {api_key}'}
        
        try:
            if backend_name == 'anthropic':
                headers['anthropic-version'] = '2023-06-01'
                payload['max_tokens'] = 1024
            
            r = requests.post(f"{backend['base_url']}/chat/completions", 
                            json=payload, headers=headers, timeout=120)
            result = r.json()
            
            if 'error' in result:
                return {'error': result['error']}
            
            choice = result['choices'][0]['message']['content']
            return {'response': choice}
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
        input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; background: #2a2a2a; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; }
        .chat { max-height: 400px; overflow-y: auto; margin: 20px 0; }
        .msg { padding: 10px 15px; margin: 5px 0; border-radius: 8px; }
        .user { background: #0044aa; margin-left: 20%; }
        .bot { background: #1a1a1a; margin-right: 20%; }
    </style>
</head>
<body>
    <h1> NexusOS</h1>
    
    {% if not session.get('user_id') %}
    <div class="card">
        <h2>Welcome to NexusOS</h2>
        <form method="POST" action="/login">
            <input type="text" name="name" placeholder="Your name" required>
            <input type="email" name="email" placeholder="Email (optional)">
            <button type="submit" class="btn">Get Started</button>
        </form>
    </div>
    {% else %}
    <div class="card">
        <p>Welcome, <strong>{{ user.name }}</strong> | <a href="/logout" style="color:#ff6666">Logout</a></p>
        
        <h3>LLM Settings</h3>
        <form method="POST" action="/settings">
            <label>Active Model:</label>
            <select name="model">
                <option value="ollama" {% if user.active_model == 'ollama' %}selected{% endif %}>Ollama (phi3) - Free</option>
                <option value="openai" {% if user.active_model == 'openai' %}selected{% endif %}>OpenAI GPT-4 (BYOK)</option>
                <option value="anthropic" {% if user.active_model == 'anthropic' %}selected{% endif %}>Anthropic Claude (BYOK)</option>
            </select>
            
            <label>API Key (if using OpenAI/Anthropic):</label>
            <input type="password" name="api_key" placeholder="sk-...">
            
            <button type="submit" class="btn">Save Settings</button>
        </form>
    </div>
    
    <div class="card">
        <h3>Chat</h3>
        <div class="chat" id="chat">
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
        <h3>Memory Stats</h3>
        <p>Conversations: {{ user.conversation_history|length }}</p>
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
                system_prompt = f"You are {user['name']}."
                result = call_llm(session['user_id'], message, system_prompt)
                
                if 'error' in result:
                    response = f"Error: {result['error']}"
                else:
                    response = result.get('response', 'No response')
                
                save_conversation(session['user_id'], message, response)
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


@app.route('/api/models', methods=['GET'])
def list_models():
    return jsonify({'backends': LLM_BACKENDS})


@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json or {}
    user_id = data.get('user_id') or session.get('user_id')
    message = data.get('message', '')
    
    if not user_id or not message:
        return jsonify({'error': 'user_id and message required'}), 400
    
    user = get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    system_prompt = f"You are {user.get('name', 'a helpful assistant')}."
    result = call_llm(user_id, message, system_prompt)
    
    if 'error' not in result:
        save_conversation(user_id, message, result.get('response', ''))
    
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)