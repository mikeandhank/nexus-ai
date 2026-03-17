-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create encryption key table (stores master key hash)
CREATE TABLE IF NOT EXISTS encryption_keys (
    id TEXT PRIMARY KEY DEFAULT 'master',
    key_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Function to encrypt text using PGP symmetric encryption
CREATE OR REPLACE FUNCTION encrypt_column(text, text)
RETURNS text AS $$
BEGIN
    RETURN pgp_sym_encrypt($1, $2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to decrypt text  
CREATE OR REPLACE FUNCTION decrypt_column(text, text)
RETURNS text AS $$
BEGIN
    RETURN pgp_sym_decrypt($1::bytea, $2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;
