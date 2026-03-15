"""
PostgreSQL Database Layer for NexusOS
Replaces SQLite for concurrent enterprise workloads
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import json

# Database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://nexusos:nexusos@localhost:5432/nexusos')

class PostgreSQL:
    def __init__(self, db_url=None):
        self.db_url = db_url or DATABASE_URL
    
    @contextmanager
    def get_conn(self):
        """Get database connection with context manager"""
        conn = psycopg2.connect(self.db_url)
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        """Initialize database schema"""
        with self.get_conn() as conn:
            cur = conn.cursor()
            
            # Users table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT,
                    subscription TEXT DEFAULT 'free',
                    api_keys TEXT DEFAULT '[]',
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Conversations table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Messages table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tokens INTEGER,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            ''')
            
            # Agents table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT DEFAULT 'general',
                    system_prompt TEXT,
                    tools TEXT DEFAULT '[]',
                    model TEXT,
                    status TEXT DEFAULT 'inactive',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Memory table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS memory (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embeddings JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Audit log table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    resource TEXT,
                    details JSONB,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Events table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload JSONB,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # API usage table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS api_usage (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    tokens INTEGER,
                    cost REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Webhooks table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS webhooks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    secret TEXT,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Usage stats table (for usage analytics)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    model TEXT,
                    provider TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    requests INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cur.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_memory_user ON memory(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_usage_user ON api_usage(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_user ON usage_stats(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_date ON usage_stats(created_at)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_webhooks_user ON webhooks(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_webhooks_event ON webhooks(event_type)')
            
            conn.commit()
            cur.close()
            print("PostgreSQL database initialized")
    
    def execute(self, query, params=None, fetch=True):
        """Execute a query"""
        with self.get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params or ())
            if fetch:
                result = cur.fetchall()
            else:
                result = cur.lastrowid
            conn.commit()
            cur.close()
            return result
    
    def execute_one(self, query, params=None):
        """Execute a query and return one result"""
        with self.get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params or ())
            result = cur.fetchone()
            cur.close()
            return result
    
    def execute_write(self, query, params=None):
        """Execute INSERT/UPDATE/DELETE"""
        with self.get_conn() as conn:
            cur = conn.cursor()
            cur.execute(query, params or ())
            conn.commit()
            result = cur.lastrowid
            cur.close()
            return result


# Singleton instance
_db = None

def get_db():
    """Get database instance"""
    global _db
    if _db is None:
        _db = PostgreSQL()
    return _db
