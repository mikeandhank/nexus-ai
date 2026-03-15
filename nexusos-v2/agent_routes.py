"""
Agent Management API Routes
"""
from flask import jsonify, request, g
from auth import require_auth
from agent_runtime import get_agent_runtime
from webhooks import get_webhook_manager
from database_compat import Database

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
    
    return app
