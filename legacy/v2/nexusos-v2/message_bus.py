"""
Inter-Agent Communication Module for NexusOS

Provides:
- Message Bus: Pub/sub for agent events
- Agent Coordination: Request/response between agents
- Shared Context: Cross-agent memory sharing

Design:
- Uses Redis for pub/sub (when available)
- Falls back to in-memory for local-only mode
- Supports both synchronous (request-response) and async (fire-and-forget) messaging
"""

import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading

# Try to import Redis, fallback to in-memory
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class MessageType(Enum):
    """Types of inter-agent messages"""
    REQUEST = "request"           # Agent asks another agent to do something
    RESPONSE = "response"         # Response to a request
    EVENT = "event"               # Fire-and-forget event
    BROADCAST = "broadcast"       # Message to all agents
    HANDOFF = "handoff"          # Transfer context to another agent


class MessagePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentMessage:
    """Structured inter-agent message"""
    id: str
    msg_type: str
    from_agent: str
    to_agent: Optional[str]  # None for broadcast
    channel: Optional[str]   # For pub/sub
    payload: Dict[str, Any]
    priority: int
    correlation_id: Optional[str]  # For request/response matching
    timestamp: str
    expires_at: Optional[str] = None
    metadata: Optional[Dict] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, data: str) -> 'AgentMessage':
        return cls(**json.loads(data))


class MessageBus:
    """
    Central message bus for inter-agent communication.
    
    Supports:
    - Pub/Sub channels
    - Request-Response patterns
    - Event broadcasting
    - Message persistence (optional)
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self.redis_client = None
        self._pubsub = None
        self._subscriptions: Dict[str, Callable] = {}
        self._pending_requests: Dict[str, threading.Event] = {}
        self._response_cache: Dict[str, Any] = {}
        self._local_messages: List[AgentMessage] = []
        self._lock = threading.Lock()
        
        # Initialize Redis if available
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                self._use_redis = True
                print("[MessageBus] Using Redis backend")
            except Exception as e:
                print(f"[MessageBus] Redis connection failed: {e}, using in-memory")
                self._use_redis = False
        else:
            self._use_redis = False
            print("[MessageBus] Using in-memory backend")
    
    def publish(self, channel: str, message: AgentMessage) -> bool:
        """Publish message to a channel"""
        try:
            if self._use_redis and self.redis_client:
                self.redis_client.publish(channel, message.to_json())
            else:
                # In-memory: store in local messages
                with self._lock:
                    self._local_messages.append(message)
            return True
        except Exception as e:
            print(f"[MessageBus] Publish error: {e}")
            return False
    
    def subscribe(self, channel: str, callback: Callable[[AgentMessage], None]) -> str:
        """Subscribe to a channel. Returns subscription ID."""
        sub_id = str(uuid.uuid4())
        self._subscriptions[sub_id] = {'channel': channel, 'callback': callback}
        
        if self._use_redis and self.redis_client and not self._pubsub:
            # Start pubsub listener in background
            self._start_pubsub_listener()
        
        return sub_id
    
    def unsubscribe(self, sub_id: str):
        """Unsubscribe from a channel"""
        if sub_id in self._subscriptions:
            del self._subscriptions[sub_id]
    
    def _start_pubsub_listener(self):
        """Start background listener for Redis pubsub"""
        if self._pubsub:
            return
        
        self._pubsub = self.redis_client.pubsub()
        # Will be started when needed
    
    def request(self, to_agent: str, payload: Dict, 
                from_agent: str = "system",
                timeout: float = 30.0) -> Optional[Dict]:
        """
        Send a request to another agent and wait for response.
        Implements request-response pattern with correlation ID.
        """
        correlation_id = str(uuid.uuid4())
        
        # Create request message
        message = AgentMessage(
            id=str(uuid.uuid4()),
            msg_type=MessageType.REQUEST.value,
            from_agent=from_agent,
            to_agent=to_agent,
            channel=f"agent.{to_agent}",
            payload=payload,
            priority=MessagePriority.NORMAL.value,
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Create response event
        event = threading.Event()
        with self._lock:
            self._pending_requests[correlation_id] = event
        
        # Publish request
        self.publish(f"agent.{to_agent}", message)
        
        # Wait for response
        if event.wait(timeout=timeout):
            with self._lock:
                response = self._response_cache.pop(correlation_id, None)
            return response
        else:
            # Timeout
            with self._lock:
                self._pending_requests.pop(correlation_id, None)
            return None
    
    def respond(self, to_agent: str, correlation_id: str, payload: Dict, 
                from_agent: str = "system"):
        """Send response to a previous request"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            msg_type=MessageType.RESPONSE.value,
            from_agent=from_agent,
            to_agent=to_agent,
            channel=f"agent.{to_agent}",
            payload=payload,
            priority=MessagePriority.NORMAL.value,
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Store response for the requestor
        with self._lock:
            self._response_cache[correlation_id] = payload
        
        # Wake up waiting thread
        event = self._pending_requests.pop(correlation_id, None)
        if event:
            event.set()
        
        self.publish(f"agent.{from_agent}", message)
    
    def broadcast(self, event_type: str, payload: Dict, from_agent: str = "system"):
        """Broadcast event to all agents"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            msg_type=MessageType.BROADCAST.value,
            from_agent=from_agent,
            to_agent=None,
            channel="broadcast",
            payload={'event_type': event_type, **payload},
            priority=MessagePriority.NORMAL.value,
            timestamp=datetime.utcnow().isoformat()
        )
        self.publish("broadcast", message)
    
    def handoff(self, from_agent: str, to_agent: str, context: Dict):
        """Hand off context/context to another agent"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            msg_type=MessageType.HANDOFF.value,
            from_agent=from_agent,
            to_agent=to_agent,
            channel=f"agent.{to_agent}",
            payload=context,
            priority=MessagePriority.HIGH.value,
            timestamp=datetime.utcnow().isoformat()
        )
        self.publish(f"agent.{to_agent}", message)
    
    def get_messages(self, channel: str, since: Optional[str] = None) -> List[AgentMessage]:
        """Get messages for a channel (for persistence/recovery)"""
        if self._use_redis and self.redis_client:
            # Would need Redis streams for this
            pass
        
        with self._lock:
            messages = [m for m in self._local_messages 
                       if m.channel == channel]
            if since:
                messages = [m for m in messages if m.timestamp >= since]
            return messages


