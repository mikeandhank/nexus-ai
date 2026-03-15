"""
RBAC (Role-Based Access Control) for NexusOS
"""

from functools import wraps
from flask import request, jsonify, g

# Role definitions
ROLES = {
    'admin': {
        'description': 'Full system access',
        'permissions': ['read', 'write', 'delete', 'admin', 'manage_users', 'manage_agents', 'manage_keys']
    },
    'user': {
        'description': 'Standard user access',
        'permissions': ['read', 'write', 'manage_agents']
    },
    'viewer': {
        'description': 'Read-only access',
        'permissions': ['read']
    },
    'developer': {
        'description': 'Developer access',
        'permissions': ['read', 'write', 'manage_agents', 'manage_keys']
    }
}

DEFAULT_ROLE = 'user'

def has_permission(role, permission):
    role_def = ROLES.get(role, ROLES['user'])
    return permission in role_def.get('permissions', [])

def get_user_role(db, user_id):
    import sqlite3
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row['role'] if row else DEFAULT_ROLE
