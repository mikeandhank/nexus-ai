"""
SSO Configuration Template
==========================
Copy this to sso_config.py and fill in your values.

Environment Variables (alternative):
- NEXUSOS_SSO_GOOGLE_CLIENT_ID
- NEXUSOS_SSO_GOOGLE_CLIENT_SECRET
- NEXUSOS_SSO_OKTA_DOMAIN
- NEXUSOS_SSO_OKTA_CLIENT_ID
- NEXUSOS_SSO_OKTA_CLIENT_SECRET
- NEXUSOS_SSO_AZURE_TENANT
- NEXUSOS_SSO_AZURE_CLIENT_ID
- NEXUSOS_SSO_AZURE_CLIENT_SECRET
"""

import os

# Google OAuth2
SSO_GOOGLE = {
    "enabled": os.environ.get("NEXUSOS_SSO_GOOGLE_ENABLED", "false").lower() == "true",
    "client_id": os.environ.get("NEXUSOS_SSO_GOOGLE_CLIENT_ID", ""),
    "client_secret": os.environ.get("NEXUSOS_SSO_GOOGLE_CLIENT_SECRET", ""),
    "redirect_uri": "https://nexusos.cloud/api/auth/sso/google/callback",
}

# Okta
SSO_OKTA = {
    "enabled": os.environ.get("NEXUSOS_SSO_OKTA_ENABLED", "false").lower() == "true",
    "domain": os.environ.get("NEXUSOS_SSO_OKTA_DOMAIN", ""),
    "client_id": os.environ.get("NEXUSOS_SSO_OKTA_CLIENT_ID", ""),
    "client_secret": os.environ.get("NEXUSOS_SSO_OKTA_CLIENT_SECRET", ""),
    "redirect_uri": "https://nexusos.cloud/api/auth/sso/okta/callback",
}

# Azure AD
SSO_AZURE = {
    "enabled": os.environ.get("NEXUSOS_SSO_AZURE_ENABLED", "false").lower() == "true",
    "tenant_id": os.environ.get("NEXUSOS_SSO_AZURE_TENANT", ""),
    "client_id": os.environ.get("NEXUSOS_SSO_AZURE_CLIENT_ID", ""),
    "client_secret": os.environ.get("NEXUSOS_SSO_AZURE_CLIENT_SECRET", ""),
    "redirect_uri": "https://nexusos.cloud/api/auth/sso/azure/callback",
}


def get_provider(provider: str):
    """Get provider config by name."""
    providers = {
        "google": SSO_GOOGLE,
        "okta": SSO_OKTA,
        "azure": SSO_AZURE,
    }
    return providers.get(provider.lower(), None)