"""
SSO/OAuth2 Integration Module
Provides SSO with Okta, Azure AD, Google, and other OAuth providers
"""
from flask import Blueprint, redirect, request, jsonify, session
import requests
import secrets
import hashlib
import urllib.parse
from functools import wraps

sso = Blueprint('sso', __name__)

# SSO Configuration (would come from database in production)
SSO_PROVIDERS = {
    "okta": {
        "type": "oauth2",
        "authorization_url": "https://{domain}/oauth2/v1/authorize",
        "token_url": "https://{domain}/oauth2/v1/token",
        "userinfo_url": "https://{domain}/oauth2/v1/userinfo",
        "scope": "openid profile email"
    },
    "azure": {
        "type": "oauth2",
        "authorization_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "scope": "openid profile email User.Read"
    },
    "google": {
        "type": "oauth2",
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid profile email"
    },
    "github": {
        "type": "oauth2",
        "authorization_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email"
    }
}


class SSOClient:
    """OAuth2/OIDC client for SSO"""
    
    def __init__(self, provider: str, config: dict):
        self.provider = provider
        self.config = config
        self.state = secrets.token_urlsafe(32)
        
    def get_authorization_url(self, client_id: str, redirect_uri: str, 
                               domain: str = None, tenant: str = None) -> str:
        """Generate authorization URL"""
        provider_config = SSO_PROVIDERS[self.provider]
        
        url_template = provider_config["authorization_url"]
        if domain:
            url_template = url_template.format(domain=domain)
        if tenant:
            url_template = url_template.format(tenant=tenant)
            
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": provider_config["scope"],
            "state": self.state
        }
        
        return f"{url_template}?{urllib.parse.urlencode(params)}"
    
    def exchange_code(self, code: str, client_id: str, client_secret: str,
                      redirect_uri: str, domain: str = None, tenant: str = None) -> dict:
        """Exchange authorization code for tokens"""
        provider_config = SSO_PROVIDERS[self.provider]
        
        url_template = provider_config["token_url"]
        if domain:
            url_template = url_template.format(domain=domain)
        if tenant:
            url_template = url_template.format(tenant=tenant)
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        resp = requests.post(url_template, data=data)
        resp.raise_for_status()
        
        return resp.json()
    
    def get_userinfo(self, access_token: str, domain: str = None) -> dict:
        """Get user info from provider"""
        provider_config = SSO_PROVIDERS[self.provider]
        
        url = provider_config["userinfo_url"]
        if domain:
            url = url.format(domain=domain)
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        
        userdata = resp.json()
        
        # Normalize user data
        return {
            "email": userdata.get("email") or userdata.get("mail"),
            "name": userdata.get("name") or userdata.get("displayName"),
            "sub": userdata.get("sub") or userdata.get("id"),
            "picture": userdata.get("picture") or userdata.get("avatar_url")
        }


# Routes
@sso.route('/api/auth/sso/authorize/<provider>', methods=['GET'])
def sso_authorize(provider):
    """Initiate SSO login"""
    if provider not in SSO_PROVIDERS:
        return jsonify({"error": "Unknown provider"}), 400
    
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri', request.host_url + 'api/auth/sso/callback')
    domain = request.args.get('domain')
    tenant = request.args.get('tenant')
    
    if not client_id:
        return jsonify({"error": "client_id required"}), 400
    
    client = SSOClient(provider, SSO_PROVIDERS[provider])
    auth_url = client.get_authorization_url(client_id, redirect_uri, domain, tenant)
    
    # Store state for verification
    session['sso_state'] = client.state
    session['sso_provider'] = provider
    
    return redirect(auth_url)


@sso.route('/api/auth/sso/callback', methods=['GET'])
def sso_callback():
    """Handle SSO callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        return jsonify({"error": error}), 400
    
    if state != session.get('sso_state'):
        return jsonify({"error": "Invalid state"}), 400
    
    provider = session.get('sso_provider')
    client_id = request.args.get('client_id')
    client_secret = request.args.get('client_secret')
    redirect_uri = request.args.get('redirect_uri')
    domain = request.args.get('domain')
    tenant = request.args.get('tenant')
    
    try:
        client = SSOClient(provider, SSO_PROVIDERS[provider])
        tokens = client.exchange_code(code, client_id, client_secret, redirect_uri, domain, tenant)
        userinfo = client.get_userinfo(tokens['access_token'], domain, tenant)
        
        # Here you would create/update user in database
        # And issue a session/JWT
        
        return jsonify({
            "message": "SSO login successful",
            "user": userinfo,
            "access_token": tokens.get('access_token')
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sso.route('/api/auth/sso/providers', methods=['GET'])
def list_providers():
    """List available SSO providers"""
    return jsonify({
        "providers": list(SSO_PROVIDERS.keys())
    })
