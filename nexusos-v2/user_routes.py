"""
User Management API Routes
Provides CRUD operations for user management (enterprise feature)
"""
from flask import jsonify, request, g
from auth import require_auth
from database_compat import DatabaseCompat as Database

_db = Database()

def setup_user_routes(app):
    
    @app.route('/api/users', methods=['GET'])
    @require_auth
    def list_users():
        """List all users (admin only)"""
        # Check admin role
        if g.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        
        # Get query params
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # For now, we'd need a list_all_users method
        # Using a workaround - could add to database layer
        # Return empty list for now with count
        return jsonify({
            "users": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        })
    
    @app.route('/api/users/<user_id>', methods=['GET'])
    @require_auth
    def get_user(user_id):
        """Get user details"""
        # Users can only view their own profile unless admin
        if g.get('role') != 'admin' and g.user_id != user_id:
            return jsonify({"error": "Forbidden"}), 403
        
        user = _db.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "id": user.get('id'),
            "email": user.get('email'),
            "name": user.get('name'),
            "role": user.get('role'),
            "created_at": user.get('created_at')
        })
    
    @app.route('/api/users/<user_id>', methods=['PUT'])
    @require_auth
    def update_user(user_id):
        """Update user details"""
        # Users can only update their own profile unless admin
        if g.get('role') != 'admin' and g.user_id != user_id:
            return jsonify({"error": "Forbidden"}), 403
        
        data = request.json or {}
        
        # Non-admins cannot change their own role
        if 'role' in data and g.get('role') != 'admin':
            del data['role']
        
        # Cannot change other user's role unless admin
        if g.get('role') != 'admin' and 'role' in data:
            del data['role']
        
        # Prevent changing id or email through this endpoint
        data.pop('id', None)
        data.pop('email', None)
        
        if not data:
            return jsonify({"error": "No valid fields to update"}), 400
        
        success = _db.update_user(user_id, **data)
        if not success:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({"message": "User updated", "user_id": user_id})
    
    @app.route('/api/users/<user_id>', methods=['DELETE'])
    @require_auth
    def delete_user(user_id):
        """Delete user (admin only)"""
        if g.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        
        # Prevent deleting self
        if g.user_id == user_id:
            return jsonify({"error": "Cannot delete yourself"}), 400
        
        # Would need delete_user method in database
        # For now, return not implemented
        return jsonify({"error": "Delete not implemented yet"}), 501
    
    @app.route('/api/users/<user_id>/role', methods=['PUT'])
    @require_auth
    def update_user_role(user_id):
        """Update user role (admin only)"""
        if g.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        
        data = request.json or {}
        new_role = data.get('role')
        
        if not new_role:
            return jsonify({"error": "role is required"}), 400
        
        valid_roles = ['user', 'admin', 'viewer']
        if new_role not in valid_roles:
            return jsonify({"error": f"Invalid role. Must be one of: {valid_roles}"}), 400
        
        success = _db.update_user(user_id, role=new_role)
        if not success:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "message": "Role updated",
            "user_id": user_id,
            "new_role": new_role
        })
    
    return app
