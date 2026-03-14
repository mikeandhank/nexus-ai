"""
NexusOS Hardware Event Listeners

Provides OS-level event detection:
- File system watchers (inotify-style)
- System state monitors (CPU, memory, network)
- User presence detection
- Battery/power monitoring
"""

import os
import time
import logging
import threading
import subprocess
from pathlib import Path
from typing import Dict, Set, Optional
from datetime import datetime

from event_bus import EventBus, EventType, EventPriority, NexusEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileSystemWatcher:
    """
    Watches directories for changes without polling.
    Uses inotify (Linux) or polling fallback.
    """
    
    def __init__(self, event_bus: EventBus, watch_paths: list = None):
        self.event_bus = event_bus
        self.watch_paths = watch_paths or ["/opt/nexusos-api"]
        self.watch_descriptors = {}  # path -> wd mapping
        self.running = False
        self.thread = None
        
        # Detect inotify support
        self.has_inotify = self._check_inotify()
        
        if self.has_inotify:
            logger.info("inotify available - using kernel-level file watching")
        else:
            logger.warning("inotify not available - using polling fallback")
    
    def _check_inotify(self) -> bool:
        """Check if inotify is available."""
        try:
            # Try to import inotify
            import ctypes
            ctypes.CDLL("libc.so.6").inotify_init1(0)
            return True
        except:
            return False
    
    def start(self):
        """Start watching files."""
        self.running = True
        
        if self.has_inotify:
            self.thread = threading.Thread(target=self._watch_inotify, daemon=True)
        else:
            self.thread = threading.Thread(target=self._watch_polling, daemon=True)
            
        self.thread.start()
        logger.info(f"FileSystemWatcher started for {self.watch_paths}")
    
    def stop(self):
        """Stop watching files."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("FileSystemWatcher stopped")
    
    def _watch_inotify(self):
        """Kernel-level file watching using inotify."""
        try:
            import ctypes
            import ctypes.util
            
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            
            # inotify constants
            IN_CREATE = 0x00000100
            IN_MODIFY = 0x00000002
            IN_DELETE = 0x00000200
            IN_MOVED_FROM = 0x00000080
            IN_MOVED_TO = 0x00000080
            IN_CLOSE_WRITE = 0x00000008
            IN_MASK = IN_CREATE | IN_MODIFY | IN_DELETE | IN_CLOSE_WRITE
            
            # Initialize inotify
            fd = libc.inotify_init1(0)
            if fd < 0:
                raise OSError("Failed to init inotify")
            
            # Add watches
            for path in self.watch_paths:
                wd = libc.inotify_add_watch(fd, path.encode(), IN_MASK)
                if wd >= 0:
                    self.watch_descriptors[path] = wd
            
            # Event buffer
            event_size = 16  # struct inotify_event size
            buf = bytearray(65536)
            
            while self.running:
                # Read with timeout
                import select
                r, _, _ = select.select([fd], [], [], 1)
                
                if fd in r:
                    n = libc.read(fd, buf, len(buf))
                    if n > 0:
                        pos = 0
                        while pos < n:
                            event = buf[pos:pos + event_size]
                            wd = int.from_bytes(event[0:4], 'little')
                            mask = int.from_bytes(event[4:8], 'little')
                            name_len = int.from_bytes(event[8:12], 'little')
                            name = buf[pos + 16:pos + 16 + name_len].decode('utf-8', errors='ignore').rstrip('\x00')
                            
                            # Find path
                            path = next((p for p, w in self.watch_descriptors.items() if w == wd), None)
                            
                            if path and not name.startswith('.'):
                                full_path = os.path.join(path, name)
                                
                                # Emit event
                                if mask & IN_CREATE:
                                    self.event_bus.emit_simple(
                                        EventType.FILE_CREATED,
                                        data={"path": full_path}
                                    )
                                if mask & IN_MODIFY:
                                    self.event_bus.emit_simple(
                                        EventType.FILE_MODIFIED,
                                        data={"path": full_path}
                                    )
                                if mask & IN_DELETE:
                                    self.event_bus.emit_simple(
                                        EventType.FILE_DELETED,
                                        data={"path": full_path}
                                    )
                            
                            pos += event_size + name_len
            
            # Cleanup
            for wd in self.watch_descriptors.values():
                libc.inotify_rm_watch(fd, wd)
            os.close(fd)
            
        except Exception as e:
            logger.error(f"inotify error: {e}")
            # Fallback to polling
            self._watch_polling()
    
    def _watch_polling(self):
        """Polling fallback when inotify unavailable."""
        last_states = {}
        
        while self.running:
            try:
                for watch_path in self.watch_paths:
                    if os.path.exists(watch_path):
                        for root, dirs, files in os.walk(watch_path):
                            for f in files:
                                full_path = os.path.join(root, f)
                                try:
                                    mtime = os.path.getmtime(full_path)
                                    
                                    if full_path not in last_states:
                                        last_states[full_path] = mtime
                                        self.event_bus.emit_simple(
                                            EventType.FILE_CREATED,
                                            data={"path": full_path}
                                        )
                                    elif last_states[full_path] != mtime:
                                        last_states[full_path] = mtime
                                        self.event_bus.emit_simple(
                                            EventType.FILE_MODIFIED,
                                            data={"path": full_path}
                                        )
                                except:
                                    pass
                
                time.sleep(5)  # Poll every 5 seconds
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(10)


class SystemMonitor:
    """
    Monitors system state: CPU, memory, network, power.
    Emits events when state changes significantly.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.running = False
        self.thread = None
        self.last_cpu_idle = True
        self.last_network_online = True
        self.last_battery_state = None
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("SystemMonitor started")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("SystemMonitor stopped")
    
    def _monitor_loop(self):
        """Continuously monitor system state."""
        while self.running:
            try:
                self._check_cpu()
                self._check_memory()
                self._check_network()
                self._check_power()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(30)
    
    def _check_cpu(self):
        """Check CPU usage."""
        try:
            # Read /proc/stat
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                parts = line.split()
                idle = int(parts[5])
                total = sum(int(p) for p in parts[1:])
            
            idle_pct = (idle / total) * 100 if total > 0 else 0
            is_idle = idle_pct > 80  # 80% idle = system idle
            
            if is_idle != self.last_cpu_idle:
                self.last_cpu_idle = is_idle
                if is_idle:
                    self.event_bus.emit_simple(
                        EventType.CPU_IDLE,
                        priority=EventPriority.LOW,
                        data={"idle_pct": idle_pct}
                    )
                else:
                    self.event_bus.emit_simple(
                        EventType.CPU_BUSY,
                        priority=EventPriority.NORMAL,
                        data={"idle_pct": idle_pct}
                    )
        except Exception as e:
            logger.debug(f"CPU check error: {e}")
    
    def _check_memory(self):
        """Check memory pressure."""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            total = int([l for l in meminfo.split('\n') if l.startswith('MemTotal:')][0].split()[1]) * 1024
            available = int([l for l in meminfo.split('\n') if l.startswith('MemAvailable:')][0].split()[1]) * 1024
            used_pct = ((total - available) / total) * 100
            
            if used_pct > 90:
                self.event_bus.emit_simple(
                    EventType.MEMORY_PRESSURE,
                    priority=EventPriority.HIGH,
                    data={"used_pct": used_pct, "available_mb": available // (1024*1024)}
                )
        except Exception as e:
            logger.debug(f"Memory check error: {e}")
    
    def _check_network(self):
        """Check network connectivity."""
        try:
            # Check if we can reach gateway
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '1', '8.8.8.8'],
                capture_output=True, timeout=5
            )
            is_online = result.returncode == 0
            
            if is_online != self.last_network_online:
                self.last_network_online = is_online
                self.event_bus.emit_simple(
                    EventType.NETWORK_ONLINE if is_online else EventType.NETWORK_OFFLINE,
                    priority=EventPriority.HIGH if not is_online else EventPriority.NORMAL
                )
        except:
            # Assume online if ping fails
            pass
    
    def _check_power(self):
        """Check battery/power state (for laptops)."""
        try:
            # Check for battery info
            if os.path.exists('/sys/class/power_supply/BAT0/status'):
                with open('/sys/class/power_supply/BAT0/status', 'r') as f:
                    status = f.read().strip()
                
                if status != self.last_battery_state:
                    self.last_battery_state = status
                    if status == 'Discharging':
                        self.event_bus.emit_simple(
                            EventType.POWER_ON_BATTERY,
                            priority=EventPriority.NORMAL
                        )
                    elif status == 'Charging':
                        self.event_bus.emit_simple(
                            EventType.POWER_CHARGING,
                            priority=EventPriority.LOW
                        )
        except Exception as e:
            logger.debug(f"Power check error: {e}")


