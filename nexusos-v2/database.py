"""NexusOS v2 - Database Layer"""
import sqlite3, json, hashlib, secrets, os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DB_PATH = os.environ.get("NEXUSOS_DB", "/opt/nexusos-data/nexusos.db")

class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try: yield conn; conn.commit()
        except Exception as e: conn.rollback(); raise e
        finally: conn.close()
    
    def _init_db(self):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT, name TEXT, role TEXT DEFAULT 'user', subscription TEXT DEFAULT 'free', created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, last_login TEXT, api_keys TEXT, preferences TEXT, active_model TEXT DEFAULT 'ollama')''')
            c.execute('''CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, title TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, message_count INTEGER DEFAULT 0, metadata TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, model_used TEXT, directive TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, metadata TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS memory_working (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT, expires_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS memory_episodic (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, event_type TEXT, summary TEXT, details TEXT, importance REAL DEFAULT 0.5, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS memory_semantic (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, entity_type TEXT, entity_name TEXT, knowledge TEXT, confidence REAL DEFAULT 0.5, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL, role TEXT, personality TEXT, tools TEXT, status TEXT DEFAULT 'idle', created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, last_active TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT NOT NULL, resource_type TEXT, resource_id TEXT, details TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, priority INTEGER DEFAULT 3, source TEXT, data TEXT, handled INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            logger.info("Database initialized")
    
    def _hash_password(self, pwd):
        salt = secrets.token_hex(16)
        return f"{salt}${hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt.encode(), 100000).hex()}"
    
    def create_user(self, uid, email, pwd=None, name='', **kw):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (id,email,password_hash,name,api_keys,preferences,active_model,subscription) VALUES (?,?,?,?,?,?,?,?)",
                (uid, email, self._hash_password(pwd) if pwd else None, name, json.dumps(kw.get('api_keys',{})), json.dumps(kw.get('preferences',{})), kw.get('active_model','ollama'), kw.get('subscription','free')))
        return self.get_user(uid)
    
    def get_user(self, uid):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (uid,))
            r = c.fetchone()
            return dict(r) if r else None
    
    def get_user_by_email(self, email):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            r = c.fetchone()
            return dict(r) if r else None
    
    def verify_password(self, uid, pwd):
        u = self.get_user(uid)
        return u and u.get('password_hash') and self._hash_password(pwd) == u['password_hash']
    
    def update_user(self, uid, **kw):
        allowed = ['name','email','preferences','active_model','subscription','api_keys','last_login']
        updates = {k:v for k,v in kw.items() if k in allowed}
        if not updates: return self.get_user(uid)
        if 'preferences' in updates: updates['preferences'] = json.dumps(updates['preferences'])
        if 'api_keys' in updates: updates['api_keys'] = json.dumps(updates['api_keys'])
        updates['updated_at'] = datetime.now().isoformat()
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute(f"UPDATE users SET {','.join(f'{k}=?' for k in updates)} WHERE id=?", list(updates.values()) + [uid])
        return self.get_user(uid)
    
    def create_conversation(self, uid, title='New Chat'):
        import uuid
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO conversations (id,user_id,title) VALUES (?,?,?)", (uuid.uuid4().hex, uid, title))
        return self.get_conversation(uuid.uuid4().hex)
    
    def get_conversation(self, cid):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM conversations WHERE id=?", (cid,))
            r = c.fetchone()
            return dict(r) if r else None
    
    def get_conversations(self, uid, limit=50):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC LIMIT ?", (uid,limit))
            return [dict(r) for r in c.fetchall()]
    
    def add_message(self, cid, role, content, **kw):
        import uuid
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO messages (id,conversation_id,role,content,model_used,directive,metadata) VALUES (?,?,?,?,?,?,?)",
                (uuid.uuid4().hex, cid, role, content, kw.get('model_used'), kw.get('directive'), json.dumps(kw.get('metadata',{}))))
        return {'conversation_id': cid, 'role': role}
    
    def get_conversation_messages(self, cid, limit=100):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC LIMIT ?", (cid,limit))
            return [dict(r) for r in c.fetchall()]
    
    def set_working_memory(self, uid, key, val, ttl=3600):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO memory_working (user_id,key,value,expires_at) VALUES (?,?,?,?)",
                (uid, key, json.dumps(val), (datetime.now()+timedelta(seconds=ttl)).isoformat()))
    
    def get_working_memory(self, uid, key):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM memory_working WHERE user_id=? AND key=? AND (expires_at IS NULL OR expires_at>?)",
                (uid, key, datetime.now().isoformat()))
            r = c.fetchone()
            return json.loads(r['value']) if r else None
    
    def add_episodic_memory(self, uid, etype, summary, details=None, importance=0.5):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO memory_episodic (user_id,event_type,summary,details,importance) VALUES (?,?,?,?,?)",
                (uid, etype, summary, json.dumps(details or {}), importance))
    
    def get_episodic_memories(self, uid, limit=100):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM memory_episodic WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (uid,limit))
            return [dict(r) for r in c.fetchall()]
    
    def add_semantic_memory(self, uid, etype, ename, knowledge, confidence=0.5):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO memory_semantic (user_id,entity_type,entity_name,knowledge,confidence) VALUES (?,?,?,?,?)",
                (uid, etype, ename, knowledge, confidence))
    
    def search_semantic_memory(self, uid, query, limit=10):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM memory_semantic WHERE user_id=? AND (entity_name LIKE ? OR knowledge LIKE ?) ORDER BY confidence DESC LIMIT ?",
                (uid, f'%{query}%', f'%{query}%', limit))
            return [dict(r) for r in c.fetchall()]
    
    def create_agent(self, uid, name, role=None, **kw):
        import uuid
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO agents (id,user_id,name,role,personality,tools,status) VALUES (?,?,?,?,?,?,?)",
                (uuid.uuid4().hex, uid, name, role, json.dumps(kw.get('personality',{})), json.dumps(kw.get('tools',[])), 'idle'))
        return self.get_agent(uuid.uuid4().hex)
    
    def get_agent(self, aid):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM agents WHERE id=?", (aid,))
            r = c.fetchone()
            return dict(r) if r else None
    
    def update_agent(self, aid, **kw):
        updates = {k:v for k,v in kw.items() if k in ['name','role','personality','tools','status','last_active']}
        if 'tools' in updates: updates['tools'] = json.dumps(updates['tools'])
        updates['updated_at'] = datetime.now().isoformat()
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute(f"UPDATE agents SET {','.join(f'{k}=?' for k in updates)} WHERE id=?", list(updates.values()) + [aid])
        return self.get_agent(aid)
    
    def get_audit_logs(self, uid=None, limit=100):
        with self._get_conn() as conn:
            c = conn.cursor()
            if uid:
                c.execute("SELECT * FROM audit_logs WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (uid,limit))
            else:
                c.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in c.fetchall()]
    
    def persist_event(self, etype, priority=3, source=None, data=None):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO events (event_type,priority,source,data) VALUES (?,?,?,?)", (etype, priority, source, json.dumps(data or {})))
    
    def get_events(self, etype=None, limit=100):
        with self._get_conn() as conn:
            c = conn.cursor()
            if etype:
                c.execute("SELECT * FROM events WHERE event_type=? ORDER BY created_at DESC LIMIT ?", (etype,limit))
            else:
                c.execute("SELECT * FROM events ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in c.fetchall()]

_db = None
def get_db(path=None):
    global _db
    if _db is None: _db = Database(path)
    return _db

def init_db(path=None):
    global _db
    _db = Database(path)
    return _db