# Global message bus instance
_message_bus: Optional[MessageBus] = None


def get_message_bus(redis_url: Optional[str] = None) -> MessageBus:
    """Get or create the global message bus"""
    global _message_bus
    if _message_bus is None:
        _message_bus = MessageBus(redis_url)
    return _message_bus


# ==================== AGENT COORDINATION ====================

class AgentCoordinator:
    """
    High-level coordination between agents.
    Handles agent discovery, task delegation, and shared state.
    """
    
    def __init__(self, message_bus: MessageBus):
        self.bus = message_bus
        self._agents: Dict[str, Dict] = {}
        self._shared_state: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register_agent(self, agent_id: str, capabilities: List[str], metadata: Dict = None):
        """Register an agent with the coordinator"""
        with self._lock:
            self._agents[agent_id] = {
                'capabilities': capabilities,
                'metadata': metadata or {},
                'registered_at': datetime.utcnow().isoformat(),
                'status': 'idle'
            }
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        with self._lock:
            self._agents.pop(agent_id, None)
    
    def find_agent(self, capability: str) -> Optional[str]:
        """Find an agent that can perform a capability"""
        with self._lock:
            for agent_id, info in self._agents.items():
                if capability in info['capabilities']:
                    return agent_id
        return None
    
    def delegate_task(self, from_agent: str, capability: str, payload: Dict, 
                      timeout: float = 30.0) -> Optional[Dict]:
        """Delegate a task to an agent with the required capability"""
        target = self.find_agent(capability)
        if not target:
            return {'error': f'No agent found with capability: {capability}'}
        
        # Update status
        with self._lock:
            if target in self._agents:
                self._agents[target]['status'] = 'working'
        
        try:
            result = self.bus.request(target, payload, from_agent=from_agent, timeout=timeout)
            return result
        finally:
            with self._lock:
                if target in self._agents:
                    self._agents[target]['status'] = 'idle'
    
    def set_shared_value(self, key: str, value: Any):
        """Set a shared value accessible by all agents"""
        with self._lock:
            self._shared_state[key] = {
                'value': value,
                'updated_at': datetime.utcnow().isoformat(),
                'updated_by': 'system'
            }
    
    def get_shared_value(self, key: str) -> Any:
        """Get a shared value"""
        with self._lock:
            entry = self._shared_state.get(key)
            return entry['value'] if entry else None
    
    def list_agents(self) -> List[Dict]:
        """List all registered agents"""
        with self._lock:
            return list(self._agents.values())


