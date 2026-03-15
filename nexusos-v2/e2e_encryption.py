"""
NexusOS E2E Encryption
Encrypt agent state at rest.
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import json

# Generate or load encryption key
ENCRYPTION_KEY_FILE = os.environ.get('NEXUSOS_KEY_FILE', '/opt/nexusos-data/.encryption_key')

def get_encryption_key():
    """Get or create encryption key"""
    if os.path.exists(ENCRYPTION_KEY_FILE):
        with open(ENCRYPTION_KEY_FILE, 'rb') as f:
            return f.read()
    
    # Generate new key
    key = Fernet.generate_key()
    os.makedirs(os.path.dirname(ENCRYPTION_KEY_FILE), exist_ok=True)
    with open(ENCRYPTION_KEY_FILE, 'wb') as f:
        f.write(key)
    os.chmod(ENCRYPTION_KEY_FILE, 0o600)
    return key


class E2EEncryption:
    """E2E encryption for agent state"""
    
    def __init__(self):
        self.key = get_encryption_key()
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data):
        """Encrypt data"""
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        elif isinstance(data, str):
            data = data.encode()
        
        encrypted = self.cipher.encrypt(data)
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data):
        """Decrypt data"""
        try:
            data = base64.b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(data)
            return decrypted.decode()
        except Exception as e:
            return None
    
    def encrypt_agent_state(self, agent_id, state):
        """Encrypt agent state"""
        data = {
            'agent_id': agent_id,
            'state': state,
            'timestamp': __import__('time').time()
        }
        return self.encrypt(data)
    
    def decrypt_agent_state(self, encrypted_state):
        """Decrypt agent state"""
        decrypted = self.decrypt(encrypted_state)
        if decrypted:
            try:
                return json.loads(decrypted)
            except:
                return None
        return None


# Global encryption instance
_encryption = None

def get_encryption():
    """Get E2E encryption instance"""
    global _encryption
    if _encryption is None:
        _encryption = E2EEncryption()
    return _encryption


def setup_encryption_routes(app):
    """Add encryption routes"""
    enc = get_encryption()
    
    @app.route('/api/encrypt', methods=['POST'])
    def encrypt_data():
        from flask import request, jsonify
        data = request.json.get('data')
        if not data:
            return jsonify({'error': 'data required'}), 400
        
        encrypted = enc.encrypt(data)
        return jsonify({'encrypted': encrypted})
    
    @app.route('/api/decrypt', methods=['POST'])
    def decrypt_data():
        from flask import request, jsonify
        data = request.json.get('encrypted')
        if not data:
            return jsonify({'error': 'encrypted required'}), 400
        
        decrypted = enc.decrypt(data)
        if decrypted is None:
            return jsonify({'error': 'decryption failed'}), 400
        
        return jsonify({'decrypted': decrypted})
    
    @app.route('/api/encryption/status', methods=['GET'])
    def encryption_status():
        from flask import jsonify
        return jsonify({
            'enabled': True,
            'key_file': ENCRYPTION_KEY_FILE,
            'algorithm': 'Fernet (AES-128)'
        })
    
    print("[NexusOS] E2E Encryption enabled")
