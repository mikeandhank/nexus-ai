# API Authentication Guide

## Overview

NexusOS API uses **Bearer Token** authentication for all protected endpoints.

## Getting a Token

### 1. Register (First Time)

```bash
curl -X POST https://nexusos.cloud/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "your-password",
    "name": "Your Name"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 2. Login (Subsequent)

```bash
curl -X POST https://nexusos.cloud/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "your-password"
  }'
```

### 3. Refresh Token

```bash
curl -X POST https://nexusos.cloud/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
  }'
```

## Using the Token

Include the token in the `Authorization` header:

```bash
curl https://nexusos.cloud/api/agents \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

## Token Types

| Token | Lifetime | Use |
|-------|----------|-----|
| `access_token` | 1 hour | API requests |
| `refresh_token` | 7 days | Get new access token |

## Token Scopes

Access tokens include role-based permissions:

- **admin**: Full access
- **developer**: Agents, tools, read API
- **user**: Basic access
- **viewer**: Read-only

## Error Responses

| Code | Meaning | Solution |
|------|---------|----------|
| 401 | Invalid token | Re-login or refresh |
| 403 | Insufficient permissions | Check your role |
| 429 | Rate limited | Wait and retry |

## Example: Python

```python
import requests

# Login
resp = requests.post("https://nexusos.cloud/api/auth/login", json={
    "email": "you@example.com",
    "password": "your-password"
})
tokens = resp.json()

# Use token
headers = {"Authorization": f"Bearer {tokens['access_token']}"}
agents = requests.get("https://nexusos.cloud/api/agents", headers=headers).json()
```

## Example: JavaScript

```javascript
const login = async () => {
  const resp = await fetch('https://nexusos.cloud/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'you@example.com', password: 'your-password' })
  });
  const { access_token } = await resp.json();
  return access_token;
};

const token = await login();
const agents = await fetch('https://nexusos.cloud/api/agents', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

## Security Notes

- Tokens are JWTs - never share them
- Store securely (env vars, keychain)
- Use HTTPS only
- Refresh before expiry to avoid interruption
