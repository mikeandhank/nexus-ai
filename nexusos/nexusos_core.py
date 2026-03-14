"""
NexusOS Core - Event-Driven Agent Operating System

Main entry point that integrates:
- Event bus (replaces cron)
- Hardware monitors (kernel-level events)
- Event handlers (reactive behavior)
- Inner life components
"""

import os
import sys
import logging
import threading
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from event_bus import EventBus, EventType, EventPriority, event_bus
from hardware_monitors import (
    init_hardware_monitors, 
    start_hardware_monitors, 
    stop_hardware_monitors,
    UserPresenceMonitor
)
from event_handlers import init_event_handlers, EventHandlerManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NexusOS:
    """
    The NexusOS Core - Event-Driven Agent Operating System
    
    Key architectural differences from traditional agent frameworks:
    1. Event-driven (not cron-based)
    2. Hardware-level awareness (CPU, memory, network, user presence)
    3. Self-optimizing (cost optimizer, pattern learning)
    4. Memory-first (compaction on idle)
    """
    
    def __init__(self):
        self.event_bus = event_bus
        self.handler_manager = None
        self.running = False
        self.user_presence = None
        
    def start(self):
        """Start NexusOS."""
        logger.info("=" * 60)
        logger.info("NexusOS - Event-Driven Agent Operating System")
        logger.info("=" * 60)
        
        # Initialize event bus
        self.event_bus.start()
        self.event_bus.emit_simple(EventType.SYSTEM_START)
        
        # Initialize hardware monitors
        init_hardware_monitors(self.event_bus)
        start_hardware_monitors()
        
        # Initialize event handlers
        self.handler_manager = init_event_handlers(self.event_bus)
        self.handler_manager.start_all()
        
        self.running = True
        logger.info("NexusOS started successfully")
        logger.info(f"Event bus running: {self.running}")
        logger.info(f"Subscribers: {len(self.event_bus.subscribers)}")
        
    def stop(self):
        """Stop NexusOS."""
        logger.info("Shutting down NexusOS...")
        
        self.event_bus.emit_simple(EventType.SYSTEM_SHUTDOWN)
        
        stop_hardware_monitors()
        if self.handler_manager:
            self.handler_manager.stop_all()
        self.event_bus.stop()
        
        self.running = False
        logger.info("NexusOS stopped")
    
    def get_status(self):
        """Get system status."""
        state = self.event_bus.get_state()
        return {
            "running": self.running,
            "state": state,
            "subscribers": len(self.event_bus.subscribers),
            "events_handled": state.get("events_handled", 0),
        }
    
    def record_user_activity(self):
        """Record user activity (call from API when user sends message)."""
        if self.user_presence:
            self.user_presence.record_activity()


def main():
    """Main entry point."""
    nexusos = NexusOS()
    
    try:
        nexusos.start()
        
        # Keep running
        while True:
            import time
            time.sleep(60)
            
            # Log status every minute
            status = nexusos.get_status()
            logger.info(f"Status: {status['events_handled']} events handled")
            
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        nexusos.stop()


if __name__ == "__main__":
    main()
