"""
JWT Key Rotation Module - UPDATED
Provides RS256 (asymmetric) JWT with key rotation
SECURITY: Now uses RS256 instead of HS256
"""
import time
import jwt
import redis
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import base64


class JWTManager:
    """
    Handles JWT with RS256 (asymmetric) for enterprise security
    
    Key improvements:
    - RS256 instead of HS256 (asymmetric = safer)
    - Private key signs, public key verifies
    - Key rotation support
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        self.key_prefix = "jwt:keys:"
        self.current_key_id = "jwt:current_key"
        self.rotation_interval = 86400 * 30  # 30 days
        
        # Load or generate keys
        self._ensure_keys()
    
    def _ensure_keys(self):
        """Ensure we have key pair"""
        # Check if we have existing keys
        key_id = self.redis.get(self.current_key_id)
        
        if not key_id:
            # Generate new key pair
            self._generate_keypair()
    
    def _generate_keypair(self):
        """Generate new RSA key pair"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Generate key ID
        key_id = f"key_{int(time.time())}"
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Get public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Store in Redis
        self.redis.set(
            f"{self.key_prefix}{key_id}:private",
            base64.b64encode(private_pem).decode(),
            ex=self.rotation_interval * 2
        )
        self.redis.set(
            f"{self.key_prefix}{key_id}:public",
            public_pem.decode(),
            ex=self.rotation_interval * 2
        )
        self.redis.set(self.current_key_id, key_id)
        
        # Store current key pair
        self._private_key = private_key
        self._public_key = public_key
        
        print(f"Generated new RSA key pair: {key_id}")
    
    def _load_current_keys(self):
        """Load current keys from Redis"""
        key_id = self.redis.get(self.current_key_id)
        
        if not key_id:
            self._generate_keypair()
            return
        
        private_pem_b64 = self.redis.get(f"{self.key_prefix}{key_id}:private")
        public_pem = self.redis.get(f"{self.key_prefix}{key_id}:public")
        
        if not private_pem_b64 or not public_pem:
            self._generate_keypair()
            return
        
        # Deserialize keys
        private_pem = base64.b64decode(private_pem_b64)
        self._private_key = serialization.load_pem_private_key(
            private_pem, password=None, backend=default_backend()
        )
        self._public_key = serialization.load_pem_public_key(
            public_pem.encode(), backend=default_backend()
        )
    
    def create_token(self, payload: dict, expires_in: int = 3600) -> str:
        """Create JWT token with RS256"""
        self._load_current_keys()
        
        now = int(time.time())
        payload.update({
            "iat": now,
            "exp": now + expires_in
        })
        
        token = jwt.encode(payload, self._private_key, algorithm="RS256")
        return token
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token with RS256"""
        self._load_current_keys()
        
        try:
            payload = jwt.decode(
                token, 
                self._public_key, 
                algorithms=["RS256"]
            )
            return {"valid": True, "payload": payload}
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": str(e)}
    
    def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token"""
        result = self.verify_token(refresh_token)
        
        if not result["valid"]:
            return result
        
        payload = result["payload"]
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            return {"valid": False, "error": "Not a refresh token"}
        
        # Create new access token
        new_access_token = self.create_token({
            "user_id": payload["user_id"],
            "email": payload["email"],
            "role": payload["role"],
            "type": "access"
        }, expires_in=3600)
        
        return {
            "valid": True,
            "access_token": new_access_token
        }
    
    def rotate_keys(self):
        """Rotate to a new key pair"""
        self._generate_keypair()


# Singleton
_jwt_manager = None

def get_jwt_manager() -> JWTManager:
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager
