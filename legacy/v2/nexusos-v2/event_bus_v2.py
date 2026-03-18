"""
NexusOS v2 - Persistent Event Bus

Replaces in-memory event bus with database-persisted events.
Supports async processing and event replay.
"""

import os
import sys
import json
import queue
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    IDLE = 5


class EventType(Enum):
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_SHUTDOWN = "system_shutdown"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_IDLE = "cpu_idle"
    CPU_BUSY = "cpu_busy"
    
    # User events
    USER_ACTIVE = "user_active"
    USER_AWAY = "user_away"
    USER_INPUT = "user_input"
    
    # Network events
    NETWORK_ONLINE = "network_online"
    NETWORK_OFFLINE = "network_offline"
    
    # File events
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    
    # Time events
    EVERY_MINUTE = "every_minute"
    EVERY_HOUR = "every_hour"
    EVERY_DAY = "every_day"
    IDLE_DETECTED = "idle_detected"
    
    # Agent events
    AGENT_THINKING = "agent_thinking"
    AGENT_ACTING = "agent_acting"
    AGENT_WAITING = "agent_waiting"
    AGENT_ERROR = "agent_error"
    AGENT_MESSAGE = "agent_message"
    
    # Memory events
    MEMORY_STORED = "memory_stored"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_COMPACTED = "memory_compacted"
    
    # Tool events
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_ERROR = "tool_error"


class PersistentEventBus:
    """
    Database-persistent event bus with async processing.
    
    Key improvements over v1:
    - Events persisted to database (survive restart)
    - Async processing with thread pool
    - Event replay capability
    - Event sourcing support
    """
    
    def __init__(self, db_path: str = None):
        self.db = get_db(db_path)
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_queue = queue.PriorityQueue()
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.handlers_thread = None
        
        # State tracking
        self.state: Dict[str, Any] = {
            "cpu_idle": False,
            "user_active": True,
            "network_online": True,
            "last_user_activity": time.time(),
            "events_handled": 0,
        }
        
    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {event_type}")
    
    def subscribe_multiple(self, event_types: List[str], handler: Callable):
        """Subscribe to multiple event types."""
        for event_type in event_types:
            self.subscribe(event_type, handler)
    
    def emit(self, event_type: str, data: Dict = None, priority: EventPriority = EventPriority.NORMAL, 
             source: str = "system"):
        """Emit event - persists to database and queues for processing."""
        # Persist to database
        self.db.persist_event(event_type, priority.value, source, data)
        
        # Create event object
        event = {
            "event_type": event_type,
            "priority": priority.value,
            "data": data or {},
            "source": source,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Add to queue
        self.event_queue.put((priority.value, time.time(), event))
        
        logger.debug(f"Event emitted: {event_type}")
    
    def emit_simple(self, event_type: str, **kwargs):
        """Convenience method for emitting events."""
        self.emit(event_type, data=kwargs.get('data'), 
                  priority=kwargs.get('priority', EventPriority.NORMAL),
                  source=kwargs.get('source', 'system'))
    
    def start(self):
        """Start the event bus."""
        self.running = True
        self.handlers_thread = threading.Thread(target=self._process_events, daemon=True)
        self.handlers_thread.start()
        self.emit(EventType.SYSTEM_START.value)
        logger.info("PersistentEventBus started")
    
    def stop(self):
        """Stop the event bus."""
        self.emit(EventType.SYSTEM_SHUTDOWN.value)
        self.running = False
        self.executor.shutdown(wait=True)
        if self.handlers_thread:
            self.handlers_thread.join(timeout=5)
        logger.info("PersistentEventBus stopped")
    
    def _process_events(self):
        """Process events from the queue asynchronously."""
        while self.running:
            try:
                priority, enqueue_time, event = self.event_queue.get(timeout=1)
                
                # Submit to thread pool
                future = self.executor.submit(self._handle_event, event)
                
                self.event_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")
    
    def _handle_event(self, event: Dict):
        """Handle a single event - call all subscribers."""
        event_type = event.get("event_type")
        
        # Get handlers
        handlers = self.subscribers.get(event_type, [])
        all_handlers = self.subscribers.get("*", []) + handlers
        
        # Execute handlers
        for handler in all_handlers:
            try:
                handler(event)
                self.state["events_handled"] += 1
            except Exception as e:
                logger.error(f"Handler error in {handler.__name__}: {e}")
    
    def replay_events(self, from_timestamp: str = None, event_type: str = None):
        """Replay events from database."""
        events = self.db.get_events(event_type, limit=1000)
        
        if from_timestamp:
            events = [e for e in events if e.get('created_at', '') > from_timestamp]
        
        logger.info(f"Replaying {len(events)} events")
        
        for event in events:
            self._handle_event({
                "event_type": event.get('event_type'),
                "priority": event.get('priority', 3),
                "data": json.loads(event.get('data', '{}')),
                "source": event.get('source'),
                "timestamp": event.get('created_at'),
            })
    
    def get_state(self) -> Dict:
        """Get current system state."""
        idle_time = time.time() - self.state.get("last_user_activity", time.time())
        self.state["idle_seconds"] = idle_time
        self.state["cpu_idle"] = idle_time > 60
        return self.state.copy()
    
    def get_recent_events(self, count: int = 100) -> List[Dict]:
        """Get recent events from database."""
        return self.db.get_events(limit=count)


# Global instance
_event_bus = None

def get_event_bus(db_path: str = None) -> PersistentEventBus:
    """Get event bus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = PersistentEventBus(db_path)
    return _event_bus

def init_event_bus(db_path: str = None) -> PersistentEventBus:
    """Initialize event bus."""
    global _event_bus
    _event_bus = PersistentEventBus(db_path)
    return _event_bus
