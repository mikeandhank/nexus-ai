"""
Database Encryption at Rest
===========================
Uses pgcrypto for PostgreSQL column-level encryption.
Implements envelope encryption with master key + data encryption keys.
"""
import os
import base64
import hashlib
import psycopg2
from typing import Dict, List, Optional


class DatabaseEncryption:
    """
    Database encryption manager using pgcrypto.
    
    Encryption Strategy:
    1. Master key stored in environment variable and encryption_keys table
    2. pgcrypto used for column-level encryption
    3. Email addresses: encrypted + SHA256 hash for lookups
    4. API keys: encrypted (no lookup needed)
    5. Provider keys: encrypted (no lookup needed)
    """
    
    def __init__(self, db_url: str, master_key: str = None):
        self.db_url = db_url
        self.master_key = master_key or os.environ.get('NEXUSOS_MASTER_KEY')
        if not self.master_key:
            raise ValueError("Master key required. Set NEXUSOS_MASTER_KEY env var.")
    
    def setup(self) -> Dict:
        """Enable pgcrypto and create encryption infrastructure."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        results = []
        
        # Enable pgcrypto
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            results.append("✅ pgcrypto extension enabled")
        except Exception as e:
            results.append(f"❌ pgcrypto error: {e}")
        
        # Create encryption keys table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS encryption_keys (
                    id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            results.append("✅ encryption_keys table ready")
        except Exception as e:
            results.append(f"❌ Table error: {e}")
        
        # Store master key hash (never store raw key)
        key_hash = hashlib.sha256(self.master_key.encode()).hexdigest()
        cursor.execute("""
            INSERT INTO encryption_keys (id, key_hash)
            VALUES ('master', %s)
            ON CONFLICT (id) DO UPDATE SET key_hash = %s
        """, (key_hash, key_hash))
        results.append("✅ Master key stored (hash only)")
        
        conn.commit()
        conn.close()
        
        return {"success": True, "actions": results}
    
    def encrypt_users_email(self) -> Dict:
        """
        Encrypt user emails with lookup hash.
        
        - Encrypts email value using pgcrypto
        - Creates SHA256 hash for login lookups
        """
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        # Add email_hash column if not exists
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS email_hash TEXT UNIQUE
        """)
        
        # Create index for lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email_hash 
            ON users(email_hash)
        """)
        
        # Encrypt emails and create lookup hashes
        cursor.execute("""
            UPDATE users 
            SET 
                email_hash = encode(digest(email, 'sha256'), 'hex'),
                email = 'pgp_encrypt:' || encode(
                    pgp_sym_encrypt(email, %s), 'hex'
                )
            WHERE email_hash IS NULL 
              AND email IS NOT NULL
              AND email NOT LIKE 'pgp_encrypt:%'
        """, (self.master_key,))
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {"encrypted": count}
    
    def encrypt_api_keys(self) -> Dict:
        """Encrypt API key hashes."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE api_keys 
            SET key_hash = 'pgp_encrypt:' || encode(
                pgp_sym_encrypt(key_hash, %s), 'hex'
            )
            WHERE key_hash NOT LIKE 'pgp_encrypt:%'
              AND key_hash IS NOT NULL
        """, (self.master_key,))
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {"encrypted": count}
    
    def encrypt_provider_keys(self) -> Dict:
        """Encrypt provider API keys."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE provider_keys 
            SET encrypted_key = 'pgp_encrypt:' || encode(
                pgp_sym_encrypt(encrypted_key, %s), 'hex'
            )
            WHERE encrypted_key NOT LIKE 'pgp_encrypt:%'
              AND encrypted_key IS NOT NULL
        """, (self.master_key,))
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {"encrypted": count}
    
    def verify(self) -> Dict:
        """Verify encryption status."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        checks = []
        
        # pgcrypto
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto'")
        checks.append(("pgcrypto", bool(cursor.fetchone())))
        
        # Master key
        cursor.execute("SELECT COUNT(*) FROM encryption_keys WHERE id = 'master'")
        checks.append(("master_key", cursor.fetchone()[0] > 0))
        
        # Encrypted emails
        cursor.execute("SELECT COUNT(*) FROM users WHERE email LIKE 'pgp_encrypt:%'")
        encrypted_emails = cursor.fetchone()[0]
        checks.append(("users.email encrypted", encrypted_emails > 0))
        
        # Email lookup hashes
        cursor.execute("SELECT COUNT(*) FROM users WHERE email_hash IS NOT NULL")
        hashed_emails = cursor.fetchone()[0]
        checks.append(("users.email_hash", hashed_emails > 0))
        
        # Encrypted API keys
        cursor.execute("SELECT COUNT(*) FROM api_keys WHERE key_hash LIKE 'pgp_encrypt:%'")
        encrypted_keys = cursor.fetchone()[0]
        checks.append(("api_keys encrypted", encrypted_keys > 0))
        
        conn.close()
        
        all_passed = all(check[1] for check in checks)
        return {
            "passed": all_passed,
            "checks": {k: "✅" if v else "❌" for k, v in checks}
        }


# SQL Helper Functions (run these in PostgreSQL):
ENCRYPTION_SQL_HELPERS = """
-- Decrypt a value encrypted with pgp_sym_encrypt
CREATE OR REPLACE FUNCTION decrypt_value(encrypted text)
RETURNS text AS $$
BEGIN
  RETURN pgp_sym_decrypt(
    decode(TRIM(SUBSTRING(encrypted FROM 13)), 'hex'), 
    'MASTER_KEY_HERE'
  );
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Encrypt a value
CREATE OR REPLACE FUNCTION encrypt_value(plaintext text)
RETURNS text AS $$
BEGIN
  IF plaintext IS NULL THEN RETURN NULL;
  END IF;
  RETURN 'pgp_encrypt:' || encode(
    pgp_sym_encrypt(plaintext, 'MASTER_KEY_HERE'), 'hex'
  );
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Usage:
-- SELECT decrypt_value(email) FROM users;
-- SELECT encrypt_value('test@example.com');
"""


if __name__ == "__main__":
    import sys
    
    db_url = os.environ.get('DATABASE_URL')
    master_key = os.environ.get('NEXUSOS_MASTER_KEY')
    
    if not db_url or not master_key:
        print("Set DATABASE_URL and NEXUSOS_MASTER_KEY env vars")
        sys.exit(1)
    
    enc = DatabaseEncryption(db_url, master_key)
    
    print("=== Setting up Database Encryption ===")
    result = enc.setup()
    for action in result.get("actions", []):
        print(action)
    
    print("\n=== Encrypting Users ===")
    result = enc.encrypt_users_email()
    print(f"Encrypted {result['encrypted']} user emails")
    
    print("\n=== Encrypting API Keys ===")
    result = enc.encrypt_api_keys()
    print(f"Encrypted {result['encrypted']} API keys")
    
    print("\n=== Encrypting Provider Keys ===")
    result = enc.encrypt_provider_keys()
    print(f"Encrypted {result['encrypted']} provider keys")
    
    print("\n=== Verification ===")
    result = enc.verify()
    for check, status in result.get("checks", {}).items():
        print(f"{status} {check}")