"""
Database Compatibility Layer
Wraps database_v2 (PostgreSQL) to provide the same API as the old database.py
This allows api_server_v5.py to work with PostgreSQL without major refactoring
"""

import os
import sys
import json
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from contextlib import contextmanager

# Import the PostgreSQL backend
from database_v2 import PostgreSQL, get_db as get_pg_db


class CursorCompat:
    """Compatibility wrapper for PostgreSQL cursor to return tuple-style rows"""
    
    def __init__(self, cursor):
        self._cursor = cursor
    
    def execute(self, query, params=None):
        if params:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
    
    def fetchall(self):
        rows = self._cursor.fetchall()
        # Convert dict rows to tuples if needed
        if rows and isinstance(rows[0], dict):
            # Get column names from cursor
            return [tuple(row[col] for col in self._cursor.keys()) for row in rows]
        return rows
    
    def fetchone(self):
        row = self._cursor.fetchone()
        if row and isinstance(row, dict):
            return tuple(row[col] for col in self._cursor.keys())
        return row
    
    @property
    def keys(self):
        return self._cursor.keys()


class ConnCompat:
    """Compatibility wrapper for PostgreSQL connection"""
    
    def __init__(self, conn):
        self._conn = conn
    
    def cursor(self):
        return CursorCompat(self._conn.cursor())
    
    def commit(self):
        self._conn.commit()
    
    def rollback(self):
        self._conn.rollback()
    
    def close(self):
        self._conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


