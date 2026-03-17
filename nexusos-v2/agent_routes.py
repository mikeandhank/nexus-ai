"""
Agent Management API Routes
"""
import os
import asyncio
from flask import jsonify, request, g
from auth import require_auth
from agent_runtime import get_agent_runtime
from webhooks import get_webhook_manager
from database_compat import DatabaseCompat as Database

# Import agent executor components
try:
    from agent_executor import get_agent_executor
    from tool_engine import ToolEngine
    from llm_integration import OllamaProvider
    EXECUTOR_AVAILABLE = True
except ImportError as e:
    EXECUTOR_AVAILABLE = False
    print(f"Warning: Agent executor not available: {e}")

# Per-user executor cache
_user_executors = {}


def get_user_executor(user_id: str):
    """Get or create a cached executor for a user"""
    global _user_executors
    
    if user_id not in _user_executors:
        executor = get_agent_executor()
        
        # Set up Ollama
        os.environ['OLLAMA_URL'] = os.environ.get('OLLAMA_BASE_URL', 'http://nexusos-v2-nexusos-ollama-1:11434')
        executor.set_llm_provider(OllamaProvider())
        
        # Set up tools
        executor.set_tool_engine(ToolEngine())
        
        _user_executors[user_id] = executor
    
    return _user_executors[user_id]

# Initialize webhook manager
_db = Database()
_webhook_mgr = get_webhook_manager(_db)

def setup_agent_routes(app):
    runtime = get_agent_runtime(db=_db)
    
    @app.route('/api/agents', methods=['POST'])
    @require_auth
    def create_agent():
        """Create a new agent"""
        data = request.json or {}
        
        agent = runtime.create_agent(
            user_id=g.user_id,
            name=data.get('name', 'Unnamed Agent'),
            role=data.get('role', 'general'),
            system_prompt=data.get('system_prompt', ''),
            model=data.get('model', 'phi3'),
            tools=data.get('tools', [])
        )
        
        # Dispatch webhook
        _webhook_mgr.dispatch('agent.created', {
            'agent_id': agent.id,
            'name': agent.name,
            'user_id': g.user_id
        })
        
        return jsonify({
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "status": agent.status
        })
    
    @app.route('/api/agents', methods=['GET'])
    @require_auth
    def list_agents():
        """List user's agents"""
        agents = runtime.list_agents(user_id=g.user_id)
        return jsonify({
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "role": a.role,
                    "status": a.status,
                    "model": a.model
                }
                for a in agents
            ]
        })
    
    @app.route('/api/agents/<agent_id>', methods=['GET'])
    @require_auth
    def get_agent(agent_id):
        """Get agent details"""
        agent = runtime.get_agent(agent_id)
        if not agent:
            return jsonify({"error": "Not found"}), 404
        
        if agent.user_id != g.user_id:
            return jsonify({"error": "Forbidden"}), 403
        
        return jsonify(runtime.get_agent_status(agent_id))
    
    @app.route('/api/agents/<agent_id>/start', methods=['POST'])
    @require_auth
    def start_agent(agent_id):
        """Start an agent"""
        agent = runtime.get_agent(agent_id)
        if not agent or agent.user_id != g.user_id:
            return jsonify({"error": "Not found"}), 404
        
        data = request.json or {}
        result = runtime.start_agent(agent_id, data.get('message', ''))
        
        # Dispatch webhook
        _webhook_mgr.dispatch('agent.started', {'agent_id': agent_id, 'user_id': g.user_id})
        
        return jsonify(result)
    
    @app.route('/api/agents/<agent_id>/stop', methods=['POST'])
    @require_auth
    def stop_agent(agent_id):
        """Stop an agent"""
        agent = runtime.get_agent(agent_id)
        if not agent or agent.user_id != g.user_id:
            return jsonify({"error": "Not found"}), 404
        
        result = runtime.stop_agent(agent_id)
        
        # Dispatch webhook
        _webhook_mgr.dispatch('agent.stopped', {'agent_id': agent_id, 'user_id': g.user_id})
        
        return jsonify(result)
    
    @app.route('/api/agents/<agent_id>/pause', methods=['POST'])
    @require_auth
    def pause_agent(agent_id):
        """Pause an agent"""
        agent = runtime.get_agent(agent_id)
        if not agent or agent.user_id != g.user_id:
            return jsonify({"error": "Not found"}), 404
        
        result = runtime.pause_agent(agent_id)
        
        # Dispatch webhook
        _webhook_mgr.dispatch('agent.paused', {'agent_id': agent_id, 'user_id': g.user_id})
        
        return jsonify(result)
    
    @app.route('/api/agents/<agent_id>/resume', methods=['POST'])
    @require_auth
    def resume_agent(agent_id):
        """Resume an agent"""
        agent = runtime.get_agent(agent_id)
        if not agent or agent.user_id != g.user_id:
            return jsonify({"error": "Not found"}), 404
        
        return jsonify(runtime.resume_agent(agent_id))
    
    @app.route('/api/agents/<agent_id>', methods=['DELETE'])
    @require_auth
    def delete_agent(agent_id):
        """Delete an agent"""
        agent = runtime.get_agent(agent_id)
        if not agent or agent.user_id != g.user_id:
            return jsonify({"error": "Not found"}), 404
        
        return jsonify(runtime.delete_agent(agent_id))
    
    # ===== Agent Execution Endpoint =====
    
    @app.route('/api/agents/<agent_id>/execute', methods=['POST'])
    @require_auth
    def execute_agent(agent_id):
        """Execute an agent with a message"""
        if not EXECUTOR_AVAILABLE:
            return jsonify({"error": "Agent executor not available"}), 500
        
        agent = runtime.get_agent(agent_id)
        if not agent or agent.user_id != g.user_id:
            return jsonify({"error": "Not found"}), 404
        
        data = request.json or {}
        message = data.get('message', '')
        
        if not message:
            return jsonify({"error": "Message required"}), 400
        
        # Get cached executor for this user (memory persists!)
        executor = get_user_executor(g.user_id)
        
        # Run the agent
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(
                executor.execute(
                    agent_id=agent_id,
                    user_id=g.user_id,  # Pass actual user_id for Inner Life
                    message=message,
                    system_prompt=agent.system_prompt or "You are a helpful AI assistant.",
                    model=agent.model or "llama3",
                    tools=agent.tools
                )
            )
            loop.close()
            
            return jsonify({
                "success": response.success,
                "content": response.content,
                "error": response.error,
                "execution_time_ms": response.execution_time_ms
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return app
