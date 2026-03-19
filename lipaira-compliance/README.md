# Lipaira Compliance & Accounting Infrastructure

**Status:** Phase 1 implementation ready (requires AWS deployment)
**Created:** 2026-03-19
**AWS Server:** 3.16.216.39 (not yet accessible)

---

## Deployed Components Checklist

### Phase 1 - Pre-Launch (Before First Revenue)

| Task | Code Ready | AWS Required | Status |
|------|-----------|--------------|--------|
| A-01 Structured Log Schema | ✅ | ❌ | Ready |
| A-02 Centralized Log Aggregation | ⚠️ | ✅ | Config ready, needs deployment |
| A-03 S3 Object Lock | ⚠️ | ✅ | Config ready, needs deployment |
| A-04 Tamper-Evidence Hashing | ⚠️ | ✅ | Lambda code ready |
| A-05 CloudTrail | ⚠️ | ✅ | Config ready |
| A-07 Transaction Ledger Table | ✅ | ⚠️ | SQL ready, needs DB |
| A-08 Stripe Webhook Audit | ✅ | ❌ | Code ready |
| A-09 Credit Ledger (Event Sourcing) | ✅ | ⚠️ | SQL ready, needs DB |
| A-10 OpenRouter Consumption Logging | ✅ | ❌ | Code ready |
| B-01 Revenue Event Stream | ✅ | ❌ | Code ready |
| B-02 COGS Event Stream | ✅ | ❌ | Code ready |
| B-04 Sales Tax Collection | ✅ | ❌ | Code ready |
| C-01 Data Inventory Map | ✅ | ❌ | Template ready |
| C-02 PII Field Tagging | ✅ | ❌ | Config ready |
| C-07 ToS Version Control | ✅ | ❌ | Code ready |
| C-08 ToS Acceptance Logging | ✅ | ❌ | Code ready |
| C-11 Encryption at Rest | ⚠️ | ✅ | KMS config ready |
| C-12 Encryption in Transit | ⚠️ | ✅ | ALB config ready |
| C-13 Least Privilege IAM | ⚠️ | ✅ | Policy docs ready |

---

## Pending Founder Decisions (★)

- [ ] Credit expiry policy
- [ ] Refund policy (full vs partial)
- [ ] AUP content categories
- [ ] Data retention exceptions
- [ ] GDPR supervisory authority

---

## Rollout Instructions

When AWS server is accessible:
1. Create S3 buckets with Object Lock (COMPLIANCE mode)
2. Deploy CloudTrail configuration
3. Run database migrations
4. Configure KMS keys
5. Set up IAM roles
6. Deploy Lambda functions

