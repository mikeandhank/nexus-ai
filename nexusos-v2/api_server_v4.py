"""
NexusOS v2 - Full API Server

Integrates all components:
- Database (SQLite)
- Event Bus (persistent)
- Tool Engine
- Skills
- Agent Pool
- Inner Life
"""

import os
import sys
import json
import uuid
import hashlib
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, session
import logging

# Import components
from database import init_db, get_db
from event_bus_v2 import init_event_bus, get_event_bus, EventType
from tool_engine import get_tool_engine
from skills import get_skill_registry
from agent_pool import get_agent_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('NEXUSOS_SECRET', 'nexusos-v2-secret-change-me')

# Initialize components
DB_PATH = os.environ.get("NEXUSOS_DB", "/opt/nexusos-data/nexusos.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Initialize database
db = init_db(DB_PATH)
logger.info("Database initialized")

# Initialize event bus
event_bus = init_event_bus(DB_PATH)
event_bus.start()
logger.info("Event bus started")

# Initialize tool engine
tool_engine = get_tool_engine()
logger.info("Tool engine initialized")

# Initialize skills
skill_registry = get_skill_registry()
logger.info("Skill registry initialized")

# Initialize agent pool
agent_pool = get_agent_pool(db, tool_engine)
logger.info("Agent pool initialized")


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
        event_bus.emit('user_registered', {'user_id': user_id, 'email': email})
        return jsonify({'user_id': user_id, 'email': email, 'name': name})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user."""
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    
    user = db.get_user_by_email(email)
    if not user or not db.verify_password(user['id'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Update last login
    db.update_user(user['id'], last_login=datetime.now().isoformat())
    
    session['user_id'] = user['id']
    event_bus.emit('user_login', {'user_id': user['id']})
    
    return jsonify({'user_id': user['id'], 'name': user.get('name'), 'subscription': user.get('subscription')})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user."""
    session.pop('user_id', None)
    return jsonify({'status': 'ok'})


def require_auth(f):
    """Require authentication."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id') or request.json.get('user_id') if request.json else None
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


# ==================== USER ====================

@app.route('/api/user', methods=['GET'])
@require_auth
def get_user():
    """Get current user."""
    user_id = session.get('user_id')
    user = db.get_user(user_id)
    if user:
        user.pop('password_hash', None)
    return jsonify(user)


@app.route('/api/user', methods=['PUT'])
@require_auth
def update_user():
    """Update user settings."""
    user_id = session.get('user_id')
    data = request.json or {}
    
    updated = db.update_user(user_id, **data)
    if updated:
        updated.pop('password_hash', None)
    return jsonify(updated or {'error': 'Update failed'})


# ==================== CONVERSATIONS ====================

@app.route('/api/conversations', methods=['GET'])
@require_auth
def list_conversations():
    """List user conversations."""
    user_id = session.get('user_id')
    conversations = db.get_conversations(user_id)
    return jsonify(conversations)


@app.route('/api/conversations', methods=['POST'])
@require_auth
def create_conversation():
    """Create new conversation."""
    user_id = session.get('user_id')
    data = request.json or {}
    title = data.get('title', 'New Chat')
    
    conv = db.create_conversation(user_id, title)
    event_bus.emit('conversation_created', {'user_id': user_id, 'conversation_id': conv['id']})
    return jsonify(conv)


@app.route('/api/conversations/<conv_id>', methods=['GET'])
@require_auth
def get_conversation(conv_id):
    """Get conversation."""
    user_id = session.get('user_id')
    conv = db.get_conversation(conv_id)
    
    if not conv or conv.get('user_id') != user_id:
        return jsonify({'error': 'Not found'}), 404
    
    messages = db.get_conversation_messages(conv_id)
    return jsonify({'conversation': conv, 'messages': messages})


# ==================== CHAT ====================

@app.route('/api/chat', methods=['POST'])
@require_auth
def chat():
    """Send chat message."""
    user_id = session.get('user_id')
    data = request.json or {}
    
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')
    
    if not conversation_id:
        # Create new conversation
        conv = db.create_conversation(user_id, message[:50])
        conversation_id = conv['id']
    
    # Get user settings
    user = db.get_user(user_id)
    active_model = user.get('active_model', 'ollama')
    
    # Get conversation history
    messages = db.get_conversation_messages(conversation_id)
    
    # Build prompt for LLM (simplified - actual implementation would call LLM)
    system_prompt = f"You are {user.get('name', 'an AI assistant')}. Directive: STANDARD"
    
    # Process message (actual LLM call would go here)
    response = f"[NexusOS] Received: {message[:100]}... (LLM integration pending)"
    directive = "STANDARD"
    
    # Store message
    db.add_message(conversation_id, 'user', message, model_used=active_model, directive=directive)
    db.add_message(conversation_id, 'assistant', response, model_used=active_model, directive=directive)
    
    # Emit event
    event_bus.emit(EventType.AGENT_MESSAGE.value, {
        'user_id': user_id,
        'conversation_id': conversation_id,
        'directive': directive
    })
    
    return jsonify({
        'response': response,
        'directive': directive,
        'conversation_id': conversation_id
    })


# ==================== TOOLS ====================

@app.route('/api/tools', methods=['GET'])
@require_auth
def list_tools():
    """List available tools."""
    tools = tool_engine.list_tools()
    return jsonify({'tools': tools})


@app.route('/api/tools/execute', methods=['POST'])
@require_auth
def execute_tool():
    """Execute a tool."""
    data = request.json or {}
    tool_name = data.get('tool')
    params = data.get('params', {})
    
    if not tool_name:
        return jsonify({'error': 'Tool name required'}), 400
    
    result = tool_engine.execute_tool(tool_name, **params)
    
    event_bus.emit('tool_executed', {
        'tool': tool_name,
        'success': result.success,
        'user_id': session.get('user_id')
    })
    
    return jsonify(result.to_dict())


# ==================== SKILLS ====================

@app.route('/api/skills', methods=['GET'])
@require_auth
def list_skills():
    """List available skills."""
    skills = skill_registry.get_skills()
    return jsonify({'skills': [s.to_dict() for s in skills]})


@app.route('/api/skills/execute', methods=['POST'])
@require_auth
def execute_skill():
    """Execute a skill."""
    data = request.json or {}
    skill_name = data.get('skill')
    context = data.get('context', {})
    context['user_id'] = session.get('user_id')
    
    try:
        result = skill_registry.execute_skill(skill_name, context)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ==================== AGENTS ====================

@app.route('/api/agents', methods=['GET'])
@require_auth
def list_agents():
    """List user's agents."""
    user_id = session.get('user_id')
    agents = agent_pool.get_agents(user_id)
    return jsonify({'agents': [a.to_dict() for a in agents]})


@app.route('/api/agents', methods=['POST'])
@require_auth
def create_agent():
    """Create new agent."""
    user_id = session.get('user_id')
    data = request.json or {}
    
    name = data.get('name')
    template = data.get('template', 'general')
    
    if not name:
        return jsonify({'error': 'Agent name required'}), 400
    
    agent = agent_pool.create_agent(user_id, name, template)
    event_bus.emit('agent_created', {'user_id': user_id, 'agent_id': agent.id, 'name': name})
    
    return jsonify(agent.to_dict())


@app.route('/api/agents/<agent_id>', methods=['GET'])
@require_auth
def get_agent(agent_id):
    """Get agent details."""
    agent = agent_pool.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    return jsonify(agent.to_dict())


@app.route('/api/agents/<agent_id>', methods=['DELETE'])
@require_auth
def delete_agent(agent_id):
    """Delete agent."""
    success = agent_pool.delete_agent(agent_id)
    return jsonify({'success': success})


@app.route('/api/agents/<agent_id>/execute', methods=['POST'])
@require_auth
def execute_agent(agent_id):
    """Execute task with agent."""
    data = request.json or {}
    task = data.get('task')
    
    if not task:
        return jsonify({'error': 'Task required'}), 400
    
    result = agent_pool.execute_task(agent_id, task)
    return jsonify(result)


# ==================== MEMORY ====================

@app.route('/api/memory/working', methods=['GET'])
@require_auth
def get_working_memory():
    """Get working memory."""
    user_id = session.get('user_id')
    key = request.args.get('key')
    
    if key:
        value = db.get_working_memory(user_id, key)
        return jsonify({'key': key, 'value': value})
    
    return jsonify({'error': 'Key required'}), 400


@app.route('/api/memory/working', methods=['POST'])
@require_auth
def set_working_memory():
    """Set working memory."""
    user_id = session.get('user_id')
    data = request.json or {}
    
    key = data.get('key')
    value = data.get('value')
    ttl = data.get('ttl', 3600)
    
    if not key:
        return jsonify({'error': 'Key required'}), 400
    
    db.set_working_memory(user_id, key, value, ttl)
    return jsonify({'status': 'ok'})


@app.route('/api/memory/episodic', methods=['GET'])
@require_auth
def get_episodic_memory():
    """Get episodic memories."""
    user_id = session.get('user_id')
    memories = db.get_episodic_memories(user_id)
    return jsonify(memories)


@app.route('/api/memory/semantic', methods=['GET'])
@require_auth
def search_semantic_memory():
    """Search semantic memory."""
    user_id = session.get('user_id')
    query = request.args.get('q', '')
    
    results = db.search_semantic_memory(user_id, query)
    return jsonify(results)


# ==================== AUDIT ====================

@app.route('/api/audit', methods=['GET'])
@require_auth
def get_audit_logs():
    """Get audit logs."""
    user_id = session.get('user_id')
    limit = int(request.args.get('limit', 100))
    
    logs = db.get_audit_logs(user_id, limit)
    return jsonify(logs)


# ==================== STATUS ====================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status."""
    return jsonify({
        'running': True,
        'components': {
            'database': db is not None,
            'event_bus': event_bus.running,
            'tool_engine': len(tool_engine.list_tools()) > 0,
            'skills': len(skill_registry.runtime_skills),
            'agents': len(agent_pool.agents),
        },
        'event_bus_state': event_bus.get_state(),
    })


# ==================== HTML UI ====================

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>NexusOS v2</title>
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #0a0a0a; color: #e0e0e0; }
        h1 { color: #00ff88; }
        .card { background: #1a1a1a; padding: 20px; border-radius: 8px; margin: 15px 0; }
        .btn { background: #00ff88; color: #000; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; background: #2a2a2a; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; }
        .status { display: inline-block; padding: 5px 10px; border-radius: 4px; background: #333; }
        .status.ok { background: #00ff88; color: #000; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    </style>
</head>
<body>
    <h1>🤖 NexusOS v2</h1>
    
    <div class="card">
        <h2>System Status</h2>
        <div class="grid">
            <div class="status ok">Database: OK</div>
            <div class="status ok">Event Bus: OK</div>
            <div class="status ok">Tools: 12</div>
            <div class="status ok">Skills: 5</div>
            <div class="status">Agents: 0</div>
            <div class="status ok">Memory: OK</div>
        </div>
    </div>
    
    <div class="card">
        <h2>Authentication</h2>
        <form method="POST" action="/api/auth/register">
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <input type="text" name="name" placeholder="Name">
            <button type="submit" class="btn">Register</button>
        </form>
    </div>
    
    <div class="card">
        <h2>Quick Actions</h2>
        <ul>
            <li><a href="/api/tools" style="color:#00ff88">List Tools</a></li>
            <li><a href="/api/skills" style="color:#00ff88">List Skills</a></li>
            <li><a href="/api/status" style="color:#00ff88">System Status</a></li>
        </ul>
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
