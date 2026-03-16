# API Authentication Flow

## Overview

NexusOS uses a token-based auth system with two tokens for maximum security and flexibility.

## Authentication Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  /login     │────▶│   Issue     │
│             │     │             │     │  Tokens     │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  /refresh   │◀────│   Access    │
                    │             │     │   Expired   │
                    └─────────────┘     └─────────────┘
```

## Step-by-Step Flow

### 1. Registration (One-time)

```bash
POST /api/auth/register
{
  "email": "you@example.com",
  "password": "secure-password",
  "name": "Your Name"
}
```

Creates user and returns tokens.

### 2. Login

```bash
POST /api/auth/login
{
  "email": "you@example.com", 
  "password": "secure-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 3. API Calls

Use `access_token` in header:
```bash
GET /api/agents
Authorization: Bearer eyJhbGci...
```

### 4. Token Refresh (before expiry)

```bash
POST /api/auth/refresh
{
  "refresh_token": "eyJ9..."
}
```

Returns new access + refresh tokens.

### 5. Logout

```bash
POST /api/auth/logout
Authorization: Bearer eyJhbGci...
```

Invalidates refresh token.

## Token Details

### Access Token
- **Lifetime:** 1 hour (3600 seconds)
- **Purpose:** Authorize API requests
- **Validation:** JWT signature + expiration check

### Refresh Token
- **Lifetime:** 7 days
- **Purpose:** Get new access tokens without re-login
- **Storage:** HttpOnly cookie or secure storage

## Security Implementation

### Password Hashing
- Uses **bcrypt** with cost factor 12
- Never stores plain text passwords

### Token Generation
- JWT with **HS256** algorithm
- Contains: `user_id`, `email`, `role`, `exp`, `iat`

### Token Storage
- Access: Client memory (short-lived)
- Refresh: HttpOnly cookie or encrypted storage

## Best Practices

1. **Store refresh token securely** - Use encrypted storage
2. **Refresh proactively** - Refresh at 50% lifetime
3. **Handle 401 gracefully** - Auto-refresh on auth failure
4. **Use HTTPS** - Always, never HTTP
5. **Implement token rotation** - Get new refresh token each time

## Error Handling

```python
import requests
from requests.auth import HTTPBasicAuth

def api_request(method, url, access_token, refresh_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.request(method, url, headers=headers)
    
    if resp.status_code == 401:
        # Token expired, refresh
        new_tokens = refresh(refresh_token)
        headers["Authorization"] = f"Bearer {new_tokens['access_token']}"
        resp = requests.request(method, url, headers=headers)
    
    return resp.json()

def refresh(refresh_token):
    resp = requests.post(API_URL + "/auth/refresh", json={
        "refresh_token": refresh_token
    })
    return resp.json()
```

## SSO Integration

For enterprise users, SSO bypasses password auth:

```
User → SSO Login → SAML/OAuth → Callback → Issue Tokens
```

See [SSO Configuration Guide](./sso-configuration.md).
