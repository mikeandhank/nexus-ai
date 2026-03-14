"""
NexusOS Event-Driven Architecture

This module provides kernel-level event handling for NexusOS,
replacing cron-based polling with real OS-level event detection.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventPriority(Enum):
    CRITICAL = 1  # System shutdown, data loss risk
    HIGH = 2      # User input, important changes
    NORMAL = 3    # Regular events
    LOW = 4       # Background tasks
    IDLE = 5      # Only when system idle


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
    NETWORK_SPEED_CHANGE = "network_speed_change"
    
    # File events (inotify-style)
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    FILE_DIR_CHANGED = "file_dir_changed"
    
    # Time events (smarter than cron)
    EVERY_MINUTE = "every_minute"
    EVERY_HOUR = "every_hour"
    EVERY_DAY = "every_day"
    IDLE_DETECTED = "idle_detected"
    
    # Agent events
    AGENT_THINKING = "agent_thinking"
    AGENT_ACTING = "agent_acting"
    AGENT_WAITING = "agent_waiting"
    AGENT_ERROR = "agent_error"
    
    # Battery/power
    POWER_ON_BATTERY = "power_on_battery"
    POWER_CHARGING = "power_charging"
    POWER_LOW = "power_low"


@dataclass
class NexusEvent:
    """Represents an event in the NexusOS event system."""
    event_type: EventType
    priority: EventPriority = EventPriority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"
    handled: bool = False
    
    def __str__(self):
        return f"[{self.priority.name}] {self.event_type.value} @ {self.timestamp.isoformat()}"


class EventBus:
    """
    Central event bus for NexusOS.
    Replaces cron with event-driven architecture.
    """
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_queue = queue.PriorityQueue()
        self.event_history: List[NexusEvent] = []
        self.state: Dict[str, Any] = {
            "cpu_idle": False,
            "user_active": True,
            "network_online": True,
            "last_user_activity": time.time(),
            "last_event": None,
            "events_handled": 0,
            "idle_seconds": 0,
        }
        self.running = False
        self.handlers_thread = None
        
    def subscribe(self, event_type: EventType, handler: Callable[[NexusEvent], None]):
        """Subscribe a handler to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {event_type.value}")
    
    def subscribe_multiple(self, event_types: List[EventType], handler: Callable):
        """Subscribe a handler to multiple event types."""
        for event_type in event_types:
            self.subscribe(event_type, handler)
    
    def emit(self, event: NexusEvent):
        """Emit an event to the bus."""
        # Update state
        self.state["last_event"] = event.event_type.value
        self.state["last_event_time"] = time.time()
        
        # Add to queue (priority-sorted)
        self.event_queue.put((event.priority.value, time.time(), event))
        
        # Keep history
        self.event_history.append(event)
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-500:]
        
        logger.debug(f"Event emitted: {event}")
    
    def emit_simple(self, event_type: EventType, priority: EventPriority = EventPriority.NORMAL, 
                    data: Dict = None, source: str = "system"):
        """Convenience method to emit events quickly."""
        event = NexusEvent(
            event_type=event_type,
            priority=priority,
            data=data or {},
            source=source
        )
        self.emit(event)
    
    def start(self):
        """Start the event processing loop."""
        self.running = True
        self.handlers_thread = threading.Thread(target=self._process_events, daemon=True)
        self.handlers_thread.start()
        logger.info("Event bus started")
    
    def stop(self):
        """Stop the event processing loop."""
        self.running = False
        if self.handlers_thread:
            self.handlers_thread.join(timeout=5)
        logger.info("Event bus stopped")
    
    def _process_events(self):
        """Process events from the queue."""
        while self.running:
            try:
                # Get event with timeout
                priority, enqueue_time, event = self.event_queue.get(timeout=1)
                
                # Get handlers for this event type
                handlers = self.subscribers.get(event.event_type, [])
                
                # Also get handlers for ALL events
                all_handlers = self.subscribers.get(EventType("all"), [])
                
                # Combine and deduplicate
                all_handlers = list(set(handlers + all_handlers))
                
                # Execute handlers
                for handler in all_handlers:
                    try:
                        handler(event)
                        event.handled = True
                        self.state["events_handled"] += 1
                    except Exception as e:
                        logger.error(f"Handler error in {handler.__name__}: {e}")
                
                self.event_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current system state."""
        # Update derived state
        idle_time = time.time() - self.state.get("last_user_activity", time.time())
        self.state["idle_seconds"] = idle_time
        self.state["cpu_idle"] = idle_time > 60  # 60 seconds = idle
        return self.state.copy()
    
    def get_recent_events(self, count: int = 10) -> List[NexusEvent]:
        """Get recent events."""
        return self.event_history[-count:]


# Global event bus
event_bus = EventBus()