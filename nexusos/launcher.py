#!/usr/bin/env python3
"""
NexusOS Launcher - Runs both API and Event-Driven OS
"""

import os
import sys
import threading
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from event_bus import EventBus, EventType, EventPriority, event_bus
from hardware_monitors import (
    init_hardware_monitors, 
    start_hardware_monitors, 
    stop_hardware_monitors,
)
from event_handlers import init_event_handlers, EventHandlerManager

def start_event_os():
    """Start the event-driven OS."""
    print("Starting NexusOS Event Layer...")
    
    # Initialize event bus
    event_bus.start()
    event_bus.emit_simple(EventType.SYSTEM_START)
    
    # Initialize hardware monitors
    init_hardware_monitors(event_bus)
    start_hardware_monitors()
    
    # Initialize event handlers
    handler_manager = init_event_handlers(event_bus)
    handler_manager.start_all()
    
    print("NexusOS Event Layer started")
    return event_bus, handler_manager

def start_api_server():
    """Start the Flask API server."""
    print("Starting API Server...")
    from api_server_v3 import app
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

def main():
    """Main launcher."""
    print("=" * 60)
    print("NexusOS - Event-Driven Agent Operating System")
    print("=" * 60)
    
    # Start event-driven OS in main thread
    event_bus, handler_manager = start_event_os()
    
    print("\nEvent System Running:")
    print(f"  - File System Watcher: Active")
    print(f"  - System Monitor: Active")
    print(f"  - User Presence: Active")
    print(f"  - Time Events: Active")
    print(f"  - Background Tasks: Active")
    print(f"  - Pattern Learning: Active")
    print(f"  - Cost Optimizer: Active")
    print(f"  - Health Checker: Active")
    print("\nAPI Server: http://0.0.0.0:8080")
    print("=" * 60)
    
    # Start API in separate thread
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(30)
            state = event_bus.get_state()
            print(f"[{time.strftime('%H:%M:%S')}] Events: {state.get('events_handled', 0)} | Idle: {state.get('idle_seconds', 0)}s | CPU Idle: {state.get('cpu_idle', False)}")
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_hardware_monitors()
        handler_manager.stop_all()
        event_bus.stop()

if __name__ == "__main__":
    main()
