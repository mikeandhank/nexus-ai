"""
NexusOS SSO/OAuth2 Integration
Support for enterprise identity providers (Google, GitHub, Microsoft, Okta).
"""

import os
import requests
from flask import jsonify, redirect, request, session
from urllib.parse import urlencode

# OAuth2 Configuration
OAUTH_CONFIG = {
    'google': {
        'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
        'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'user_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
        'scope': 'openid email profile'
    },
    'github': {
        'client_id': os.environ.get('GITHUB_CLIENT_ID', ''),
        'client_secret': os.environ.get('GITHUB_CLIENT_SECRET', ''),
        'auth_url': 'https://github.com/login/oauth/authorize',
        'token_url': 'https://github.com/login/oauth/access_token',
        'user_url': 'https://api.github.com/user',
        'scope': 'user:email'
    },
    'microsoft': {
        'client_id': os.environ.get('MICROSOFT_CLIENT_ID', ''),
        'client_secret': os.environ.get('MICROSOFT_CLIENT_SECRET', ''),
        'auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        'user_url': 'https://graph.microsoft.com/v1.0/me',
        'scope': 'openid email User.Read'
    }
}


def setup_sso_routes(app):
    """Add SSO/OAuth2 routes"""
    
    @app.route('/api/auth/sso/<provider>', methods=['GET'])
    def sso_login(provider):
        """Start SSO login"""
        if provider not in OAUTH_CONFIG:
            return jsonify({'error': 'Provider not supported'}), 400
        
        config = OAUTH_CONFIG[provider]
        if not config['client_id']:
            return jsonify({'error': 'Provider not configured'}), 400
        
        # Generate state for CSRF protection
        import uuid
        state = str(uuid.uuid4())
        session['oauth_state'] = state
        session['oauth_provider'] = provider
        
        # Build auth URL
        params = {
            'client_id': config['client_id'],
            'redirect_uri': f"{request.host_url}api/auth/sso/callback",
            'response_type': 'code',
            'scope': config['scope'],
            'state': state
        }
        
        auth_url = f"{config['auth_url']}?{urlencode(params)}"
        return redirect(auth_url)
    
    @app.route('/api/auth/sso/callback', methods=['GET'])
    def sso_callback():
        """Handle SSO callback"""
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            return redirect(f"/ui/login?error={error}")
        
        if state != session.get('oauth_state'):
            return redirect("/ui/login?error=invalid_state")
        
        provider = session.get('oauth_provider')
        if not provider or provider not in OAUTH_CONFIG:
            return redirect("/ui/login?error=invalid_provider")
        
        config = OAUTH_CONFIG[provider]
        
        try:
            # Exchange code for token
            token_response = requests.post(config['token_url'], data={
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': f"{request.host_url}api/auth/sso/callback'
            })
            token_data = token_response.json()
            
            if 'error' in token_data:
                return redirect(f"/ui/login?error={token_data.get('error_description', 'token_error')}")
            
            access_token = token_data.get('access_token')
            
            # Get user info
            headers = {'Authorization': f'Bearer {access_token}'}
            user_response = requests.get(config['user_url'], headers=headers)
            user_data = user_response.json()
            
            # Extract email and name
            email = user_data.get('email') or user_data.get('mail')
            name = user_data.get('name') or user_data.get('login')
            
            if not email:
                return redirect("/ui/login?error=no_email")
            
            # Find or create user in our DB
            from api_server_v5 import get_user_by_email, create_user
            
            user = get_user_by_email(email)
            if not user:
                # Auto-register SSO user
                import uuid
                user_id = str(uuid.uuid4())
                import hashlib
                password_hash = hashlib.sha256(f"{access_token}{state}".encode()).hexdigest()
                user = create_user(user_id, email, password_hash, name or 'SSO User')
            
            # Create JWT token
            from api_server_v5 import create_access_token, create_refresh_token
            
            access = create_access_token(user['id'], user.get('role', 'user'))
            refresh = create_refresh_token(user['id'])
            
            # Redirect to UI with token
            return redirect(f"/ui/sso?{urlencode({'token': access, 'refresh': refresh, 'name': name or email})}")
            
        except Exception as e:
            return redirect(f"/ui/login?error=callback_error")
    
    @app.route('/api/auth/sso/status', methods=['GET'])
    def sso_status():
        """Get SSO configuration status"""
        status = {}
        for provider, config in OAUTH_CONFIG.items():
            status[provider] = {
                'enabled': bool(config['client_id']),
                'configured': bool(config['client_id'] and config['client_secret'])
            }
        return jsonify({'providers': status})
    
    print("[NexusOS] SSO/OAuth2 routes enabled")