class DatabaseCompat:
    """Compatibility layer wrapping PostgreSQL with old SQLite API"""
    
    def __init__(self, db_url=None):
        self._pg = PostgreSQL(db_url)
    
    @contextmanager
    def _get_conn(self):
        """Get database connection - compatible with old SQLite API"""
        # Get actual connection from the PostgreSQL context manager
        pg_conn = self._pg.get_conn().__enter__()
        try:
            yield ConnCompat(pg_conn)
            pg_conn.commit()
        except Exception:
            pg_conn.rollback()
            raise
        finally:
            pg_conn.close()
    
    def _init_db(self):
        """Initialize the PostgreSQL database"""
        self._pg.init_db()
    
    def _hash_password(self, pwd):
        """Hash password with PBKDF2"""
        import hashlib
        salt = secrets.token_hex(16)
        return f"{salt}${hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt.encode(), 100000).hex()}"
    
    def _parse_password_hash(self, stored):
        """Extract salt and hash from stored password"""
        if not stored or '$' not in stored:
            return None, None
        parts = stored.split('$')
        return parts[0], parts[1] if len(parts) > 1 else None
    
    def create_user(self, uid, email, pwd=None, name='', **kw):
        """Create a new user"""
        password_hash = self._hash_password(pwd) if pwd else None
        api_keys = json.dumps(kw.get('api_keys', {}))
        preferences = json.dumps(kw.get('preferences', {}))
        
        self._pg.execute_write(
            """INSERT INTO users (id, email, password_hash, name, api_keys, preferences, role, subscription, active_model, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
            (uid, email, password_hash, name, api_keys, preferences, 
             kw.get('role', 'user'), kw.get('subscription', 'free'), 
             kw.get('active_model', 'ollama'))
        )
        return self.get_user(uid)
    
    def get_user(self, uid):
        """Get user by ID"""
        return self._pg.execute_one("SELECT * FROM users WHERE id = %s", (uid,))
    
    def get_user_by_email(self, email):
        """Get user by email"""
        return self._pg.execute_one("SELECT * FROM users WHERE email = %s", (email,))
    
    def verify_password(self, uid, pwd):
        """Verify password for user"""
        user = self.get_user(uid)
        if not user or not user.get('password_hash'):
            return False
        
        stored = user['password_hash']
        salt, stored_hash = self._parse_password_hash(stored)
        if not salt or not stored_hash:
            return False
        
        computed = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt.encode(), 100000).hex()
        return computed == stored_hash
    
    def update_user(self, uid, **kw):
        """Update user fields"""
        allowed = ['name', 'email', 'role', 'subscription', 'active_model', 'last_login']
        updates = {}
        
        for k, v in kw.items():
            if k in allowed:
                updates[k] = v
        
        if not updates:
            return self.get_user(uid)
        
        if 'preferences' in updates:
            updates['preferences'] = json.dumps(updates['preferences'])
        if 'api_keys' in updates:
            updates['api_keys'] = json.dumps(updates['api_keys'])
        
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        set_clause = ', '.join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [uid]
        
        self._pg.execute_write(f"UPDATE users SET {set_clause} WHERE id = %s", values)
        return self.get_user(uid)
    
    def create_conversation(self, user_id, title=''):
        """Create a new conversation"""
        conv_id = str(uuid.uuid4())
        self._pg.execute_write(
            "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (%s, %s, %s, NOW(), NOW())",
            (conv_id, user_id, title or '')
        )
        return self.get_conversation(conv_id)
    
    def get_conversation(self, conv_id):
        """Get conversation by ID"""
        return self._pg.execute_one("SELECT * FROM conversations WHERE id = %s", (conv_id,))
    
    def get_conversations(self, user_id):
        """Get all conversations for a user"""
        return self._pg.execute(
            "SELECT * FROM conversations WHERE user_id = %s ORDER BY updated_at DESC", 
            (user_id,)
        )
    
    def get_conversation_messages(self, conv_id):
        """Get all messages in a conversation"""
        return self._pg.execute(
            "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at", 
            (conv_id,)
        )
    
    def add_message(self, conv_id, role, content, **kw):
        """Add a message to a conversation"""
        msg_id = str(uuid.uuid4())
        self._pg.execute_write(
            """INSERT INTO messages (id, conversation_id, role, content, model, created_at)
               VALUES (%s, %s, %s, %s, %s, NOW())""",
            (msg_id, conv_id, role, content, kw.get('model_used', 'ollama'))
        )
        # Update conversation timestamp
        self._pg.execute_write(
            "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
            (conv_id,)
        )
    
    def delete_conversation(self, conv_id, user_id):
        """Delete a conversation"""
        # Delete messages first
        self._pg.execute_write("DELETE FROM messages WHERE conversation_id = %s", (conv_id,))
        self._pg.execute_write("DELETE FROM conversations WHERE id = %s AND user_id = %s", (conv_id, user_id))
    
    def get_user_usage(self, user_id, days=30):
        """Get usage stats for user"""
        return self._pg.execute(
            """SELECT * FROM api_usage 
               WHERE user_id = %s AND created_at > NOW() - INTERVAL '%s days'
               ORDER BY created_at DESC""",
            (user_id, days)
        )
    
    def get_usage_summary(self, user_id):
        """Get aggregated usage summary"""
        result = self._pg.execute_one(
            """SELECT 
               COUNT(*) as total_requests,
               COALESCE(SUM(tokens), 0) as total_tokens,
               COALESCE(SUM(cost), 0) as total_cost
               FROM api_usage WHERE user_id = %s""",
            (user_id,)
        )
        return result or {'total_requests': 0, 'total_tokens': 0, 'total_cost': 0}
    
    def track_usage(self, user_id, model, provider, input_tokens, output_tokens):
        """Track API usage"""
        total = input_tokens + output_tokens
        cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)  # Rough estimate
        self._pg.execute_write(
            """INSERT INTO api_usage (user_id, provider, model, tokens, cost, created_at)
               VALUES (%s, %s, %s, %s, %s, NOW())""",
            (user_id, provider, model, total, cost)
        )


# Singleton instance
_db = None

def init_db(db_path=None):
    """Initialize database (API compatible)"""
    global _db
    _db = DatabaseCompat()
    return _db

def get_db():
    """Get database instance (API compatible)"""
    global _db
    if _db is None:
        _db = init_db()
    return _db