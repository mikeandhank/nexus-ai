"""
End-to-End Encryption Module
Provides encryption for sensitive data at rest
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import os
import hashlib


class E2EEncryptor:
    """
    End-to-end encryption for sensitive data
    Uses AES-256 with PBKDF2 key derivation
    """
    
    def __init__(self, master_key: str = None):
        """
        Initialize with master key
        """
        if master_key:
            self.key = self._derive_key(master_key)
        else:
            # Generate new key for new installations
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password: str, salt: bytes = None) -> bytes:
        """Derive encryption key from password"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Returns: base64 encoded ciphertext
        """
        if not plaintext:
            return ""
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext
        
        Returns: plaintext string
        """
        if not ciphertext:
            return ""
        
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def encrypt_dict(self, data: dict, fields: list = None) -> dict:
        """
        Encrypt specific fields in a dictionary
        
        Args:
            data: Dictionary to encrypt
            fields: List of field names to encrypt (encrypts all if None)
        """
        result = data.copy()
        
        if fields is None:
            # Encrypt all string values
            for key, value in result.items():
                if isinstance(value, str) and value:
                    result[key] = self.encrypt(value)
        else:
            for field in fields:
                if field in result and isinstance(result[field], str):
                    result[field] = self.encrypt(result[field])
        
        return result
    
    def decrypt_dict(self, data: dict, fields: list = None) -> dict:
        """Decrypt specific fields in a dictionary"""
        result = data.copy()
        
        if fields is None:
            for key, value in result.items():
                if isinstance(value, str) and value:
                    try:
                        result[key] = self.decrypt(value)
                    except:
                        pass  # Not encrypted, leave as-is
        else:
            for field in fields:
                if field in result and isinstance(result[field], str):
                    try:
                        result[field] = self.decrypt(result[field])
                    except:
                        pass
        
        return result
    
    def hash_for_storage(self, data: str) -> str:
        """
        Create a one-way hash for storage (not reversible)
        Use for comparing without exposing
        """
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key"""
        return Fernet.generate_key().decode()
    
    @staticmethod
    def generate_salt() -> str:
        """Generate a random salt"""
        return base64.urlsafe_b64encode(os.urandom(16)).decode()


# Convenience functions
_default_encryptor = None

def get_encryptor(master_key: str = None) -> E2EEncryptor:
    """Get global encryptor instance"""
    global _default_encryptor
    if _default_encryptor is None:
        _default_encryptor = E2EEncryptor(master_key)
    return _default_encryptor


def encrypt(data: str) -> str:
    """Quick encrypt function"""
    return get_encryptor().encrypt(data)


def decrypt(data: str) -> str:
    """Quick decrypt function"""
    return get_encryptor().decrypt(data)


# Example usage for API keys
def encrypt_api_key(provider: str, api_key: str) -> dict:
    """
    Encrypt and store an API key
    
    Returns: {
        "provider": "openai",
        "key_hash": "...",
        "encrypted_key": "..."
    }
    """
    encryptor = get_encryptor()
    
    return {
        "provider": provider,
        "key_hash": encryptor.hash_for_storage(api_key),
        "encrypted_key": encryptor.encrypt(api_key)
    }


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key"""
    return get_encryptor().decrypt(encrypted_key)
