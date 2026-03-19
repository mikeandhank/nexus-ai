# Lipaira API Documentation

**Base URL:** `https://lipaira.cloud/api/v1`

## Authentication

All API requests require an API key in the header:
```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### Agents

#### Create Agent
```
POST /agents
{
  "name": "My Agent",
  "system_prompt": "You are a helpful assistant...",
  "model": "openai/gpt-4"
}
```

#### List Agents
```
GET /agents
```

#### Get Agent
```
GET /agents/{agent_id}
```

#### Execute Agent
```
POST /agents/{agent_id}/execute
{
  "message": "Hello, help me with...",
  "stream": true
}
```

#### Delete Agent
```
DELETE /agents/{agent_id}
```

---

### Credits / Payments

#### Get Credit Balance
```
GET /credits
```

#### Purchase Credits
```
POST /credits/purchase
{
  "amount_dollars": 100,
  "stripe_payment_method_id": "pm_xxx"
}
```

#### Get Transaction History
```
GET /credits/transactions
```

---

### Webhooks

#### Register Webhook
```
POST /webhooks
{
  "url": "https://your-app.com/webhook",
  "events": ["agent.executed", "credit.low"]
}
```

#### List Webhooks
```
GET /webhooks
```

#### Delete Webhook
```
DELETE /webhooks/{webhook_id}
```

---

### Admin

#### Get Usage Analytics
```
GET /admin/analytics
```

#### Get All Users
```
GET /admin/users
```

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 429 | Rate Limited |
| 500 | Server Error |

## Rate Limits

- **API:** 100 requests/minute
- **Streaming:** 10 concurrent connections

## SDK

### Python
```python
from lipaira import Client

client = Client(api_key="your_key")
agent = client.agents.create(name="Assistant", system_prompt="...")
response = agent.execute("Hello!")
```
