"""
Encryption utilities using pgcrypto for data-at-rest encryption.
Sensitive columns are encrypted using AES-256-CBC.
"""
import os
import json
import hashlib
from typing import Optional, Any

# Get encryption key from environment (should be set in production)
def get_encryption_key() -> str:
    """Get or generate encryption key."""
    key = os.environ.get('NEXUSOS_ENCRYPTION_KEY')
    if not key:
        # For development - generate a stable key based on machine ID
        key = os.environ.get('NEXUSOS_SECRET_KEY', 'dev-key-change-in-production')
    return key[:32].ljust(32, '0')  # Pad to 32 bytes for AES-256

def hash_key_for_storage(key: str) -> str:
    """Hash key for storage (used when storing the key hash)."""
    return hashlib.sha256(key.encode()).hexdigest()

# Column-level encryption helpers
# These work with PostgreSQL pgcrypto functions via SQL

ENCRYPTED_COLUMNS = {
    'users': ['api_keys', 'password_hash'],
    'webhooks': ['secret'],
    'agents': ['system_prompt', 'tools']
}

def should_encrypt(table: str, column: str) -> bool:
    """Check if a column should be encrypted."""
    return column in ENCRYPTED_COLUMNS.get(table, [])

# Note: Actual encryption happens at DB level via pgcrypto
# This module provides utility functions for key management
