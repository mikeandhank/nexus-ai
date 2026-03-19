"""
C-01: Data Inventory Map
Machine-readable GDPR Article 30 compliance
"""

from typing import List, Optional
from enum import Enum


class LegalBasis(str, Enum):
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGITIMATE_INTEREST = "legitimate_interest"
    LEGAL_OBLIGATION = "legal_obligation"


class DataCategory(str, Enum):
    PERSONAL_IDENTIFIABLE = "personal_identifiable"
    FINANCIAL = "financial"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SENSITIVE = "sensitive"


class RetentionPeriod(str, Enum):
    UNTIL_DELETION = "until_deletion"
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    YEARS_1 = "1_year"
    YEARS_2 = "2_years"
    YEARS_7 = "7_years"
    INDEFINITE = "indefinite"


# C-01: Data Inventory - Update this as schema changes
DATA_INVENTORY = {
    "version": "1.0",
    "last_updated": "2026-03-19",
    "entities": [
        {
            "name": "customer",
            "description": "End user accounts",
            "legal_basis": LegalBasis.CONTRACT.value,
            "fields": [
                {"name": "id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "email", "type": "email", "pii": True, "retention": RetentionPeriod.YEARS_7},
                {"name": "name", "type": "string", "pii": True, "retention": RetentionPeriod.YEARS_7},
                {"name": "password_hash", "type": "hash", "pii": False, "retention": RetentionPeriod.UNTIL_DELETION},
                {"name": "created_at", "type": "timestamp", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "updated_at", "type": "timestamp", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "deleted_at", "type": "timestamp", "pii": False, "retention": RetentionPeriod.YEARS_7},
            ],
            "third_parties": ["AWS (hosting)", "PostgreSQL (database)"],
            "storage_location": "AWS us-east-1"
        },
        {
            "name": "transaction",
            "description": "Financial transactions",
            "legal_basis": LegalBasis.LEGAL_OBLIGATION.value,
            "fields": [
                {"name": "id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "customer_id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "event_type", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "amount_cents", "type": "integer", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "currency", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "stripe_payment_intent_id", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "created_at", "type": "timestamp", "pii": False, "retention": RetentionPeriod.YEARS_7},
            ],
            "third_parties": ["Stripe (payments)", "AWS (hosting)"],
            "storage_location": "AWS us-east-1",
            "retention_note": "IRS requirement: 7 years for financial records"
        },
        {
            "name": "credit_ledger",
            "description": "Token credit event ledger",
            "legal_basis": LegalBasis.CONTRACT.value,
            "fields": [
                {"name": "event_id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "customer_id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "event_type", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "credits_delta", "type": "integer", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "stripe_payment_id", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "event_timestamp", "type": "timestamp", "pii": False, "retention": RetentionPeriod.YEARS_7},
            ],
            "third_parties": ["Stripe (payments)"],
            "storage_location": "AWS us-east-1"
        },
        {
            "name": "api_key",
            "description": "Customer API keys",
            "legal_basis": LegalBasis.CONTRACT.value,
            "fields": [
                {"name": "id", "type": "uuid", "pii": False, "retention": RetentionPeriod.UNTIL_DELETION},
                {"name": "customer_id", "type": "uuid", "pii": False, "retention": RetentionPeriod.UNTIL_DELETION},
                {"name": "key_hash", "type": "hash", "pii": False, "retention": RetentionPeriod.UNTIL_DELETION},
                {"name": "name", "type": "string", "pii": False, "retention": RetentionPeriod.UNTIL_DELETION},
                {"name": "last_used_at", "type": "timestamp", "pii": False, "retention": RetentionPeriod.DAYS_90},
                {"name": "created_at", "type": "timestamp", "pii": False, "retention": RetentionPeriod.UNTIL_DELETION},
            ],
            "third_parties": [],
            "storage_location": "AWS us-east-1"
        },
        {
            "name": "agent",
            "description": "AI agent configurations",
            "legal_basis": LegalBasis.CONTRACT.value,
            "fields": [
                {"name": "id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "customer_id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "name", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "system_prompt", "type": "text", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "memory", "type": "json", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "created_at", "type": "timestamp", "pii": False, "retention": RetentionPeriod.YEARS_7},
            ],
            "third_parties": [],
            "storage_location": "AWS us-east-1"
        },
        {
            "name": "openrouter_request",
            "description": "LLM API call logs (COGS)",
            "legal_basis": LegalBasis.LEGITIMATE_INTEREST.value,
            "fields": [
                {"name": "id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "customer_id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "api_key_id", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "model", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "total_tokens", "type": "integer", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "cost_usd", "type": "decimal", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "timestamp", "type": "timestamp", "pii": False, "retention": RetentionPeriod.YEARS_7},
            ],
            "third_parties": ["OpenRouter (LLM routing)"],
            "storage_location": "AWS us-east-1"
        },
        {
            "name": "access_log",
            "description": "Authentication and access events",
            "legal_basis": LegalBasis.LEGITIMATE_INTEREST.value,
            "fields": [
                {"name": "event_id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "customer_id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "event_type", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "ip_address", "type": "ip", "pii": True, "retention": RetentionPeriod.YEARS_1},
                {"name": "user_agent", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_1},
                {"name": "timestamp", "type": "timestamp", "pii": False, "retention": RetentionPeriod.YEARS_7},
            ],
            "third_parties": ["AWS (CloudWatch)"],
            "storage_location": "AWS us-east-1",
            "retention_note": "Reduced retention for IP address (PII)"
        },
        {
            "name": "tos_acceptance",
            "description": "Terms of Service acceptance records",
            "legal_basis": LegalBasis.LEGAL_OBLIGATION.value,
            "fields": [
                {"name": "id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "customer_id", "type": "uuid", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "tos_version", "type": "string", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "accepted_at", "type": "timestamp", "pii": False, "retention": RetentionPeriod.YEARS_7},
                {"name": "ip_address", "type": "ip", "pii": True, "retention": RetentionPeriod.YEARS_7},
            ],
            "third_parties": [],
            "storage_location": "AWS us-east-1"
        }
    ]
}


# C-02: PII Field Tagging - CI Check
PII_TAGGING_CHECK = '''#!/bin/bash
# C-02: CI check for new PII fields
# Block any migration that adds PII without documentation

set -e

echo "Checking for new PII fields in migration..."

# Fields that indicate PII
PII_PATTERNS="email|name|phone|address|ip_address|payment|credit_card|ssn"

# Check migration files
for file in migrations/*.sql; do
    if grep -iE "$PII_PATTERNS" "$file" > /dev/null; then
        echo "WARNING: Potential PII field found in $file"
        echo "Please ensure the field is documented in DATA_INVENTORY with:"
        echo "  - pii: true"
        echo "  - retention period"
        echo "  - legal basis"
        
        # Check if documented
        if ! grep -q "pii.*true" "$file"; then
            echo "ERROR: PII field must be tagged in data inventory"
            exit 1
        fi
    fi
done

echo "PII check passed"
'''


def get_pii_fields() -> List[dict]:
    """Get all PII-tagged fields from inventory"""
    pii_fields = []
    for entity in DATA_INVENTORY["entities"]:
        for field in entity["fields"]:
            if field.get("pii"):
                pii_fields.append({
                    "entity": entity["name"],
                    "field": field["name"],
                    "type": field["type"],
                    "retention": field["retention"]
                })
    return pii_fields


def get_entity_retention(entity_name: str) -> Optional[str]:
    """Get retention period for an entity"""
    for entity in DATA_INVENTORY["entities"]:
        if entity["name"] == entity_name:
            return entity.get("retention_note", "See individual fields")
    return None
