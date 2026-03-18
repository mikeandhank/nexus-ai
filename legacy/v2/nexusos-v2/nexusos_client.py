"""
NexusOS Python Client Library
==============================
A simple client for interacting with NexusOS Enterprise APIs.

Usage:
    from nexusos_client import NexusOSClient
    
    client = NexusOSClient("http://187.124.150.225:8080", api_key="your-key")
    
    # Webhooks
    client.register_webhook("chat.message", "https://your-callback.com/hook")
    webhooks = client.list_webhooks()
    
    # Usage Analytics
    usage = client.get_usage(days=7)
    print(f"Total cost: ${usage['summary']['total_cost_usd']}")
"""
import requests
import json
from typing import Dict, List, Optional, Any


class NexusOSClient:
    """Python client for NexusOS Enterprise APIs"""
    
    def __init__(self, base_url: str, api_key: str = None, timeout: int = 30):
        """
        Initialize NexusOS client
        
        Args:
            base_url: Base URL of NexusOS server (e.g., http://localhost:8080)
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make HTTP request to NexusOS API"""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('headers', {}).setdefault('Content-Type', 'application/json')
        
        if self.api_key:
            kwargs['headers']['Authorization'] = f'Bearer {self.api_key}'
        
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    # ==================== HEALTH & STATUS ====================
    
    def status(self) -> Dict:
        """Get system status"""
        return self._request('GET', '/api/status')
    
    # ==================== WEBHOOKS ====================
    
    def register_webhook(
        self, 
        event_type: str, 
        url: str, 
        secret: str = None
    ) -> Dict:
        """
        Register a webhook for an event type
        
        Args:
            event_type: Event to listen for (e.g., "chat.message", "agent.started")
            url: Callback URL to receive the webhook
            secret: Optional secret for signature verification
        
        Returns:
            Webhook registration details including ID
        """
        data = {
            'event_type': event_type,
            'url': url,
        }
        if secret:
            data['secret'] = secret
        
        return self._request('POST', '/api/webhooks/register', json=data)
    
    def list_webhooks(self) -> List[Dict]:
        """List all registered webhooks"""
        return self._request('GET', '/api/webhooks')
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook by ID"""
        self._request('DELETE', f'/api/webhooks/{webhook_id}')
        return True
    
    def test_webhook(self, webhook_id: str = None) -> Dict:
        """Test webhook delivery (optionally for specific webhook)"""
        data = {}
        if webhook_id:
            data['webhook_id'] = webhook_id
        return self._request('POST', '/api/webhooks/test', json=data)
    
    # ==================== USAGE ANALYTICS ====================
    
    def get_usage(self, days: int = 7, user_id: str = None) -> Dict:
        """
        Get usage statistics
        
        Args:
            days: Number of days to look back
            user_id: Optional user ID to filter by
        
        Returns:
            Usage summary and daily breakdown
        """
        params = {'days': days}
        if user_id:
            params['user_id'] = user_id
        return self._request('GET', '/api/usage', params=params)
    
    def get_usage_summary(self) -> Dict:
        """Get total usage summary all-time"""
        return self._request('GET', '/api/usage/summary')
    
    def get_user_usage(self, user_id: str, days: int = 30) -> Dict:
        """Get usage for a specific user"""
        return self._request('GET', f'/api/usage/user/{user_id}', params={'days': days})
    
    def track_usage(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: str = "openai"
    ) -> Dict:
        """
        Track a usage event
        
        Args:
            user_id: User who made the request
            model: Model used (e.g., "gpt-4o")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: LLM provider name
        
        Returns:
            Success status and estimated cost
        """
        data = {
            'user_id': user_id,
            'model': model,
            'provider': provider,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
        }
        return self._request('POST', '/api/usage/track', json=data)
    
    # ==================== AGENTS ====================
    
    def get_agent_stats(self) -> Dict:
        """Get agent activity statistics"""
        return self._request('GET', '/api/agents/stats')
    
    def list_agents(self) -> List[Dict]:
        """List all agents"""
        return self._request('GET', '/api/agents')
    
    def get_agent(self, agent_id: str) -> Dict:
        """Get details of a specific agent"""
        return self._request('GET', f'/api/agents/{agent_id}')
    
    def create_agent(self, name: str, model: str = None, tools: List[str] = None) -> Dict:
        """Create a new agent"""
        data = {'name': name}
        if model:
            data['model'] = model
        if tools:
            data['tools'] = tools
        return self._request('POST', '/api/agents', json=data)
    
    def pause_agent(self, agent_id: str) -> Dict:
        """Pause an agent"""
        return self._request('POST', f'/api/agents/{agent_id}/pause')
    
    def resume_agent(self, agent_id: str) -> Dict:
        """Resume a paused agent"""
        return self._request('POST', f'/api/agents/{agent_id}/resume')
    
    def stop_agent(self, agent_id: str) -> Dict:
        """Stop an agent"""
        return self._request('POST', f'/api/agents/{agent_id}/stop')
    
    # ==================== CHAT ====================
    
    def chat(self, message: str, user_id: str = None, agent_id: str = None) -> Dict:
        """Send a chat message"""
        data = {'message': message}
        if user_id:
            data['user_id'] = user_id
        if agent_id:
            data['agent_id'] = agent_id
        return self._request('POST', '/api/chat', json=data)


# ==================== CONVENIENCE FUNCTIONS ====================

def quick_test(base_url: str = "http://localhost:8080", api_key: str = None) -> bool:
    """
    Quick connectivity test
    
    Returns True if system is reachable, False otherwise
    """
    try:
        client = NexusOSClient(base_url, api_key)
        status = client.status()
        return status.get('running', False)
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    
    # Simple CLI for testing
    if len(sys.argv) < 2:
        print("Usage: python nexusos_client.py <base_url> [api_key]")
        sys.exit(1)
    
    base_url = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    client = NexusOSClient(base_url, api_key)
    
    print("Testing NexusOS connection...")
    try:
        status = client.status()
        print(f"✓ Connected! Version: {status.get('version', 'unknown')}")
        print(f"  Running: {status.get('running')}")
        print(f"  Enterprise: {status.get('enterprise')}")
        print(f"  Providers: {status.get('tiers', {}).get('pro', {}).get('providers', [])}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)