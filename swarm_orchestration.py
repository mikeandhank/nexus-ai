"""
Swarm Orchestration - Multi-Agent Federated System
"""

import uuid
import asyncio
from datetime import datetime
from flask import jsonify, request

# In-memory swarm registry (would be DB in production)
SWARMS = {}

class SwarmAgent:
    def __init__(self, agent_id, role, capabilities):
        self.id = agent_id
        self.role = role  # researcher, synthesizer, validator, executor
        self.capabilities = capabilities
        self.status = 'idle'

class Swarm:
    def __init__(self, name, description):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.agents = []
        self.created_at = datetime.utcnow()
        self.status = 'created'
    
    def add_agent(self, agent):
        self.agents.append(agent)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'agents': [{'id': a.id, 'role': a.role, 'capabilities': a.capabilities} for a in self.agents],
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

def create_swarm_routes(app, require_nexus_key):
    """Register swarm routes with Flask app"""
    
    @app.route('/api/swarm/create', methods=['POST'])
    @require_nexus_key
    def create_swarm():
        """Create a new swarm of agents"""
        data = request.get_json()
        
        swarm = Swarm(
            name=data.get('name', 'Unnamed Swarm'),
            description=data.get('description', '')
        )
        
        # Add agents to swarm
        for agent_spec in data.get('agents', []):
            agent = SwarmAgent(
                agent_id=agent_spec.get('id', str(uuid.uuid4())),
                role=agent_spec.get('role', 'worker'),
                capabilities=agent_spec.get('capabilities', [])
            )
            swarm.add_agent(agent)
        
        SWARMS[swarm.id] = swarm
        
        return jsonify({
            'swarm': swarm.to_dict(),
            'message': f'Swarm "{swarm.name}" created with {len(swarm.agents)} agents'
        })
    
    @app.route('/api/swarm/<swarm_id>/execute', methods=['POST'])
    @require_nexus_key
    def swarm_execute(swarm_id):
        """Execute task across swarm - parallel execution with result aggregation"""
        if swarm_id not in SWARMS:
            return jsonify({'error': 'Swarm not found'}), 404
        
        swarm = SWARMS[swarm_id]
        task = request.get_json().get('task', '')
        
        # Execute each agent in parallel (simulated)
        results = []
        for agent in swarm.agents:
            # In real implementation, this calls each agent's executor
            results.append({
                'agent_id': agent.id,
                'role': agent.role,
                'status': 'completed',
                'output': f'[Simulated] {agent.role} processed: {task[:50]}...'
            })
        
        # Synthesize results
        synthesis = {
            'swarm_id': swarm_id,
            'task': task,
            'agent_results': results,
            'synthesized': f'Aggregated {len(results)} agent outputs',
            'executed_at': datetime.utcnow().isoformat()
        }
        
        return jsonify(synthesis)
    
    @app.route('/api/swarm/<swarm_id>/handoff', methods=['POST'])
    @require_nexus_key
    def swarm_handoff(swarm_id):
        """Hand off from one agent to another in the swarm"""
        if swarm_id not in SWARMS:
            return jsonify({'error': 'Swarm not found'}), 404
        
        data = request.get_json()
        from_agent = data.get('from_agent')
        to_agent = data.get('to_agent')
        payload = data.get('payload', {})
        
        return jsonify({
            'status': 'handed_off',
            'from': from_agent,
            'to': to_agent,
            'payload_size': len(payload),
            'message': f'Results handed from {from_agent} to {to_agent}'
        })
    
    @app.route('/api/swarm', methods=['GET'])
    @require_nexus_key
    def list_swarms():
        """List all swarms"""
        return jsonify({
            'swarms': [s.to_dict() for s in SWARMS.values()]
        })
    
    @app.route('/api/swarm/<swarm_id>', methods=['GET'])
    @require_nexus_key
    def get_swarm(swarm_id):
        """Get swarm details"""
        if swarm_id not in SWARMS:
            return jsonify({'error': 'Swarm not found'}), 404
        return jsonify(SWARMS[swarm_id].to_dict())
    
    return app
