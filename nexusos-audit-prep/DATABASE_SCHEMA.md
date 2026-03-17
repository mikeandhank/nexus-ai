# Database Schema

## Core Tables

### users
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    tier TEXT DEFAULT 'free',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### conversations
```sql
CREATE TABLE conversations (
    conversation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    agent_id TEXT,
    title TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### messages
```sql
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tokens_used INTEGER,
    model TEXT,
    cost_usd DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);
```

### agents
```sql
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    model TEXT DEFAULT 'phi3',
    system_prompt TEXT,
    tools JSONB DEFAULT '[]',
    status TEXT DEFAULT 'stopped',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### api_usage
```sql
CREATE TABLE api_usage (
    usage_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    agent_id TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10,6),
    endpoint TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### api_keys
```sql
CREATE TABLE api_keys (
    key_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    name TEXT,
    rate_limit INTEGER DEFAULT 100,
    monthly_limit INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### audit_log
```sql
CREATE TABLE audit_log (
    log_id TEXT PRIMARY KEY,
    user_id TEXT,
    event_type TEXT NOT NULL,
    resource TEXT,
    action TEXT,
    ip_address TEXT,
    user_agent TEXT,
    status TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### kernel_agents
```sql
CREATE TABLE kernel_agents (
    agent_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    state TEXT DEFAULT 'created',
    pid INTEGER,
    memory_usage BIGINT,
    cpu_percent DECIMAL(5,2),
    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### kernel_events
```sql
CREATE TABLE kernel_events (
    event_id TEXT PRIMARY KEY,
    agent_id TEXT,
    event_type TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### kernel_ipc
```sql
CREATE TABLE kernel_ipc (
    message_id TEXT PRIMARY KEY,
    msg_type TEXT NOT NULL,
    from_agent_id TEXT,
    to_agent_id TEXT,
    channel TEXT,
    payload JSONB,
    correlation_id TEXT,
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### user_balances
```sql
CREATE TABLE user_balances (
    user_id TEXT PRIMARY KEY,
    balance DECIMAL(10,2) DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0,
    total_reloaded DECIMAL(10,2) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### api_reloads
```sql
CREATE TABLE api_reloads (
    reload_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    fee DECIMAL(10,2) NOT NULL,
    total_charged DECIMAL(10,2) NOT NULL,
    payment_method TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### rbac_roles
```sql
CREATE TABLE rbac_roles (
    role_id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    parent_role_id TEXT,
    permissions JSONB DEFAULT '[]',
    is_system BOOLEAN DEFAULT FALSE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### rbac_assignments
```sql
CREATE TABLE rbac_assignments (
    assignment_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    resource_scope TEXT,
    granted_by TEXT,
    granted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);
```
