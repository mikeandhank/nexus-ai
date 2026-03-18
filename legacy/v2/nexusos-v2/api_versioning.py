"""
API Versioning Module
====================
Version API endpoints for backward compatibility
"""
from functools import wraps
from flask import request, jsonify, g
import re


class APIVersioner:
    """
    Handle API versioning via URL path or headers
    """
    
    CURRENT_VERSION = "v1"
    SUPPORTED_VERSIONS = ["v1"]
    
    # Version deprecation schedule
    DEPRECATED = {
        # "v0": "2026-03-01"  # Example
    }
    
    @classmethod
    def get_version(cls) -> str:
        """Get API version from request"""
        # Check URL path first: /api/v1/...
        match = re.match(r'/api/(v\d+)/', request.path)
        if match:
            return match.group(1)
        
        # Check header
        version = request.headers.get('X-API-Version')
        if version in cls.SUPPORTED_VERSIONS:
            return version
        
        # Default to current
        return cls.CURRENT_VERSION
    
    @classmethod
    def check_version(cls, version: str) -> tuple:
        """Check if version is valid"""
        if version not in cls.SUPPORTED_VERSIONS:
            return False, f"Unsupported API version. Supported: {', '.join(cls.SUPPORTED_VERSIONS)}"
        
        if version in cls.DEPRECATED:
            return False, f"API version {version} was deprecated on {cls.DEPRECATED[version]}"
        
        return True, None
    
    @classmethod
    def version_required(cls, version: str = None):
        """Decorator to require specific version"""
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                requested = version or cls.get_version()
                valid, error = cls.check_version(requested)
                
                if not valid:
                    return jsonify({"error": error, "code": "VERSION_INVALID"}), 400
                
                g.api_version = requested
                return f(*args, **kwargs)
            return wrapped
        return decorator


# Response formatter for consistent API responses
def api_response(data=None, error=None, meta=None, version: str = None):
    """Format consistent API response"""
    response = {}
    
    if data is not None:
        response["data"] = data
    
    if error:
        response["error"] = error
        response["success"] = False
    else:
        response["success"] = True
    
    if meta:
        response["meta"] = meta
    
    # Add version info
    version = version or APIVersioner.get_version()
    response["version"] = version
    
    return jsonify(response)


def paginate(query, page: int = 1, per_page: int = 20):
    """Paginate database queries"""
    offset = (page - 1) * per_page
    
    # Get total count
    count_query = query.statement.with_only_columns(query.column_descriptions[0].type)
    total = len(query.all())  # Simple count
    
    # Get page
    items = query.limit(per_page).offset(offset).all()
    
    return {
        "items": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


# Example endpoint structure:
#
# @app.route('/api/v1/agents', methods=['GET'])
# @APIVersioner.version_required('v1')
# def list_agents():
#     agents = get_agents()
#     return api_response(data=agents)
#
# @app.route('/api/v2/agents', methods=['GET'])
# @APIVersioner.version_required('v2')
# def list_agents_v2():
#     agents = get_agents()  # Enhanced response
#     return api_response(data=agents)