# Flask routes for message bus API
def setup_message_bus_routes(app, message_bus: MessageBus, coordinator: AgentCoordinator):
    """Add message bus routes to Flask app"""
    from flask import request, jsonify
    
    @app.route('/api/messages/publish', methods=['POST'])
    def publish_message():
        """Publish a message to a channel"""
        data = request.json or {}
        channel = data.get('channel')
        msg_type = data.get('type', 'event')
        
        if not channel:
            return jsonify({'error': 'channel required'}), 400
        
        message = AgentMessage(
            id=str(uuid.uuid4()),
            msg_type=msg_type,
            from_agent=data.get('from_agent', 'api'),
            to_agent=data.get('to_agent'),
            channel=channel,
            payload=data.get('payload', {}),
            priority=data.get('priority', 2),
            timestamp=datetime.utcnow().isoformat()
        )
        
        success = message_bus.publish(channel, message)
        return jsonify({'success': success, 'message_id': message.id})
    
    @app.route('/api/messages/channels', methods=['GET'])
    def list_channels():
        """List active channels"""
        # In production, track active channels
        return jsonify({'channels': ['broadcast', 'agent.*']})
    
    @app.route('/api/messages/<channel>', methods=['GET'])
    def get_channel_messages(channel):
        """Get messages for a channel"""
        since = request.args.get('since')
        messages = message_bus.get_messages(channel, since)
        return jsonify({
            'messages': [asdict(m) for m in messages[-50:]]  # Last 50
        })
    
    @app.route('/api/agents/delegate', methods=['POST'])
    def delegate_task():
        """Delegate a task to an agent"""
        data = request.json or {}
        capability = data.get('capability')
        payload = data.get('payload', {})
        from_agent = data.get('from_agent', 'api')
        
        if not capability:
            return jsonify({'error': 'capability required'}), 400
        
        result = coordinator.delegate_task(from_agent, capability, payload)
        return jsonify(result or {'error': 'timeout'})
    
    @app.route('/api/agents', methods=['GET'])
    def list_registered_agents():
        """List all registered agents"""
        return jsonify({'agents': coordinator.list_agents()})
    
    @app.route('/api/agents/<agent_id>', methods=['POST'])
    def register_agent(agent_id):
        """Register an agent"""
        data = request.json or {}
        coordinator.register_agent(
            agent_id,
            data.get('capabilities', []),
            data.get('metadata', {})
        )
        return jsonify({'status': 'registered'})
    
    @app.route('/api/shared/<key>', methods=['GET', 'PUT', 'DELETE'])
    def shared_state(key):
        """Access shared state"""
        if request.method == 'GET':
            value = coordinator.get_shared_value(key)
            return jsonify({'key': key, 'value': value})
        elif request.method == 'PUT':
            data = request.json or {}
            coordinator.set_shared_value(key, data.get('value'))
            return jsonify({'status': 'set'})
        else:
            with coordinator._lock:
                coordinator._shared_state.pop(key, None)
            return jsonify({'status': 'deleted'})
