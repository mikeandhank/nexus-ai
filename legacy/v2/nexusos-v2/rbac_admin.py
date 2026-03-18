"""
RBAC Admin GUI Routes
Admin interface for managing roles and permissions
"""
from flask import Blueprint, jsonify, request
from auth import require_auth, get_current_user
import json

rbac_admin = Blueprint('rbac_admin', __name__)

# In-memory role definitions (would be in database in production)
ROLES = {
    "admin": {
        "name": "Administrator",
        "description": "Full system access",
        "permissions": ["*"]
    },
    "developer": {
        "name": "Developer", 
        "description": "Can manage agents and API",
        "permissions": ["agents:*", "api:*", "logs:read"]
    },
    "user": {
        "name": "User",
        "description": "Standard user access",
        "permissions": ["agents:read", "chat:use"]
    },
    "viewer": {
        "name": "Viewer",
        "description": "Read-only access",
        "permissions": ["agents:read", "logs:read"]
    }
}

PERMISSIONS = {
    "agents:create": "Create new agents",
    "agents:read": "View agents",
    "agents:update": "Update agent configuration", 
    "agents:delete": "Delete agents",
    "agents:*": "Full agent access",
    "api:read": "Read API",
    "api:write": "Write API",
    "api:*": "Full API access",
    "users:manage": "Manage users",
    "users:read": "View users",
    "logs:read": "View logs",
    "logs:write": "Write logs",
    "settings:read": "View settings",
    "settings:write": "Modify settings",
    "billing:read": "View billing",
    "billing:manage": "Manage billing",
    "*": "Superuser access"
}


@rbac_admin.route('/api/admin/roles', methods=['GET'])
@require_auth
def list_roles():
    """List all available roles"""
    user = get_current_user()
    if user.get('role') != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    return jsonify({
        "roles": ROLES,
        "permissions": PERMISSIONS
    })


@rbac_admin.route('/api/admin/roles', methods=['POST'])
@require_auth
def create_role():
    """Create a new role"""
    user = get_current_user()
    if user.get('role') != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    data = request.json
    role_name = data.get('name')
    
    if not role_name:
        return jsonify({"error": "Role name required"}), 400
    
    if role_name in ROLES:
        return jsonify({"error": "Role already exists"}), 400
    
    ROLES[role_name] = {
        "name": data.get('display_name', role_name),
        "description": data.get('description', ''),
        "permissions": data.get('permissions', [])
    }
    
    return jsonify({"role": ROLES[role_name]}), 201


@rbac_admin.route('/api/admin/roles/<role_name>', methods=['PUT'])
@require_auth
def update_role(role_name):
    """Update an existing role"""
    user = get_current_user()
    if user.get('role') != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    if role_name not in ROLES:
        return jsonify({"error": "Role not found"}), 404
    
    data = request.json
    ROLES[role_name].update({
        "name": data.get('display_name', ROLES[role_name]['name']),
        "description": data.get('description', ROLES[role_name]['description']),
        "permissions": data.get('permissions', ROLES[role_name]['permissions'])
    })
    
    return jsonify({"role": ROLES[role_name]})


@rbac_admin.route('/api/admin/roles/<role_name>', methods=['DELETE'])
@require_auth
def delete_role(role_name):
    """Delete a role"""
    user = get_current_user()
    if user.get('role') != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    if role_name not in ROLES:
        return jsonify({"error": "Role not found"}), 404
    
    if role_name == 'admin':
        return jsonify({"error": "Cannot delete admin role"}), 400
    
    del ROLES[role_name]
    return jsonify({"message": "Role deleted"})


@rbac_admin.route('/api/admin/users', methods=['GET'])
@require_auth
def list_users():
    """List all users (admin only)"""
    user = get_current_user()
    if user.get('role') != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    # This would fetch from database
    return jsonify({
        "users": [
            {"id": "sample-user-id", "email": "admin@example.com", "role": "admin"},
            {"id": "sample-user-id-2", "email": "user@example.com", "role": "user"}
        ]
    })


@rbac_admin.route('/api/admin/users/<user_id>/role', methods=['PUT'])
@require_auth
def update_user_role(user_id):
    """Update a user's role"""
    user = get_current_user()
    if user.get('role') != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    data = request.json
    new_role = data.get('role')
    
    if new_role not in ROLES:
        return jsonify({"error": "Invalid role"}), 400
    
    # This would update database
    return jsonify({
        "message": "User role updated",
        "user_id": user_id,
        "role": new_role
    })


@rbac_admin.route('/api/admin/permissions/check', methods=['POST'])
@require_auth
def check_permission():
    """Check if user has specific permission"""
    user = get_current_user()
    data = request.json
    permission = data.get('permission')
    
    if not permission:
        return jsonify({"error": "Permission required"}), 400
    
    user_role = user.get('role', 'viewer')
    role_perms = ROLES.get(user_role, {}).get('permissions', [])
    
    has_permission = (
        '*' in role_perms or 
        permission in role_perms or
        permission.split(':')[0] + ':*' in role_perms
    )
    
    return jsonify({
        "user_id": user.get('user_id'),
        "role": user_role,
        "permission": permission,
        "allowed": has_permission
    })
