# Lipaira Security Requirements
# Based on OpenClaw vulnerability analysis (CVE-2026-25253, March 2026)

## 1. Network Security

### Binding Configuration
- **DEFAULT:** Bind to `127.0.0.1` (localhost) only
- **PUBLIC:** Explicit opt-in required, never `0.0.0.0`
- Document in deployment guides

### TLS/SSL
- All connections over HTTPS/WSS (TLS 1.3 minimum)
- HTTP redirect to HTTPS (already done)
- Certificate auto-renewal via Let's Encrypt

## 2. Authentication

### Token Security
- JWT RS256 (asymmetric) - DONE
- Token rotation every 24 hours
- Short expiration (15 min access, 7 day refresh)
- Per-session tokens, no shared tokens

### WebSocket Security
- Auth required for all WS connections
- Token validation on every connection
- No token in URL (prevent leakage)

## 3. Input Handling

### Sanitization (ALREADY BUILT)
- SQL injection prevention
- XSS prevention  
- Path traversal protection
- Command injection prevention
- Use parameterized queries

## 4. Plugin/Skill System

### Integrity Verification
- Hash verification before loading any skill
- Signed skills with public key validation
- Reject unsigned/unverified skills

### Sandboxed Execution
- Skills run with minimal permissions
- No direct file system access
- No shell command execution
- Resource limits (memory, CPU, time)

### Review Process
- Code review required for published skills
- Automated vulnerability scanning
- Malicious skill detection

## 5. Memory System

### Sanitization
- Sanitize prompts before persistence
- Strip potential prompt injection payloads
- Reset on suspicious content

### Isolation
- Per-customer memory isolation
- No cross-session contamination
- Encrypted at rest

## 6. Credential Management

### Encryption (ALREADY BUILT)
- KMS encryption for all credentials
- No plaintext secrets
- AWS Secrets Manager integration

### Rotation
- Auto-rotate every 90 days
- Audit secret access

## 7. Audit & Logging

### Structured Logging (ALREADY BUILT)
- Immutable logs (S3 Object Lock)
- Hash verification for log integrity
- All events logged: auth, API, admin actions

### Retention
- 7 years for financial logs (IRS)
- 1 year for access logs
- Encrypted archival

## 8. Default Configuration

### Secure by Default
- Authentication ON by default
- Rate limiting ON by default
- CAPTCHA ON by default
- No open registration

### Production Hardening
- Firewall rules
- Fail2ban for SSH
- No root login
- IP allowlist option

## 9. Monitoring

### Real-time Alerts (ALREADY BUILT)
- Failed auth attempts
- Admin actions
- Config changes
- Unusual traffic patterns

### Incident Response
- Kill switch for API keys
- Webhook revocation procedure
- Customer notification pipeline

---

## Implementation Status

| Requirement | Status | Notes |
|-------------|--------|-------|
| Localhost binding | ⏳ | Need to change default |
| WS auth | ⏳ | Implement per-connection |
| Plugin signing | ⏳ | Design + implement |
| Skill sandbox | ⏳ | Build isolation layer |
| Memory sanitization | ⏳ | Add prompt scrubbing |
| Secret rotation | ⏳ | Add automation |

---

**Context:** OpenClaw had 135,000+ exposed instances, 50,000+ vulnerable to RCE. We must avoid these mistakes.
