"""
NexusOS Structured Logging & Activity Tracking

Provides:
- Structured JSON logging
- Activity log (every action recorded)
- Audit trails for compliance
- Kill switches for safety
"""

import json
import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import os

# Try to use PostgreSQL if available
try:
    import psycopg2
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    USE_PG = bool(DATABASE_URL)
    if USE_PG:
        def get_pg_conn():
            return psycopg2.connect(DATABASE_URL)
except ImportError:
    USE_PG = False


class LogLevel(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


class EventType(Enum):
    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_PAUSED = "agent.paused"
    AGENT_RESUMED = "agent.resumed"
    AGENT_DELETED = "agent.deleted"
    AGENT_ERROR = "agent.error"
    
    # Chat events
    CHAT_MESSAGE = "chat.message"
    CHAT_COMPLETE = "chat.complete"
    CHAT_ERROR = "chat.error"
    
    # User events
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    
    # Tool events
    TOOL_CALLED = "tool.called"
    TOOL_SUCCESS = "tool.success"
    TOOL_ERROR = "tool.error"
    
    # LLM events
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"
    LLM_ERROR = "llm.error"
    
    # System events
    SYSTEM_START = "system.start"
    SYSTEM_ERROR = "system.error"
    API_REQUEST = "api.request"


@dataclass
class LogEntry:
    """Structured log entry"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    level: str = "INFO"
    event_type: str = ""
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    success: bool = True
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class StructuredLogger:
    """
    Centralized structured logging for NexusOS.
    Logs to both console and database for audit trails.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._logs: List[LogEntry] = []
        self._max_memory_logs = 10000
        self._log_file = os.environ.get('NEXUSOS_LOG_FILE', '/var/log/nexusos/activity.log')
        self._min_level = LogLevel[os.environ.get('NEXUSOS_LOG_LEVEL', 'INFO').upper()]
        
        # Initialize DB table
        self._init_log_table()
    
    def _init_log_table(self):
        """Initialize the activity_log table"""
        if not USE_PG:
            return
        
        try:
            conn = get_pg_conn()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    level TEXT,
                    event_type TEXT,
                    user_id TEXT,
                    agent_id TEXT,
                    message TEXT,
                    details JSONB,
                    duration_ms REAL,
                    success BOOLEAN DEFAULT true,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)
            
            # Create indexes for common queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_user 
                ON activity_log(user_id, timestamp)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_agent 
                ON activity_log(agent_id, timestamp)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_type 
                ON activity_log(event_type, timestamp)
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Logger] DB init error: {e}")
    
    def _should_log(self, level: LogLevel) -> bool:
        return level.value >= self._min_level.value
    
    def log(self, level: LogLevel, event_type: str, message: str,
            user_id: str = None, agent_id: str = None,
            details: Dict = None, duration_ms: float = None,
            success: bool = True, ip_address: str = None,
            user_agent: str = None):
        """Create a log entry"""
        
        if not self._should_log(level):
            return
        
        entry = LogEntry(
            level=level.name,
            event_type=event_type,
            message=message,
            user_id=user_id,
            agent_id=agent_id,
            details=details or {},
            duration_ms=duration_ms,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Store in memory
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > self._max_memory_logs:
                self._logs = self._logs[-self._max_memory_logs:]
        
        # Write to DB (async in production, sync for now)
        self._write_to_db(entry)
        
        # Print to console in JSON format for container logs
        print(json.dumps(entry.to_dict()))
        
        return entry
    
    def _write_to_db(self, entry: LogEntry):
        """Write log entry to database"""
        if not USE_PG:
            return
        
        try:
            conn = get_pg_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO activity_log 
                (id, timestamp, level, event_type, user_id, agent_id, 
                 message, details, duration_ms, success, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                entry.id, entry.timestamp, entry.level, entry.event_type,
                entry.user_id, entry.agent_id, entry.message,
                json.dumps(entry.details), entry.duration_ms,
                entry.success, entry.ip_address, entry.user_agent
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Logger] DB write error: {e}")
    
    # Convenience methods
    def debug(self, event_type: str, message: str, **kwargs):
        return self.log(LogLevel.DEBUG, event_type, message, **kwargs)
    
    def info(self, event_type: str, message: str, **kwargs):
        return self.log(LogLevel.INFO, event_type, message, **kwargs)
    
    def warning(self, event_type: str, message: str, **kwargs):
        return self.log(LogLevel.WARNING, event_type, message, **kwargs)
    
    def error(self, event_type: str, message: str, **kwargs):
        return self.log(LogLevel.ERROR, event_type, message, **kwargs)
    
    def critical(self, event_type: str, message: str, **kwargs):
        return self.log(LogLevel.CRITICAL, event_type, message, **kwargs)
    
    # Query methods
    def get_logs(self, user_id: str = None, agent_id: str = None,
                 event_type: str = None, since: datetime = None,
                 limit: int = 100) -> List[LogEntry]:
        """Query log entries"""
        
        if USE_PG:
            return self._query_from_db(user_id, agent_id, event_type, since, limit)
        
        # Fallback to memory
        return self._query_from_memory(user_id, agent_id, event_type, since, limit)
    
    def _query_from_db(self, user_id: str = None, agent_id: str = None,
                       event_type: str = None, since: datetime = None,
                       limit: int = 100) -> List[LogEntry]:
        """Query from PostgreSQL"""
        
        query = "SELECT * FROM activity_log WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)
        if agent_id:
            query += " AND agent_id = %s"
            params.append(agent_id)
        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)
        if since:
            query += " AND timestamp >= %s"
            params.append(since.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        try:
            conn = get_pg_conn()
            conn.row_factory = None
            cur = conn.cursor()
            cur.execute(query, params)
            
            entries = []
            for row in cur.fetchall():
                entries.append(LogEntry(
                    id=row[0], timestamp=row[1], level=row[2],
                    event_type=row[3], user_id=row[4], agent_id=row[5],
                    message=row[6], details=row[7] or {}, duration_ms=row[8],
                    success=row[9], ip_address=row[10], user_agent=row[11]
                ))
            conn.close()
            return entries
        except Exception as e:
            print(f"[Logger] Query error: {e}")
            return []
    
    def _query_from_memory(self, user_id: str = None, agent_id: str = None,
                           event_type: str = None, since: datetime = None,
                           limit: int = 100) -> List[LogEntry]:
        """Query from memory (fallback)"""
        
        results = self._logs.copy()
        
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if since:
            since_iso = since.isoformat()
            results = [e for e in results if e.timestamp >= since_iso]
        
        return results[-limit:][::-1]


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger() -> StructuredLogger:
    """Get the global logger instance"""
    global _logger
    if _logger is None:
        _logger = StructuredLogger()
    return _logger


# ==================== KILL SWITCHES ====================

class KillSwitches:
    """
    Safety mechanisms to halt operations when thresholds are exceeded.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Default limits (can be overridden via env)
        self.limits = {
            'max_tokens_per_request': int(os.environ.get('NEXUSOS_MAX_TOKENS', 8192)),
            'max_tool_calls_per_request': int(os.environ.get('NEXUSOS_MAX_TOOL_CALLS', 50)),
            'max_concurrent_agents': int(os.environ.get('NEXUSOS_MAX_AGENTS', 10)),
            'max_requests_per_minute': int(os.environ.get('NEXUSOS_MAX_RPM', 120)),
            'max_cost_per_day_usd': float(os.environ.get('NEXUSOS_MAX_DAILY_COST', 100.0)),
            'max_conversation_length': int(os.environ.get('NEXUSOS_MAX_CONV_LENGTH', 100)),
        }
        
        # Current usage tracking
        self._user_usage: Dict[str, Dict] = {}
        self._request_timestamps: Dict[str, List[float]] = {}
        self._daily_costs: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def check(self, user_id: str, operation: str, value: Any = None) -> tuple[bool, str]:
        """
        Check if operation is allowed.
        Returns (allowed: bool, reason: str)
        """
        
        now = time.time()
        
        with self._lock:
            # Initialize user if new
            if user_id not in self._user_usage:
                self._user_usage[user_id] = {
                    'tokens_used': 0,
                    'tool_calls': 0,
                    'agents_started': 0,
                }
                self._request_timestamps[user_id] = []
            
            user = self._user_usage[user_id]
            requests = self._request_timestamps[user_id]
            
            # Check requests per minute
            recent_requests = [t for t in requests if now - t < 60]
            if len(recent_requests) >= self.limits['max_requests_per_minute']:
                return False, f"Rate limit: {self.limits['max_requests_per_minute']} requests/minute"
            
            # Check token limit
            if operation == 'tokens' and value:
                if user['tokens_used'] + value > self.limits['max_tokens_per_request']:
                    return False, f"Token limit exceeded: {self.limits['max_tokens_per_request']}"
            
            # Check tool call limit
            if operation == 'tool_call':
                if user['tool_calls'] >= self.limits['max_tool_calls_per_request']:
                    return False, f"Tool call limit exceeded: {self.limits['max_tool_calls_per_request']}"
            
            # Check concurrent agents
            if operation == 'start_agent':
                if user['agents_started'] >= self.limits['max_concurrent_agents']:
                    return False, f"Agent limit exceeded: {self.limits['max_concurrent_agents']}"
            
            # Record the operation
            if operation == 'tokens':
                user['tokens_used'] += value
            elif operation == 'tool_call':
                user['tool_calls'] += 1
            elif operation == 'start_agent':
                user['agents_started'] += 1
            elif operation == 'stop_agent':
                user['agents_started'] = max(0, user['agents_started'] - 1)
            
            requests.append(now)
            
            return True, "OK"
    
    def reset_user(self, user_id: str):
        """Reset usage for a user (admin function)"""
        with self._lock:
            self._user_usage.pop(user_id, None)
            self._request_timestamps.pop(user_id, None)
    
    def get_limits(self) -> Dict:
        """Get current limits"""
        return self.limits.copy()
    
    def set_limit(self, key: str, value: Any):
        """Update a limit (admin function)"""
        if key in self.limits:
            self.limits[key] = value


def get_kill_switches() -> KillSwitches:
    """Get the global kill switches instance"""
    return KillSwitches()


# ==================== RATE LIMITING ====================

class RateLimiter:
    """
    Token bucket rate limiting per user/endpoint.
    """
    
    def __init__(self):
        self._buckets: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        
        # Default: 100 requests per minute
        self.default_rate = 100
        self.default_window = 60  # seconds
    
    def check(self, key: str, rate: int = None, window: int = None) -> bool:
        """
        Check if request is allowed.
        Uses token bucket algorithm.
        """
        
        rate = rate or self.default_rate
        window = window or self.default_window
        now = time.time()
        
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = {
                    'tokens': rate,
                    'last_refill': now,
                    'requests': []
                }
            
            bucket = self._buckets[key]
            
            # Refill tokens
            elapsed = now - bucket['last_refill']
            refill = (elapsed / window) * rate
            bucket['tokens'] = min(rate, bucket['tokens'] + refill)
            bucket['last_refill'] = now
            
            # Clean old requests
            bucket['requests'] = [t for t in bucket['requests'] if now - t < window]
            
            # Check limit
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                bucket['requests'].append(now)
                return True
            
            return False
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests for key"""
        with self._lock:
            bucket = self._buckets.get(key, {'tokens': self.default_rate})
            return int(bucket['tokens'])
    
    def reset(self, key: str):
        """Reset rate limit for key"""
        with self._lock:
            self._buckets.pop(key, None)


# Flask route integration
def setup_logging_routes(app, logger: StructuredLogger, kill_switches: KillSwitches, rate_limiter: RateLimiter = None):
    """Add logging and monitoring routes to Flask app"""
    from flask import request, jsonify
    
    if rate_limiter is None:
        rate_limiter = _rate_limiter
    
    @app.route('/api/logs', methods=['GET'])
    def get_logs():
        """Query activity logs"""
        user_id = request.args.get('user_id')
        agent_id = request.args.get('agent_id')
        event_type = request.args.get('event_type')
        limit = request.args.get('limit', 100, type=int)
        
        logs = logger.get_logs(user_id, agent_id, event_type, limit=limit)
        return jsonify({
            'logs': [l.to_dict() for l in logs],
            'count': len(logs)
        })
    
    @app.route('/api/limits', methods=['GET'])
    def get_limits():
        """Get current kill switch limits"""
        return jsonify({
            'limits': kill_switches.get_limits()
        })
    
    @app.route('/api/limits', methods=['PUT'])
    def update_limits():
        """Update kill switch limits (admin only)"""
        # Would add admin check here
        data = request.json or {}
        for key, value in data.items():
            kill_switches.set_limit(key, value)
        return jsonify({'status': 'updated'})
    
    @app.route('/api/usage/reset', methods=['POST'])
    def reset_usage():
        """Reset user's usage counters"""
        data = request.json or {}
        user_id = data.get('user_id')
        if user_id:
            kill_switches.reset_user(user_id)
            return jsonify({'status': 'reset'})
        return jsonify({'error': 'user_id required'}), 400
    
    @app.route('/api/rate_limit/status', methods=['GET'])
    def rate_limit_status():
        """Check rate limit status"""
        user_id = request.args.get('user_id', 'anonymous')
        endpoint = request.args.get('endpoint', 'api')
        key = f"{user_id}:{endpoint}"
        
        remaining = rate_limiter.get_remaining(key)
        return jsonify({
            'remaining': remaining,
            'limit': rate_limiter.default_rate,
            'window_seconds': rate_limiter.default_window
        })


# Global instances
logger = get_logger()
kill_switches = get_kill_switches()
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the rate limiter instance"""
    return _rate_limiter
