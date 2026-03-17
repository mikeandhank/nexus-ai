# API Error Codes Reference

## HTTP Status Codes

| Code | Meaning | NexusOS Usage |
|------|---------|---------------|
| 200 | OK | Success |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid JWT |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource |
| 422 | Unprocessable | Validation failed |
| 429 | Too Many Requests | Rate limited |
| 500 | Internal Error | Server error |
| 503 | Service Unavailable | System overloaded |

## NexusOS Error Codes

### Authentication (AUTH_*)
| Code | Meaning | Resolution |
|------|---------|-------------|
| AUTH_INVALID_CREDENTIALS | Wrong email/password | Check credentials |
| AUTH_TOKEN_EXPIRED | JWT expired | Refresh token |
| AUTH_TOKEN_INVALID | Malformed JWT | Re-authenticate |
| AUTH_REGISTRATION_DISABLED | Registration closed | Contact admin |
| AUTH_USER_EXISTS | Email already registered | Use different email |

### Authorization (AUTHZ_*)
| Code | Meaning | Resolution |
|------|---------|-------------|
| AUTHZ_INSUFFICIENT_PERMS | Role too low | Request elevated role |
| AUTHZ_RESOURCE_FORBIDDEN | Don't own resource | Check ownership |

### Resource (RES_*)
| Code | Meaning | Resolution |
|------|---------|-------------|
| RES_NOT_FOUND | Item doesn't exist | Check ID |
| RES_ALREADY_EXISTS | Duplicate creation | Use different ID |
| RES_DELETED | Item was deleted | Restore or create new |

### Agent (AGENT_*)
| Code | Meaning | Resolution |
|------|---------|-------------|
| AGENT_NOT_FOUND | Agent ID invalid | Check agent_id |
| AGENT_RUNNING | Can't modify while running | Stop first |
| AGENT_STOPPED | Can't use stopped agent | Start first |
| AGENT_TIMEOUT | Execution took too long | Increase timeout |

### LLM (LLM_*)
| Code | Meaning | Resolution |
|------|---------|-------------|
| LLM_NOT_AVAILABLE | Model offline | Try different model |
| LLM_RESPONSE_EMPTY | Model returned nothing | Retry request |
| LLM_RATE_LIMITED | Model API limit hit | Wait and retry |
| LLM_CONTEXT_OVERFLOW | Prompt too long | Reduce context |

### Rate Limiting (RATE_*)
| Code | Meaning | Resolution |
|------|---------|-------------|
| RATE_LIMIT_EXCEEDED | Too many requests | Wait and retry |
| RATE_QUOTA_EXCEEDED | Monthly limit hit | Add balance |

### Database (DB_*)
| Code | Meaning | Resolution |
|------|---------|-------------|
| DB_CONNECTION_FAILED | Can't connect to DB | Check DB status |
| DB_QUERY_FAILED | SQL error | Check query syntax |
| DB_CONSTRAINT_VIOLATION | Data integrity | Check unique constraints |

---

## Example Error Responses

### 401 Unauthorized
```json
{
  "error": "AUTH_TOKEN_EXPIRED",
  "message": "Access token has expired. Please refresh.",
  "code": 401
}
```

### 403 Forbidden
```json
{
  "error": "AUTHZ_INSUFFICIENT_PERMS",
  "message": "Admin role required for this action",
  "code": 403
}
```

### 429 Too Many Requests
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit: 100 requests per minute",
  "retry_after": 30,
  "code": 429
}
```

### 500 Internal Error
```json
{
  "error": "INTERNAL_ERROR",
  "message": "An unexpected error occurred",
  "request_id": "req_abc123",
  "code": 500
}
```
