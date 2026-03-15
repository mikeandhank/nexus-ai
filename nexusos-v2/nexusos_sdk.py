"""
NexusOS Python SDK
Define and deploy agents programmatically.
"""

import requests
import json
from typing import Optional, List, Dict, Any

class NexusOS:
    """Python SDK for NexusOS"""
    
    def __init__(self, api_url: str, api_key: str = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self._session = requests.Session()
        if api_key:
            self._session.headers['Authorization'] = f'Bearer {api_key}'
    
    def status(self) -> Dict:
        """Get system status"""
        return self._get('/api/status')
    
    # ========== AGENTS ==========
    
    def list_agents(self) -> List[Dict]:
        """List all agents"""
        return self._get('/api/agents').get('agents', [])
    
    def get_agent(self, agent_id: str) -> Dict:
        """Get agent details"""
        return self._get(f'/api/agents/{agent_id}')
    
    def create_agent(self, 
                     name: str,
                     description: str = '',
                     model: str = 'phi3',
                     system_prompt: str = '',
                     tools: List[str] = None) -> Dict:
        """Create a new agent"""
        return self._post('/api/agents', {
            'name': name,
            'description': description,
            'model': model,
            'system_prompt': system_prompt,
            'tools': tools or []
        })
    
    def start_agent(self, agent_id: str) -> Dict:
        """Start an agent"""
        return self._post(f'/api/agents/{agent_id}/start', {})
    
    def stop_agent(self, agent_id: str) -> Dict:
        """Stop an agent"""
        return self._post(f'/api/agents/{agent_id}/stop', {})
    
    def delete_agent(self, agent_id: str) -> Dict:
        """Delete an agent"""
        return self._delete(f'/api/agents/{agent_id}')
    
    # ========== CHAT ==========
    
    def chat(self, message: str, agent_id: str = None, user_id: str = 'sdk') -> Dict:
        """Send a chat message"""
        payload = {'message': message, 'user_id': user_id}
        if agent_id:
            payload['agent_id'] = agent_id
        return self._post('/api/chat', payload)
    
    # ========== CONVERSATIONS ==========
    
    def list_conversations(self, user_id: str = None) -> List[Dict]:
        """List conversations"""
        params = {'user_id': user_id} if user_id else {}
        return self._get('/api/conversations', params).get('conversations', [])
    
    def get_conversation(self, conv_id: str) -> Dict:
        """Get conversation messages"""
        return self._get(f'/api/conversations/{conv_id}')
    
    # ========== MEMORY ==========
    
    def remember(self, key: str, value: str) -> Dict:
        """Store a memory"""
        return self._post('/api/memory/remember', {'key': key, 'value': value})
    
    def recall(self, query: str) -> List[Dict]:
        """Recall memories"""
        return self._post('/api/memory/recall', {'query': query}).get('results', [])
    
    # ========== METRICS ==========
    
    def metrics(self) -> Dict:
        """Get system metrics"""
        return self._get('/api/metrics')
    
    def logs(self, limit: int = 10) -> List[Dict]:
        """Get audit logs"""
        return self._get('/api/logs', {'limit': limit}).get('logs', [])
    
    # ========== UTILITY ==========
    
    def _get(self, path: str, params: Dict = None) -> Dict:
        r = self._session.get(f'{self.api_url}{path}', params=params)
        r.raise_for_status()
        return r.json()
    
    def _post(self, path: str, data: Dict) -> Dict:
        r = self._session.post(f'{self.api_url}{path}', json=data)
        r.raise_for_status()
        return r.json()
    
    def _delete(self, path: str) -> Dict:
        r = self._session.delete(f'{self.api_url}{path}')
        r.raise_for_status()
        return r.json()


# ========== AGENT DECORATOR ==========

def agent(name: str, description: str = '', model: str = 'phi3', tools: List[str] = None):
    """Decorator to define an agent"""
    def decorator(func):
        func._nexus_agent = {
            'name': name,
            'description': description,
            'model': model,
            'tools': tools or [],
            'system_prompt': func.__doc__ or ''
        }
        return func
    return decorator


# ========== EXAMPLE USAGE ==========

if __name__ == '__main__':
    # Quick demo
    nexus = NexusOS('http://187.124.150.225:8080')
    
    print("🔗 NexusOS Python SDK Demo")
    print("=" * 40)
    
    # Check status
    status = nexus.status()
    print(f"Status: {status.get('version')} | PostgreSQL: {status['infrastructure']['postgres']} | Redis: {status['infrastructure']['redis']}")
    
    # List agents
    agents = nexus.list_agents()
    print(f"Agents: {len(agents)}")
    
    # Send a test message
    result = nexus.chat("Hello from Python SDK!")
    print(f"Chat: {result.get('response', 'No response')[:80]}...")
