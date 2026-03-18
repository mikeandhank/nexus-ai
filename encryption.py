"""
Encryption utilities using pgcrypto for data-at-rest encryption.
Sensitive columns are encrypted using AES-256-CBC.
"""
import os
import json
import hashlib
import hmac
import base64
from typing import Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Get encryption key from environment - FAIL if not set in production
def get_encryption_key() -> str:
    """Get encryption key - fails if not set in production."""
    env = os.environ.get('NEXUSOS_ENV', 'development')
    
    key = os.environ.get('NEXUSOS_ENCRYPTION_KEY')
    
    if not key:
        if env == 'production':
            raise ValueError("NEXUSOS_ENCRYPTION_KEY must be set in production")
        # Development fallback - but warn
        import warnings
        warnings.warn("Using insecure dev key - set NEXUSOS_ENCRYPTION_KEY for production")
        key = os.environ.get('NEXUSOS_SECRET_KEY', 'dev-key-do-not-use-in-prod')
    
    # Use proper key derivation (PBKDF2)
    return derive_key(key)

def derive_key(password: str, salt: bytes = None) -> str:
    """Derive a proper encryption key using PBKDF2."""
    if salt is None:
        salt = b'nexusos-salt-v1'  # Fixed salt for deterministic derivation
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key.decode()

def hash_key_for_storage(key: str) -> str:
    """Hash key for storage with salt - use bcrypt in production."""
    import bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(key.encode(), salt)
    return hashed.decode()

def verify_key_hash(key: str, stored_hash: str) -> bool:
    """Verify key against stored hash using bcrypt."""
    import bcrypt
    try:
        return bcrypt.checkpw(key.encode(), stored_hash.encode())
    except Exception:
        return False

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
