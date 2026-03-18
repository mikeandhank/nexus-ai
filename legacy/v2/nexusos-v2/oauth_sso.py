"""
OAuth2/SSO Integration - Enterprise Single Sign-On
==================================================
Supports Okta, Azure AD, Google Workspace via OAuth2/OIDC.
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OAuthProvider:
    """OAuth2/OIDC Provider Configuration"""
    provider_id: str
    name: str  # "okta", "azure", "google"
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: List[str]
    redirect_uri: str
    
    # Provider-specific
    domain: str = ""  # For Okta/Azure tenant
    tenant_id: str = ""  # For Azure
    
    enabled: bool = True


class OAuth2Manager:
    """
    OAuth2/OIDC SSO Manager
    
    Supports:
    - Okta
    - Azure AD
    - Google Workspace
    - Generic OIDC providers
    """
    
    # Supported providers
    PROVIDERS = {
        "okta": {
            "authorize_url": "https://{domain}/oauth2/v1/authorize",
            "token_url": "https://{domain}/oauth2/v1/token",
            "userinfo_url": "https://{domain}/oauth2/v1/userinfo",
            "scopes": ["openid", "profile", "email", "groups"]
        },
        "azure": {
            "authorize_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
            "scopes": ["openid", "profile", "email", "User.Read"]
        },
        "google": {
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
            "scopes": ["openid", "profile", "email"]
        }
    }
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.environ.get('NEXUSOS_URL', 'https://nexusos.cloud')
        self.providers: Dict[str, OAuthProvider] = {}
        self.sessions: Dict[str, Dict] = {}  # State -> session info
        
        # Load configured providers
        self._load_providers()
    
    def _load_providers(self):
        """Load providers from environment or config"""
        # Check for configured providers
        for provider_name in ["okta", "azure", "google"]:
            client_id = os.environ.get(f"{provider_name.upper()}_CLIENT_ID")
            client_secret = os.environ.get(f"{provider_name.upper()}_CLIENT_SECRET")
            
            if client_id and client_secret:
                config = self.PROVIDERS[provider_name]
                
                provider = OAuthProvider(
                    provider_id=provider_name,
                    name=provider_name.title(),
                    client_id=client_id,
                    client_secret=client_secret,
                    authorize_url=config["authorize_url"],
                    token_url=config["token_url"],
                    userinfo_url=config["userinfo_url"],
                    scopes=config["scopes"],
                    redirect_uri=f"{self.base_url}/auth/oauth/callback",
                    domain=os.environ.get(f"{provider_name.upper()}_DOMAIN", ""),
                    tenant_id=os.environ.get(f"{provider_name.upper()}_TENANT", "")
                )
                
                self.providers[provider_name] = provider
                logger.info(f"Loaded OAuth provider: {provider_name}")
    
    def add_provider(self, provider: OAuthProvider) -> Dict:
        """Add a new OAuth provider"""
        self.providers[provider.provider_id] = provider
        return {"success": True, "provider": provider.provider_id}
    
    def get_login_url(self, provider_id: str, state: str = None) -> Dict:
        """
        Generate OAuth2 login URL for a provider.
        
        Returns:
            {"url": "...", "state": "...", "session_id": "..."}
        """
        if provider_id not in self.providers:
            return {"success": False, "error": f"Provider {provider_id} not configured"}
        
        provider = self.providers[provider_id]
        
        # Generate state for CSRF protection
        if not state:
            state = uuid.uuid4().hex
        
        # Store session info
        session_id = uuid.uuid4().hex
        self.sessions[state] = {
            "session_id": session_id,
            "provider_id": provider_id,
            "created_at": datetime.utcnow(),
            "redirect_uri": provider.redirect_uri
        }
        
        # Build authorization URL
        import urllib.parse
        
        params = {
            "client_id": provider.client_id,
            "redirect_uri": provider.redirect_uri,
            "response_type": "code",
            "scope": " ".join(provider.scopes),
            "state": state
        }
        
        # Provider-specific modifications
        url_template = provider.authorize_url
        
        if provider_id == "okta" and provider.domain:
            url_template = url_template.replace("{domain}", provider.domain)
        elif provider_id == "azure" and provider.tenant_id:
            url_template = url_template.replace("{tenant}", provider.tenant_id)
        
        auth_url = f"{url_template}?{urllib.parse.urlencode(params)}"
        
        return {
            "success": True,
            "url": auth_url,
            "state": state,
            "session_id": session_id
        }
    
    def handle_callback(self, code: str, state: str) -> Dict:
        """
        Handle OAuth2 callback and exchange code for tokens.
        
        Returns:
            {"success": bool, "user": {...}, "access_token": "..."}
        """
        if state not in self.sessions:
            return {"success": False, "error": "Invalid state parameter"}
        
        session = self.sessions[state]
        provider = self.providers[session["provider_id"]]
        
        # Exchange code for tokens
        import requests
        
        token_data = {
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": provider.redirect_uri
        }
        
        try:
            response = requests.post(
                provider.token_url,
                data=token_data,
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Token exchange failed: {response.status_code}"
                }
            
            tokens = response.json()
            access_token = tokens.get("access_token")
            id_token = tokens.get("id_token")
            
            # Get user info
            userinfo_response = requests.get(
                provider.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30
            )
            
            userinfo = userinfo_response.json() if userinfo_response.status_code == 200 else {}
            
            # Create or update user
            user = {
                "provider": provider.provider_id,
                "provider_id": userinfo.get("sub", userinfo.get("id")),
                "email": userinfo.get("email"),
                "name": userinfo.get("name", userinfo.get("displayName")),
                "picture": userinfo.get("picture", userinfo.get("avatar")),
                "access_token": access_token,
                "id_token": id_token,
                "refresh_token": tokens.get("refresh_token"),
                "expires_at": datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))
            }
            
            # Clean up session
            del self.sessions[state]
            
            return {
                "success": True,
                "user": user,
                "access_token": access_token
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def refresh_token(self, refresh_token: str, provider_id: str) -> Dict:
        """Refresh an OAuth token"""
        if provider_id not in self.providers:
            return {"success": False, "error": "Provider not found"}
        
        provider = self.providers[provider_id]
        
        try:
            response = requests.post(
                provider.token_url,
                data={
                    "client_id": provider.client_id,
                    "client_secret": provider.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                tokens = response.json()
                return {
                    "success": True,
                    "access_token": tokens.get("access_token"),
                    "expires_in": tokens.get("expires_in")
                }
            else:
                return {"success": False, "error": "Refresh failed"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_providers(self) -> List[Dict]:
        """List available OAuth providers"""
        return [
            {
                "id": p.provider_id,
                "name": p.name,
                "enabled": p.enabled,
                "scopes": p.scopes
            }
            for p in self.providers.values()
        ]
    
    def get_provider(self, provider_id: str) -> Optional[OAuthProvider]:
        """Get a specific provider"""
        return self.providers.get(provider_id)


# SSO Login Page Generator
def generate_login_page(oauth_providers: List[Dict]) -> str:
    """Generate HTML login page with SSO buttons"""
    
    buttons_html = ""
    for provider in oauth_providers:
        buttons_html += f'''
        <a href="/auth/oauth/login/{provider['id']}" 
           class="sso-button {provider['id']}">
            <span class="icon">{provider['name']}</span>
            Sign in with {provider['name']}
        </a>
        '''
    
    html = f'''
<!DOCTYPE html>
<html>
<head>
    <title>Sign In - NexusOS</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }}
        h1 {{ text-align: center; color: #333; }}
        .sso-buttons {{ display: flex; flex-direction: column; gap: 15px; }}
        .sso-button {{ 
            display: flex; align-items: center; justify-content: center; gap: 10px;
            padding: 15px 20px; border-radius: 8px; text-decoration: none; font-weight: 600;
            transition: transform 0.2s;
        }}
        .sso-button:hover {{ transform: scale(1.02); }}
        .sso-button.okta {{ background: #007dc1; color: white; }}
        .sso-button.azure {{ background: #0078d4; color: white; }}
        .sso-button.google {{ background: #4285f4; color: white; }}
        .divider {{ text-align: center; margin: 20px 0; color: #666; }}
        .email-login {{ display: block; text-align: center; color: #666; text-decoration: none; }}
    </style>
</head>
<body>
    <h1>Sign In to NexusOS</h1>
    <div class="sso-buttons">
        {buttons_html}
    </div>
    <div class="divider">or</div>
    <a href="/auth/login" class="email-login">Sign in with email</a>
</body>
</html>
    '''
    
    return html


# Singleton
_oauth_manager = None

def get_oauth_manager(base_url: str = None) -> OAuth2Manager:
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuth2Manager(base_url)
    return _oauth_manager
