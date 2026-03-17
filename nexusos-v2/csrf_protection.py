"""
CSRF Protection Module
======================
Enterprise-grade CSRF protection for Flask
"""
import os
import secrets
import time
from functools import wraps
from flask import session, request, jsonify, g


class CSRFProtection:
    """
    CSRF protection using double-submit cookie pattern
    """
    
    def __init__(self, app=None):
        self.app = app
        self.token_name = 'csrf_token'
        self.header_name = 'X-CSRF-Token'
        self.token_expiry = 3600  # 1 hour
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        app.before_request(self._check_token)
    
    def generate_token(self) -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)
    
    def get_token(self) -> str:
        """Get or create CSRF token for session"""
        if self.token_name not in session:
            session[self.token_name] = self.generate_token()
            session[f"{self.token_name}_time"] = time.time()
        
        # Check expiry
        token_time = session.get(f"{self.token_name}_time", 0)
        if time.time() - token_time > self.token_expiry:
            session[self.token_name] = self.generate_token()
            session[f"{self.token_name}_time"] = time.time()
        
        return session[self.token_name]
    
    def _check_token(self):
        """Check CSRF token before request"""
        # Skip for safe methods
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return None
        
        # Skip for non-state-changing endpoints
        safe_endpoints = ['/api/status', '/api/health', '/mcp/tools']
        if any(request.path.startswith(p) for p in safe_endpoints):
            return None
        
        # Get token from header
        token = request.headers.get(self.header_name)
        
        if not token:
            return jsonify({
                'error': 'CSRF_TOKEN_MISSING',
                'message': 'CSRF token required for this request'
            }), 403
        
        # Validate token
        session_token = session.get(self.token_name)
        
        if not session_token or token != session_token:
            return jsonify({
                'error': 'CSRF_TOKEN_INVALID',
                'message': 'Invalid CSRF token'
            }), 403
        
        return None
    
    def inject_token(self, response):
        """Inject CSRF token into response"""
        if request.method == 'GET':
            response.set_cookie(
                self.token_name,
                self.get_token(),
                httponly=False,  # JavaScript needs to read this
                secure=request.is_secure,
                samesite='Lax'
            )
        return response


def csrf_exempt(f):
    """Decorator to exempt endpoint from CSRF"""
    f.csrf_exempt = True
    return f


def get_csrf_token() -> str:
    """Get CSRF token for current session"""
    csrf = g.get('csrf_protection')
    if csrf:
        return csrf.get_token()
    return ''