class UserPresenceMonitor:
    """
    Detects user presence via input activity.
    Used to adjust agent responsiveness.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.running = False
        self.thread = None
        self.last_activity = time.time()
        self.idle_threshold = 120  # 2 minutes
        self.is_away = False
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("UserPresenceMonitor started")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("UserPresenceMonitor stopped")
    
    def record_activity(self):
        """Call this when user activity is detected."""
        self.last_activity = time.time()
        if self.is_away:
            self.is_away = False
            self.event_bus.emit_simple(
                EventType.USER_ACTIVE,
                priority=EventPriority.HIGH
            )
    
    def _monitor_loop(self):
        """Monitor for user activity."""
        while self.running:
            try:
                now = time.time()
                idle_seconds = now - self.last_activity
                
                if not self.is_away and idle_seconds > self.idle_threshold:
                    self.is_away = True
                    self.event_bus.emit_simple(
                        EventType.USER_AWAY,
                        priority=EventPriority.NORMAL,
                        data={"idle_seconds": idle_seconds}
                    )
                elif self.is_away and idle_seconds < 30:
                    self.is_away = False
                    self.event_bus.emit_simple(
                        EventType.USER_ACTIVE,
                        priority=EventPriority.HIGH
                    )
                
                # Emit idle detection periodically
                if idle_seconds > 300:  # 5 minutes
                    self.event_bus.emit_simple(
                        EventType.IDLE_DETECTED,
                        priority=EventPriority.IDLE,
                        data={"idle_seconds": idle_seconds}
                    )
                
                time.sleep(10)
            except Exception as e:
                logger.error(f"User presence error: {e}")
                time.sleep(30)


class TimeEventEmitter:
    """
    Smarter time-based events than cron.
    Emits events at regular intervals but can be controlled by system state.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.running = False
        self.thread = None
        self.minute_count = 0
        self.hour_count = 0
        self.day_count = 0
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._emit_loop, daemon=True)
        self.thread.start()
        logger.info("TimeEventEmitter started")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("TimeEventEmitter stopped")
    
    def _emit_loop(self):
        """Emit time-based events."""
        while self.running:
            try:
                time.sleep(60)  # Every minute
                self.minute_count += 1
                
                state = self.event_bus.get_state()
                
                # Only emit if not under heavy load
                if not state.get("memory_pressure", False):
                    self.event_bus.emit_simple(
                        EventType.EVERY_MINUTE,
                        priority=EventPriority.IDLE if state.get("cpu_idle") else EventPriority.NORMAL,
                        data={"minute": self.minute_count, "state": state}
                    )
                
                if self.minute_count >= 60:
                    self.minute_count = 0
                    self.hour_count += 1
                    self.event_bus.emit_simple(
                        EventType.EVERY_HOUR,
                        priority=EventPriority.LOW,
                        data={"hour": self.hour_count}
                    )
                    
                    if self.hour_count >= 24:
                        self.hour_count = 0
                        self.day_count += 1
                        self.event_bus.emit_simple(
                            EventType.EVERY_DAY,
                            priority=EventPriority.LOW,
                            data={"day": self.day_count}
                        )
                        
            except Exception as e:
                logger.error(f"Time emitter error: {e}")
                time.sleep(60)


# Initialize all hardware-level monitors
file_watcher = None
system_monitor = None
user_presence = None
time_emitter = None


def init_hardware_monitors(event_bus: EventBus):
    """Initialize all hardware-level monitors."""
    global file_watcher, system_monitor, user_presence, time_emitter
    
    file_watcher = FileSystemWatcher(event_bus)
    system_monitor = SystemMonitor(event_bus)
    user_presence = UserPresenceMonitor(event_bus)
    time_emitter = TimeEventEmitter(event_bus)
    
    logger.info("Hardware monitors initialized")


def start_hardware_monitors():
    """Start all hardware-level monitors."""
    if file_watcher:
        file_watcher.start()
    if system_monitor:
        system_monitor.start()
    if user_presence:
        user_presence.start()
    if time_emitter:
        time_emitter.start()
    logger.info("All hardware monitors started")


def stop_hardware_monitors():
    """Stop all hardware-level monitors."""
    if file_watcher:
        file_watcher.stop()
    if system_monitor:
        system_monitor.stop()
    if user_presence:
        user_presence.stop()
    if time_emitter:
        time_emitter.stop()
    logger.info("All hardware monitors stopped")