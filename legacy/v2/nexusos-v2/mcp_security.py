"""
MCP Tool Security Layer
Adds permission scoping and safety checks to MCP tools
"""
import re
import os
from typing import Dict, List, Optional, Any
from functools import wraps


class ToolSecurityPolicy:
    """
    Security policies for MCP tools
    """
    
    # Allowed paths for file operations (sandbox)
    ALLOWED_PATHS = [
        "/app/data/",
        "/tmp/nexusos/",
        "/workspace/"
    ]
    
    # Blocked commands for process_run
    BLOCKED_COMMANDS = [
        r"rm\s+-rf\s+/",
        r"dd\s+if=",
        r"mkfs",
        r":\(\)\{",  # Fork bomb
        r"curl.*\|.*sh",
        r"wget.*\|.*sh",
        r"nc\s+-e",
        r"/dev/tcp/",
        r"curl\s+http://169\.254\.169\.254",
    ]
    
    # Blocked SQL commands
    BLOCKED_SQL = [
        r"DROP\s+DATABASE",
        r"DROP\s+TABLE\s+users",
        r"TRUNCATE",
        r"DELETE\s+FROM\s+users",
        r"ALTER\s+TABLE\s+users",
        r"GRANT\s+ALL",
        r"REVOKE\s+ALL",
    ]
    
    # Blocked URLs for network requests
    BLOCKED_URLS = [
        r"169\.254\.169\.254",
        r"metadata\.google\.internal",
        r"localhost",
        r"127\.0\.0\.1",
        r"0\.0\.0\.0",
        r"::1",
    ]
    
    @classmethod
    def check_path(cls, path: str, allowed_paths: List[str] = None) -> bool:
        """Check if path is within allowed directories"""
        if allowed_paths is None:
            allowed_paths = cls.ALLOWED_PATHS
            
        abs_path = os.path.abspath(path)
        
        for allowed in allowed_paths:
            if abs_path.startswith(allowed):
                return True
        return False
    
    @classmethod
    def check_command(cls, command: str) -> tuple:
        """Check if command is blocked"""
        for pattern in cls.BLOCKED_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Blocked command pattern: {pattern}"
        return True, ""
    
    @classmethod
    def check_sql(cls, query: str) -> tuple:
        """Check if SQL query is safe"""
        for pattern in cls.BLOCKED_SQL:
            if re.search(pattern, query, re.IGNORECASE):
                return False, f"Blocked SQL pattern: {pattern}"
        return True, ""
    
    @classmethod
    def check_url(cls, url: str) -> tuple:
        """Check if URL is safe (no SSRF)"""
        for pattern in cls.BLOCKED_URLS:
            if re.search(pattern, url, re.IGNORECASE):
                return False, f"Blocked URL pattern: {pattern}"
        return True, ""


class AgentPermission:
    """
    Defines what an agent is allowed to access
    """
    
    def __init__(
        self,
        agent_id: str,
        allowed_paths: List[str] = None,
        allowed_docker_containers: List[str] = None,
        can_execute_commands: bool = False,
        can_access_database: bool = False,
        can_make_network_calls: bool = False,
        database_allowed_tables: List[str] = None,
        max_execution_time: int = 30
    ):
        self.agent_id = agent_id
        self.allowed_paths = allowed_paths or ["/app/data/", "/tmp/nexusos/"]
        self.allowed_docker_containers = allowed_docker_containers or []
        self.can_execute_commands = can_execute_commands
        self.can_access_database = can_access_database
        self.can_make_network_calls = can_make_network_calls
        self.database_allowed_tables = database_allowed_tables or []
        self.max_execution_time = max_execution_time


def require_permission(permission: str):
    """
    Decorator to check agent permissions before executing a tool
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get agent context (would come from request)
            agent_perm = get_agent_permission()
            
            if permission == "execute" and not agent_perm.can_execute_commands:
                return {"error": "Agent not permitted to execute commands"}
            
            if permission == "database" and not agent_perm.can_access_database:
                return {"error": "Agent not permitted to access database"}
            
            if permission == "network" and not agent_perm.can_make_network_calls:
                return {"error": "Agent not permitted to make network calls"}
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global agent context
_current_agent_permission = None

def set_agent_permission(perm: AgentPermission):
    global _current_agent_permission
    _current_agent_permission = perm

def get_agent_permission() -> AgentPermission:
    global _current_agent_permission
    if _current_agent_permission is None:
        # Default restrictive permissions
        _current_agent_permission = AgentPermission(
            agent_id="default",
            allowed_paths=["/tmp/nexusos/"],
            can_execute_commands=False,
            can_access_database=False,
            can_make_network_calls=False
        )
    return _current_agent_permission


def secure_file_operation(operation: str, path: str, **kwargs) -> Dict:
    """
    Wrapper for file operations with security checks
    """
    policy = ToolSecurityPolicy()
    
    # Check path
    if not policy.check_path(path, get_agent_permission().allowed_paths):
        return {
            "error": f"Path not allowed: {path}",
            "allowed_paths": get_agent_permission().allowed_paths
        }
    
    # For write/delete, additional checks
    if operation in ["write", "delete"]:
        # Check for dangerous paths
        dangerous = ["/etc/", "/var/", "/root/", "/home/", "/usr/bin/", "/usr/sbin/"]
        for d in dangerous:
            if path.startswith(d):
                return {"error": f"Cannot modify system path: {path}"}
    
    return None  # Pass through


def secure_process_run(command: str) -> Dict:
    """
    Wrapper for process execution with security checks
    """
    policy = ToolSecurityPolicy()
    perm = get_agent_permission()
    
    if not perm.can_execute_commands:
        return {"error": "Agent not permitted to execute commands"}
    
    # Check command
    safe, error = policy.check_command(command)
    if not safe:
        return {"error": f"Command blocked: {error}"}
    
    # Check execution time
    if perm.max_execution_time:
        # Would enforce timeout in actual execution
        pass
    
    return None  # Pass through


def secure_db_query(query: str) -> Dict:
    """
    Wrapper for database queries with security checks
    """
    policy = ToolSecurityPolicy()
    perm = get_agent_permission()
    
    if not perm.can_access_database:
        return {"error": "Agent not permitted to access database"}
    
    # Check SQL
    safe, error = policy.check_sql(query)
    if not safe:
        return {"error": f"Query blocked: {error}"}
    
    # If table restrictions exist, check them
    if perm.database_allowed_tables:
        # Extract table from query
        tables = re.findall(r"FROM\s+(\w+)", query, re.IGNORECASE)
        for table in tables:
            if table not in perm.database_allowed_tables:
                return {"error": f"Table not allowed: {table}"}
    
    return None


def secure_network_call(url: str) -> Dict:
    """
    Wrapper for network calls with security checks (SSRF prevention)
    """
    policy = ToolSecurityPolicy()
    perm = get_agent_permission()
    
    if not perm.can_make_network_calls:
        return {"error": "Agent not permitted to make network calls"}
    
    # Check URL
    safe, error = policy.check_url(url)
    if not safe:
        return {"error": f"URL blocked: {error}"}
    
    return None


def secure_docker_operation(container: str, operation: str) -> Dict:
    """
    Wrapper for Docker operations with scope checks
    """
    perm = get_agent_permission()
    
    if not perm.allowed_docker_containers:
        return {"error": "Agent not permitted to manage Docker"}
    
    if container not in perm.allowed_docker_containers:
        return {
            "error": f"Container not allowed: {container}",
            "allowed_containers": perm.allowed_docker_containers
        }
    
    return None
