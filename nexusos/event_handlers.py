"""
NexusOS Event Handlers

Handlers that respond to events from the event bus.
These implement the actual behavior of the agent OS.
"""

import os
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any

from event_bus import EventBus, EventType, EventPriority, NexusEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackgroundTaskHandler:
    """
    Handles background tasks when system is idle.
    Replaces cron-based background processing.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.pending_tasks = []
        self.running = False
        self.thread = None
        
    def add_task(self, task: Dict):
        """Add a background task."""
        self.pending_tasks.append(task)
        logger.info(f"Task added: {task.get('name', 'unnamed')}")
    
    def start(self):
        """Start processing background tasks."""
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.CPU_IDLE, self._on_cpu_idle)
        self.event_bus.subscribe(EventType.IDLE_DETECTED, self._on_idle)
        
        logger.info("BackgroundTaskHandler started")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("BackgroundTaskHandler stopped")
    
    def _on_cpu_idle(self, event: NexusEvent):
        """When CPU is idle, run background tasks."""
        if self.pending_tasks:
            logger.info(f"CPU idle - processing {len(self.pending_tasks)} pending tasks")
            self._process_loop()
    
    def _on_idle(self, event: NexusEvent):
        """User is idle - good time for heavy processing."""
        logger.info(f"User idle for {event.data.get('idle_seconds', 0)}s - scheduling intensive tasks")
    
    def _process_loop(self):
        """Process pending tasks."""
        while self.pending_tasks and self.running:
            task = self.pending_tasks.pop(0)
            try:
                logger.info(f"Executing task: {task.get('name', 'unnamed')}")
                # Task would execute here
                # For now, just log it
            except Exception as e:
                logger.error(f"Task error: {e}")
                # Could re-queue on failure


class MemoryCompactionHandler:
    """
    Handles memory compaction when idle.
    Optimizes memory usage and saves state.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.last_compaction = None
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.IDLE_DETECTED, self._on_idle)
        self.event_bus.subscribe(EventType.EVERY_HOUR, self._on_hourly)
        self.event_bus.subscribe(EventType.SYSTEM_SHUTDOWN, self._on_shutdown)
    
    def _on_idle(self, event: NexusEvent):
        """Compact memory when system is idle."""
        idle_time = event.data.get('idle_seconds', 0)
        if idle_time > 600:  # 10+ minutes idle
            self._compact_memory()
    
    def _on_hourly(self, event: NexusEvent):
        """Hourly memory check."""
        if self.last_compaction:
            hours_since = (datetime.now() - self.last_compaction).hours
            if hours_since > 1:
                self._compact_memory()
    
    def _on_shutdown(self, event: NexusEvent):
        """Always compact before shutdown."""
        self._compact_memory()
    
    def _compact_memory(self):
        """Perform memory compaction."""
        logger.info("Compacting memory...")
        self.last_compaction = datetime.now()
        # Would compact memories here
        self.event_bus.emit_simple(
            EventType("memory_compacted"),
            data={"timestamp": self.last_compaction.isoformat()}
        )


class PatternLearner:
    """
    Learns patterns from events over time.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.patterns = {}
        self.pattern_counts = {}
        
        # Subscribe to all events
        self.event_bus.subscribe_multiple([
            EventType.USER_ACTIVE,
            EventType.USER_AWAY,
            EventType.FILE_MODIFIED,
            EventType.CPU_IDLE,
            EventType.NETWORK_ONLINE,
            EventType.NETWORK_OFFLINE,
        ], self._record_pattern)
    
    def _record_pattern(self, event: NexusEvent):
        """Record event patterns."""
        event_name = event.event_type.value
        now = datetime.now()
        hour = now.hour
        day = now.strftime('%A')
        
        key = f"{event_name}_{hour}_{day}"
        self.pattern_counts[key] = self.pattern_counts.get(key, 0) + 1
        
        # Detect frequent patterns
        if self.pattern_counts[key] > 10:
            self.patterns[event_name] = {
                "typical_hour": hour,
                "typical_day": day,
                "count": self.pattern_counts[key]
            }
    
    def get_patterns(self) -> Dict:
        """Get learned patterns."""
        return self.patterns.copy()


class CostOptimizer:
    """
    Optimizes API usage based on system state.
    Uses cheaper models when idle, more expensive when active.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.current_model = "phi3"  # Default to free model
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.USER_AWAY, self._on_user_away)
        self.event_bus.subscribe(EventType.USER_ACTIVE, self._on_user_active)
        self.event_bus.subscribe(EventType.MEMORY_PRESSURE, self._on_memory_pressure)
    
    def _on_user_away(self, event: NexusEvent):
        """When user away, switch to cheaper processing."""
        self.current_model = "phi3"  # Free Ollama model
        logger.info("User away - switched to free model")
    
    def _on_user_active(self, event: NexusEvent):
        """When user active, use better model."""
        self.current_model = "gpt-4o-mini"  # Better model
        logger.info("User active - switched to premium model")
    
    def _on_memory_pressure(self, event: NexusEvent):
        """Under memory pressure, use minimal resources."""
        self.current_model = "phi3"  # Always free model
        logger.info("Memory pressure - using minimal model")


class HealthChecker:
    """
    Monitors system health and emits warnings.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.start_time = None
        
        self.event_bus.subscribe(EventType.SYSTEM_START, self._on_start)
        self.event_bus.subscribe(EventType.EVERY_MINUTE, self._on_minute)
        self.event_bus.subscribe(EventType.AGENT_ERROR, self._on_error)
    
    def _on_start(self, event: NexusEvent):
        """Track when system started."""
        self.start_time = datetime.now()
    
    def _on_minute(self, event: NexusEvent):
        """Periodic health check."""
        state = self.event_bus.get_state()
        
        # Check for issues
        events_handled = state.get("events_handled", 0)
        idle_seconds = state.get("idle_seconds", 0)
        
        if idle_seconds > 3600:  # 1 hour idle
            logger.info(f"System running for 1+ hour, {events_handled} events handled")
    
    def _on_error(self, event: NexusEvent):
        """Log errors."""
        logger.error(f"Agent error detected: {event.data}")


class EventHandlerManager:
    """
    Manages all event handlers.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.handlers = []
        
    def register(self, handler):
        """Register a handler."""
        self.handlers.append(handler)
        logger.info(f"Handler registered: {handler.__class__.__name__}")
    
    def start_all(self):
        """Start all handlers."""
        for handler in self.handlers:
            if hasattr(handler, 'start'):
                handler.start()
        logger.info(f"All {len(self.handlers)} handlers started")
    
    def stop_all(self):
        """Stop all handlers."""
        for handler in self.handlers:
            if hasattr(handler, 'stop'):
                handler.stop()
        logger.info("All handlers stopped")


def init_event_handlers(event_bus: EventBus) -> EventHandlerManager:
    """Initialize all event handlers."""
    manager = EventHandlerManager(event_bus)
    
    # Register handlers
    manager.register(BackgroundTaskHandler(event_bus))
    manager.register(MemoryCompactionHandler(event_bus))
    manager.register(PatternLearner(event_bus))
    manager.register(CostOptimizer(event_bus))
    manager.register(HealthChecker(event_bus))
    
    return manager
