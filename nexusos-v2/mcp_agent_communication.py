"""
MCP Agent Communication Tools
Tools for multi-agent workflows and communication
"""
import json
import time
import uuid
from typing import Dict, List, Any, Optional
import redis
import os


class AgentCommunication:
    """
    Message bus and agent communication system
    """
    
    def __init__(self, redis_url: str = None):
        self.redis = redis.from_url(redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        self.channels_key = "agent:channels"
        self.messages_key = "agent:messages:"
    
    def create_channel(
        self, 
        name: str, 
        description: str = "",
        members: List[str] = None
    ) -> Dict:
        """
        Create a communication channel
        """
        channel_id = f"ch_{uuid.uuid4().hex[:8]}"
        
        channel = {
            "id": channel_id,
            "name": name,
            "description": description,
            "members": members or [],
            "created_at": time.time(),
            "created_by": "system"
        }
        
        # Store channel
        self.redis.hset(
            self.channels_key,
            channel_id,
            json.dumps(channel)
        )
        
        # Create member set
        if members:
            member_key = f"agent:channel:{channel_id}:members"
            for m in members:
                self.redis.sadd(member_key, m)
        
        return {"success": True, "channel_id": channel_id}
    
    def list_channels(self, agent_id: str = None) -> List[Dict]:
        """
        List all channels, optionally filtered by membership
        """
        channels = []
        
        for channel_id in self.redis.hkeys(self.channels_key):
            channel = json.loads(self.redis.hget(self.channels_key, channel_id))
            
            if agent_id:
                # Check membership
                member_key = f"agent:channel:{channel_id}:members"
                if not self.redis.sismember(member_key, agent_id):
                    continue
            
            channels.append(channel)
        
        return channels
    
    def send_message(
        self,
        channel_id: str,
        sender_id: str,
        content: str,
        message_type: str = "text",
        metadata: Dict = None
    ) -> Dict:
        """
        Send a message to a channel
        """
        # Verify channel exists
        channel = self.redis.hget(self.channels_key, channel_id)
        if not channel:
            return {"success": False, "error": "Channel not found"}
        
        message = {
            "id": f"msg_{uuid.uuid4().hex[:12]}",
            "channel_id": channel_id,
            "sender_id": sender_id,
            "content": content,
            "type": message_type,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        
        # Store message
        msg_key = f"{self.messages_key}{channel_id}"
        self.redis.zadd(msg_key, {json.dumps(message): time.time()})
        
        # Set TTL (30 days)
        self.redis.expire(msg_key, 30 * 86400)
        
        # Publish to channel for real-time delivery
        self.redis.publish(f"agent:channel:{channel_id}", json.dumps(message))
        
        return {"success": True, "message_id": message["id"]}
    
    def receive_messages(
        self,
        channel_id: str,
        since: float = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Receive messages from a channel
        """
        msg_key = f"{self.messages_key}{channel_id}"
        
        if since:
            messages = self.redis.zrangebyscore(msg_key, since, "+inf")
        else:
            messages = self.redis.zrevrange(msg_key, 0, limit - 1)
        
        return [json.loads(m) for m in messages]
    
    def subscribe_channel(self, agent_id: str, channel_id: str) -> Dict:
        """Subscribe an agent to a channel"""
        # Verify channel exists
        channel = self.redis.hget(self.channels_key, channel_id)
        if not channel:
            return {"success": False, "error": "Channel not found"}
        
        member_key = f"agent:channel:{channel_id}:members"
        self.redis.sadd(member_key, agent_id)
        
        return {"success": True}
    
    def unsubscribe_channel(self, agent_id: str, channel_id: str) -> Dict:
        """Unsubscribe an agent from a channel"""
        member_key = f"agent:channel:{channel_id}:members"
        self.redis.srem(member_key, agent_id)
        
        return {"success": True}
    
    def list_agents(self) -> List[Dict]:
        """
        List all active agents in the system
        """
        # Get from Redis set
        agents_key = "agent:all:agents"
        
        # This would be populated by agent runtime
        # For now, return empty list
        return []
    
    def agent_status(self, agent_id: str) -> Dict:
        """
        Get status of a specific agent
        """
        status_key = f"agent:status:{agent_id}"
        status = self.redis.get(status_key)
        
        if status:
            return json.loads(status)
        
        return {
            "agent_id": agent_id,
            "status": "unknown",
            "last_seen": None
        }
    
    def broadcast(
        self,
        sender_id: str,
        content: str,
        target_agents: List[str] = None
    ) -> Dict:
        """
        Broadcast a message to all agents or specific agents
        """
        if target_agents:
            # Send to specific agents
            for agent_id in target_agents:
                self.send_message(
                    channel_id=f"direct:{agent_id}",
                    sender_id=sender_id,
                    content=content,
                    message_type="broadcast"
                )
        else:
            # Broadcast to global channel
            self.send_message(
                channel_id="global",
                sender_id=sender_id,
                content=content,
                message_type="broadcast"
            )
        
        return {"success": True}


# Global instance
_comm = None

def get_communication() -> AgentCommunication:
    global _comm
    if _comm is None:
        _comm = AgentCommunication()
    return _comm


# MCP Tool Functions

def agent_create_channel(name: str, description: str = "", members: List[str] = None, **kwargs) -> Dict:
    """Create a communication channel"""
    return get_communication().create_channel(name, description, members)

def agent_list_channels(agent_id: str = None, **kwargs) -> Dict:
    """List available channels"""
    return {"channels": get_communication().list_channels(agent_id)}

def agent_send_message(channel_id: str, sender_id: str, content: str, **kwargs) -> Dict:
    """Send a message to a channel"""
    return get_communication().send_message(channel_id, sender_id, content)

def agent_receive_messages(channel_id: str, since: float = None, limit: int = 50, **kwargs) -> Dict:
    """Receive messages from a channel"""
    return {"messages": get_communication().receive_messages(channel_id, since, limit)}

def agent_subscribe(agent_id: str, channel_id: str, **kwargs) -> Dict:
    """Subscribe to a channel"""
    return get_communication().subscribe_channel(agent_id, channel_id)

def agent_list(**kwargs) -> Dict:
    """List all agents"""
    return {"agents": get_communication().list_agents()}

def agent_status(agent_id: str, **kwargs) -> Dict:
    """Get agent status"""
    return get_communication().agent_status(agent_id)

def agent_broadcast(sender_id: str, content: str, target_agents: List[str] = None, **kwargs) -> Dict:
    """Broadcast to agents"""
    return get_communication().broadcast(sender_id, content, target_agents)
