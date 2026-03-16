"""
Inter-Agent Communication (IPC)
================================
True OS-style message passing between agents.
"""

import os
import json
import uuid
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IPCMessageType(Enum):
    """IPC Message Types"""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    SIGNAL = "signal"
    EVENT = "event"


@dataclass
class IPCMessage:
    """Inter-process message"""
    message_id: str
    msg_type: IPCMessageType
    
    # Routing
    from_agent_id: str
    to_agent_id: str  # "*" for broadcast
    
    # Content
    channel: str      # e.g., "data", "control", "events"
    payload: Any
    
    # Metadata
    correlation_id: str = ""  # For request/response matching
    reply_to: str = ""        # Message ID to reply to
    
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: int = 60             # Time to live in seconds
    
    # Status
    delivered: bool = False
    acknowledged: bool = False


@dataclass
class IPCChannel:
    """Named channel for pub/sub"""
    channel_id: str
    name: str
    subscribers: List[str] = field(default_factory=list)
    persistent: bool = False   # Keep messages after delivery


class AgentIPC:
    """
    Inter-Agent Communication System
    
    Features:
    - Direct agent-to-agent messaging
    - Pub/Sub channels
    - Request/Response pattern
    - Broadcast to all agents
    - Signal delivery
    - Message persistence
    """
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.environ.get('DATABASE_URL',
            'postgresql://nexusos:nexusos@localhost:5432/nexusos')
        
        # In-memory message bus
        self.message_queue: Dict[str, IPCMessage] = {}
        self.channels: Dict[str, IPCChannel] = {}
        self.agent_mailboxes: Dict[str, List[IPCMessage]] = defaultdict(list)
        
        # Subscriptions
        self.subscriptions: Dict[str, List[str]] = defaultdict(list)  # agent_id -> [channels]
        
        # Message handlers
        self.handlers: Dict[str, Callable] = {}
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Initialize DB
        self._init_db()
    
    def _init_db(self):
        """Initialize IPC tables"""
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kernel_ipc (
                    message_id TEXT PRIMARY KEY,
                    msg_type TEXT NOT NULL,
                    from_agent_id TEXT NOT NULL,
                    to_agent_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    payload JSONB,
                    correlation_id TEXT,
                    reply_to TEXT,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    ttl INTEGER DEFAULT 60,
                    delivered BOOLEAN DEFAULT FALSE,
                    acknowledged BOOLEAN DEFAULT FALSE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kernel_channels (
                    channel_id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    subscribers JSONB DEFAULT '[]',
                    persistent BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("IPC DB initialized")
        except Exception as e:
            logger.warning(f"IPC DB init failed (using memory): {e}")
    
    # ========== MESSAGE SENDING ==========
    
    def send_message(self, from_agent_id: str, to_agent_id: str,
                    channel: str, payload: Any,
                    msg_type: IPCMessageType = IPCMessageType.REQUEST,
                    correlation_id: str = "",
                    reply_to: str = "") -> IPCMessage:
        """Send a message to an agent"""
        
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        
        message = IPCMessage(
            message_id=message_id,
            msg_type=msg_type,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            channel=channel,
            payload=payload,
            correlation_id=correlation_id or uuid.uuid4().hex,
            reply_to=reply_to
        )
        
        with self._lock:
            self.message_queue[message_id] = message
            
            # Deliver to recipient's mailbox
            if to_agent_id != "*":
                self.agent_mailboxes[to_agent_id].append(message)
            
            # If broadcast, add to all mailboxes
            if to_agent_id == "*":
                self._deliver_broadcast(message)
            
            # Publish to channel
            self._publish_to_channel(channel, message)
        
        # Persist to DB
        self._persist_message(message)
        
        logger.info(f"IPC: {from_agent_id} -> {to_agent_id} [{channel}]")
        
        return message
    
    def send_request(self, from_agent_id: str, to_agent_id: str,
                    channel: str, payload: Any,
                    timeout: int = 30) -> Dict:
        """Send request and wait for response"""
        
        correlation_id = uuid.uuid4().hex
        
        # Send message
        message = self.send_message(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            channel=channel,
            payload=payload,
            msg_type=IPCMessageType.REQUEST,
            correlation_id=correlation_id
        )
        
        # Wait for response
        start = datetime.utcnow()
        while (datetime.utcnow() - start).seconds < timeout:
            with self._lock:
                # Check for response
                for msg in self.agent_mailboxes.get(from_agent_id, []):
                    if (msg.msg_type == IPCMessageType.RESPONSE and 
                        msg.correlation_id == correlation_id):
                        self.agent_mailboxes[from_agent_id].remove(msg)
                        return {
                            "success": True,
                            "response": msg.payload,
                            "message_id": msg.message_id
                        }
            
            import time
            time.sleep(0.1)
        
        return {"success": False, "error": "Timeout waiting for response"}
    
    def broadcast(self, from_agent_id: str, channel: str, payload: Any):
        """Broadcast to all agents"""
        return self.send_message(
            from_agent_id=from_agent_id,
            to_agent_id="*",
            channel=channel,
            payload=payload,
            msg_type=IPCMessageType.BROADCAST
        )
    
    def reply_to(self, from_agent_id: str, original_message: IPCMessage, payload: Any):
        """Send reply to a message"""
        return self.send_message(
            from_agent_id=from_agent_id,
            to_agent_id=original_message.from_agent_id,
            channel=original_message.channel,
            payload=payload,
            msg_type=IPCMessageType.RESPONSE,
            correlation_id=original_message.correlation_id,
            reply_to=original_message.message_id
        )
    
    # ========== CHANNELS (Pub/Sub) ==========
    
    def create_channel(self, name: str, persistent: bool = False) -> IPCChannel:
        """Create a channel"""
        
        channel_id = f"ch_{uuid.uuid4().hex[:12]}"
        
        channel = IPCChannel(
            channel_id=channel_id,
            name=name,
            persistent=persistent
        )
        
        with self._lock:
            self.channels[name] = channel
        
        logger.info(f"Created channel: {name}")
        
        return channel
    
    def subscribe(self, agent_id: str, channel_name: str) -> Dict:
        """Subscribe agent to channel"""
        
        if channel_name not in self.channels:
            return {"success": False, "error": "Channel not found"}
        
        with self._lock:
            channel = self.channels[channel_name]
            if agent_id not in channel.subscribers:
                channel.subscribers.append(agent_id)
            
            self.subscriptions[agent_id].append(channel_name)
        
        return {"success": True}
    
    def unsubscribe(self, agent_id: str, channel_name: str) -> Dict:
        """Unsubscribe from channel"""
        
        with self._lock:
            if channel_name in self.channels:
                channel = self.channels[channel_name]
                if agent_id in channel.subscribers:
                    channel.subscribers.remove(agent_id)
            
            if channel_name in self.subscriptions.get(agent_id, []):
                self.subscriptions[agent_id].remove(channel_name)
        
        return {"success": True}
    
    def _publish_to_channel(self, channel_name: str, message: IPCMessage):
        """Publish message to channel subscribers"""
        
        if channel_name not in self.channels:
            return
        
        channel = self.channels[channel_name]
        
        for subscriber_id in channel.subscribers:
            if subscriber_id != message.from_agent_id:
                self.agent_mailboxes[subscriber_id].append(message)
    
    def _deliver_broadcast(self, message: IPCMessage):
        """Deliver broadcast to all agents"""
        
        for agent_id in self.agent_mailboxes.keys():
            if agent_id != message.from_agent_id:
                self.agent_mailboxes[agent_id].append(message)
    
    # ========== RECEIVING ==========
    
    def receive_message(self, agent_id: str, timeout: int = 0) -> Optional[IPCMessage]:
        """
        Receive message from agent's mailbox.
        
        Args:
            agent_id: Agent to receive for
            timeout: Seconds to wait (0 = non-blocking)
        
        Returns:
            IPCMessage or None
        """
        
        start = datetime.utcnow()
        
        while True:
            with self._lock:
                if self.agent_mailboxes[agent_id]:
                    message = self.agent_mailboxes[agent_id].pop(0)
                    message.delivered = True
                    return message
            
            if timeout <= 0:
                break
            
            if (datetime.utcnow() - start).seconds >= timeout:
                break
            
            import time
            time.sleep(0.1)
        
        return None
    
    def peek_messages(self, agent_id: str, channel: str = None, 
                     limit: int = 10) -> List[IPCMessage]:
        """Peek at messages without removing"""
        
        with self._lock:
            messages = self.agent_mailboxes.get(agent_id, [])
            
            if channel:
                messages = [m for m in messages if m.channel == channel]
            
            return messages[:limit]
    
    def acknowledge_message(self, message_id: str) -> Dict:
        """Acknowledge message receipt"""
        
        with self._lock:
            if message_id in self.message_queue:
                self.message_queue[message_id].acknowledged = True
                return {"success": True}
        
        return {"success": False, "error": "Message not found"}
    
    # ========== QUERY ==========
    
    def get_message(self, message_id: str) -> Optional[IPCMessage]:
        """Get message by ID"""
        return self.message_queue.get(message_id)
    
    def list_channels(self) -> List[Dict]:
        """List all channels"""
        return [
            {
                "name": c.name,
                "subscribers": len(c.subscribers),
                "persistent": c.persistent
            }
            for c in self.channels.values()
        ]
    
    def get_agent_subscriptions(self, agent_id: str) -> List[str]:
        """Get agent's channel subscriptions"""
        return self.subscriptions.get(agent_id, [])
    
    def get_mailbox_stats(self, agent_id: str) -> Dict:
        """Get mailbox statistics"""
        with self._lock:
            messages = self.agent_mailboxes.get(agent_id, [])
            
            by_channel = defaultdict(int)
            by_type = defaultdict(int)
            
            for msg in messages:
                by_channel[msg.channel] += 1
                by_type[msg.msg_type.value] += 1
            
            return {
                "total": len(messages),
                "by_channel": dict(by_channel),
                "by_type": dict(by_type),
                "subscriptions": self.subscriptions.get(agent_id, [])
            }
    
    def get_stats(self) -> Dict:
        """Get IPC statistics"""
        return {
            "total_messages": len(self.message_queue),
            "total_channels": len(self.channels),
            "total_mailboxes": len(self.agent_mailboxes),
            "total_subscriptions": sum(len(s) for s in self.subscriptions.values())
        }
    
    # ========== PERSISTENCE ==========
    
    def _persist_message(self, message: IPCMessage):
        """Persist message to DB"""
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO kernel_ipc 
                (message_id, msg_type, from_agent_id, to_agent_id, channel, 
                 payload, correlation_id, reply_to, ttl, delivered, acknowledged)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                message.message_id,
                message.msg_type.value,
                message.from_agent_id,
                message.to_agent_id,
                message.channel,
                json.dumps(message.payload),
                message.correlation_id,
                message.reply_to,
                message.ttl,
                message.delivered,
                message.acknowledged
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to persist message: {e}")


# Example usage:
#
# # Agent A sends to Agent B
# ipc.send_message("agent_a", "agent_b", "data", {"key": "value"})
#
# # Agent B receives
# msg = ipc.receive_message("agent_b", timeout=30)
#
# # Agent B replies
# ipc.reply_to("agent_b", msg, {"result": "ok"})
#
# # Channel pub/sub
# ipc.create_channel("agent_events")
# ipc.subscribe("agent_a", "agent_events")
# ipc.broadcast("agent_a", "agent_events", {"event": "task_complete"})

# Singleton
_ipc = None

def get_ipc(db_url: str = None) -> AgentIPC:
    global _ipc
    if _ipc is None:
        _ipc = AgentIPC(db_url)
    return _ipc
