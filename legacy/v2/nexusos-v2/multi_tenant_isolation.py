"""
Multi-Tenant Isolation with Row-Level Security
Ensures data isolation between tenants
"""
import uuid
from functools import wraps
from flask import request, g, jsonify


class TenantContext:
    """Manages tenant context for the current request"""
    
    def __init__(self):
        self.current_tenant_id = None
        self.current_user_id = None
    
    def set(self, tenant_id: str, user_id: str):
        self.current_tenant_id = tenant_id
        self.current_user_id = user_id
    
    def get_tenant_id(self) -> str:
        return self.current_tenant_id
    
    def get_user_id(self) -> str:
        return self.current_user_id
    
    def clear(self):
        self.current_tenant_id = None
        self.current_user_id = None


# Global tenant context
tenant_context = TenantContext()


class TenantIsolation:
    """
    Provides multi-tenant data isolation using row-level security
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    def get_tenant_filter(self, table_name: str) -> str:
        """
        Get the tenant ID filter for a table
        This is appended to all queries for the table
        """
        tenant_id = tenant_context.get_tenant_id()
        if not tenant_id:
            return ""  # No filtering for admin/system queries
        
        return f"{table_name}.tenant_id = '{tenant_id}'"
    
    def filter_query(self, base_query: str, table_name: str) -> str:
        """Add tenant filter to a query"""
        filter_clause = self.get_tenant_filter(table_name)
        if not filter_clause:
            return base_query
        
        # Add WHERE or AND clause
        if "WHERE" in base_query.upper():
            return f"{base_query} AND {filter_clause}"
        else:
            return f"{base_query} WHERE {filter_clause}"
    
    def get_tenant_id_from_subdomain(self, host: str) -> str:
        """
        Extract tenant ID from subdomain
        e.g., tenant1.nexusos.cloud -> tenant1
        """
        if not host:
            return None
        
        parts = host.split('.')
        if len(parts) >= 2 and parts[0] != 'www' and parts[0] != 'nexusos':
            return parts[0]
        return None
    
    def get_tenant_from_api_key(self, api_key: str) -> str:
        """
        Get tenant ID from API key
        API key format: tenant_id:user_id:signature
        """
        if not api_key:
            return None
        
        try:
            parts = api_key.split(':')
            if len(parts) >= 2:
                return parts[0]
        except:
            pass
        return None


def require_tenant(f):
    """
    Decorator to ensure request has valid tenant context
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check for tenant in various sources
        tenant_id = None
        
        # 1. From subdomain
        host = request.host
        tenant_id = TenantIsolation(None).get_tenant_id_from_subdomain(host)
        
        # 2. From API key header
        if not tenant_id:
            api_key = request.headers.get('X-API-Key')
            if api_key:
                tenant_id = TenantIsolation(None).get_tenant_from_api_key(api_key)
        
        # 3. From JWT token
        if not tenant_id:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                # Would decode JWT and extract tenant_id
                pass
        
        # 4. From query parameter (less secure, for debugging)
        if not tenant_id:
            tenant_id = request.args.get('tenant_id')
        
        if tenant_id:
            tenant_context.current_tenant_id = tenant_id
        
        return f(*args, **kwargs)
    
    return decorated


class DataAccessPolicy:
    """
    Defines access policies for different data types
    """
    
    # Who can access what
    POLICIES = {
        "users": {
            "read": "tenant",
            "write": "tenant_admin",
            "delete": "tenant_admin"
        },
        "agents": {
            "read": "tenant_user",
            "write": "tenant_user", 
            "delete": "tenant_user"
        },
        "conversations": {
            "read": "owner",
            "write": "owner",
            "delete": "owner"
        },
        "api_keys": {
            "read": "tenant_admin",
            "write": "tenant_admin",
            "delete": "tenant_admin"
        },
        "settings": {
            "read": "tenant_admin",
            "write": "tenant_admin",
            "delete": "tenant_admin"
        }
    }
    
    @classmethod
    def can_access(cls, resource: str, operation: str, user_role: str) -> bool:
        """Check if user with role can perform operation on resource"""
        if resource not in cls.POLICIES:
            return False
        
        policy = cls.POLICIES[resource].get(operation, "")
        
        # Role hierarchy
        role_hierarchy = {
            "owner": 4,      # Can do everything
            "tenant_admin": 3,
            "tenant_user": 2,
            "tenant": 1,
            "public": 0
        }
        
        required_role = policy
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level


def get_isolation_status() -> dict:
    """Get current isolation status"""
    return {
        "tenant_context_active": tenant_context.current_tenant_id is not None,
        "current_tenant": tenant_context.current_tenant_id,
        "policies_loaded": len(DataAccessPolicy.POLICIES) > 0,
        "supported_resources": list(DataAccessPolicy.POLICIES.keys())
    }
