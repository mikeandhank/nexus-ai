"""
Custom RBAC API - Enterprise Role-Based Access Control
====================================================
Allows enterprises to define custom roles beyond the 4 static ones.
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomRBAC:
    """
    Enterprise Custom RBAC
    
    Allows:
    - Custom role definitions
    - Role hierarchies
    - Permission sets
    - Resource-level access
    - Enterprise organization mapping
    """
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.environ.get('DATABASE_URL',
            'postgresql://nexusos:nexusos@localhost:5432/nexusos')
        self._init_db()
    
    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def _init_db(self):
        """Initialize RBAC tables"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Custom roles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rbac_roles (
                role_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                parent_role_id TEXT,
                permissions JSONB DEFAULT '[]',
                is_system BOOLEAN DEFAULT FALSE,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Role assignments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rbac_assignments (
                assignment_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                resource_scope TEXT,  # For org-level scoping
                granted_by TEXT,
                granted_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP,
                UNIQUE(user_id, role_id, resource_scope)
            )
        """)
        
        # Permission definitions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rbac_permissions (
                permission_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                resource_type TEXT,  # agent, tool, api, data
                actions JSONB DEFAULT '[]',  # ["read", "write", "delete"]
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Predefined permissions
        cursor.execute("""
            INSERT INTO rbac_permissions (permission_id, name, description, resource_type, actions) VALUES
            ('agent.read', 'Read Agents', 'View agent information', 'agent', '["read"]'),
            ('agent.write', 'Manage Agents', 'Create, update, delete agents', 'agent', '["read", "write", "delete"]'),
            ('agent.execute', 'Execute Agents', 'Run agent tasks', 'agent', '["execute"]'),
            ('tool.read', 'Read Tools', 'View available tools', 'tool', '["read"]'),
            ('tool.use', 'Use Tools', 'Execute tool operations', 'tool', '["use"]'),
            ('api.read', 'Read API', 'Make read API calls', 'api', '["read"]'),
            ('api.write', 'Write API', 'Make write API calls', 'api', '["read", "write"]'),
            ('admin.users', 'Manage Users', 'User administration', 'admin', '["read", "write", "delete"]'),
            ('admin.roles', 'Manage Roles', 'Role administration', 'admin', '["read", "write", "delete"]'),
            ('audit.read', 'Read Audit', 'View audit logs', 'audit', '["read"]')
            ON CONFLICT DO NOTHING
        """)
        
        # Predefined roles (system roles)
        cursor.execute("""
            INSERT INTO rbac_roles (role_id, name, description, is_system, permissions) VALUES
            ('admin', 'Administrator', 'Full system access', TRUE, '["*"]'),
            ('developer', 'Developer', 'Can manage agents and tools', TRUE, '["agent.*", "tool.*", "api.read"]'),
            ('user', 'User', 'Basic user access', TRUE, '["agent.read", "tool.use", "api.read"]'),
            ('viewer', 'Viewer', 'Read-only access', TRUE, '["agent.read", "tool.read", "api.read", "audit.read"]')
            ON CONFLICT DO NOTHING
        """)
        
        conn.commit()
        conn.close()
    
    # ========== ROLE MANAGEMENT ==========
    
    def create_role(self, name: str, description: str = "", 
                   permissions: List[str] = None, parent_role_id: str = None,
                   created_by: str = None) -> Dict:
        """Create a custom role"""
        role_id = f"role_{uuid.uuid4().hex[:12]}"
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO rbac_roles (role_id, name, description, permissions, parent_role_id, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (role_id, name, description, json.dumps(permissions or []), 
              parent_role_id, created_by))
        
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        
        logger.info(f"Created role: {name} ({role_id})")
        return {"success": True, "role": dict(result)}
    
    def get_role(self, role_id: str) -> Optional[Dict]:
        """Get a role by ID"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM rbac_roles WHERE role_id = %s", (role_id,))
        result = cursor.fetchone()
        conn.close()
        
        return dict(result) if result else None
    
    def list_roles(self, include_system: bool = True) -> List[Dict]:
        """List all roles"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM rbac_roles"
        if not include_system:
            query += " WHERE is_system = FALSE"
        
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def update_role(self, role_id: str, updates: Dict) -> Dict:
        """Update a custom role"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        allowed = ["name", "description", "permissions", "parent_role_id"]
        update_fields = []
        values = []
        
        for key, value in updates.items():
            if key in allowed:
                update_fields.append(f"{key} = %s")
                values.append(value if not isinstance(value, list) else json.dumps(value))
        
        if not update_fields:
            return {"success": False, "error": "No valid fields to update"}
        
        values.append(role_id)
        
        cursor.execute(f"""
            UPDATE rbac_roles 
            SET {', '.join(update_fields)}, updated_at = NOW()
            WHERE role_id = %s
            RETURNING *
        """, values)
        
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        
        return {"success": True, "role": dict(result)} if result else {"success": False}
    
    def delete_role(self, role_id: str) -> Dict:
        """Delete a custom role"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Check if system role
        cursor.execute("SELECT is_system FROM rbac_roles WHERE role_id = %s", (role_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            return {"success": False, "error": "Cannot delete system role"}
        
        # Delete assignments first
        cursor.execute("DELETE FROM rbac_assignments WHERE role_id = %s", (role_id,))
        
        # Delete role
        cursor.execute("DELETE FROM rbac_roles WHERE role_id = %s", (role_id,))
        
        conn.commit()
        conn.close()
        
        return {"success": True}
    
    # ========== PERMISSION MANAGEMENT ==========
    
    def list_permissions(self) -> List[Dict]:
        """List all available permissions"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM rbac_permissions ORDER BY resource_type, name")
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    # ========== USER ASSIGNMENTS ==========
    
    def assign_role(self, user_id: str, role_id: str, 
                   resource_scope: str = None, granted_by: str = None,
                   expires_at: datetime = None) -> Dict:
        """Assign a role to a user"""
        assignment_id = f"assign_{uuid.uuid4().hex[:12]}"
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO rbac_assignments 
            (assignment_id, user_id, role_id, resource_scope, granted_by, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, role_id, resource_scope) 
            DO UPDATE SET granted_at = NOW(), granted_by = EXCLUDED.granted_by
            RETURNING *
        """, (assignment_id, user_id, role_id, resource_scope, granted_by, expires_at))
        
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        
        return {"success": True, "assignment": dict(result)}
    
    def revoke_role(self, user_id: str, role_id: str, resource_scope: str = None) -> Dict:
        """Revoke a role from a user"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM rbac_assignments 
            WHERE user_id = %s AND role_id = %s AND (resource_scope = %s OR %s IS NULL)
        """, (user_id, role_id, resource_scope, resource_scope))
        
        conn.commit()
        conn.close()
        
        return {"success": True}
    
    def get_user_roles(self, user_id: str) -> List[Dict]:
        """Get all roles assigned to a user"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT ra.*, rr.name as role_name, rr.permissions
            FROM rbac_assignments ra
            JOIN rbac_roles rr ON ra.role_id = rr.role_id
            WHERE ra.user_id = %s 
            AND (ra.expires_at IS NULL OR ra.expires_at > NOW())
        """, (user_id,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission"""
        roles = self.get_user_roles(user_id)
        
        for role in roles:
            perms = role.get("permissions", [])
            
            # Wildcard check
            if "*" in perms:
                return True
            
            # Direct permission
            if permission in perms:
                return True
            
            # Wildcard matching (e.g., "agent.*" matches "agent.read")
            for perm in perms:
                if perm.endswith(".*") and permission.startswith(perm[:-1]):
                    return True
        
        return False
    
    def check_access(self, user_id: str, resource_type: str, action: str) -> bool:
        """Check if user can perform action on resource type"""
        permission = f"{resource_type}.{action}"
        return self.check_permission(user_id, permission)


# Default system roles
SYSTEM_ROLES = {
    "admin": {
        "description": "Full system access",
        "permissions": ["*"]
    },
    "developer": {
        "description": "Can manage agents and tools",
        "permissions": ["agent.*", "tool.*", "api.read", "audit.read"]
    },
    "user": {
        "description": "Basic user access",
        "permissions": ["agent.read", "tool.use", "api.read"]
    },
    "viewer": {
        "description": "Read-only access",
        "permissions": ["agent.read", "tool.read", "api.read", "audit.read"]
    }
}


# Singleton
_rbac = None

def get_rbac(db_url: str = None) -> CustomRBAC:
    global _rbac
    if _rbac is None:
        _rbac = CustomRBAC(db_url)
    return _rbac
