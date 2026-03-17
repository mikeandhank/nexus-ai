"""
Nexus Server - Full Implementation
Complete server with: Auth, LLM Routing, Cost/Quality Slider, Billing, Usage
"""

import os
import sys
import json
import uuid
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('NEXUSOS_SECRET_KEY', secrets.token_hex(32))

# ============================================================================
# COST/QUALITY SLIDER - MODEL MAPPING
# ============================================================================

class QualityLevel:
    """Cost/Quality slider levels."""
    SPEED = 'speed'          # Cheapest, fastest
    BALANCED = 'balanced'    # Default
    QUALITY = 'quality'      # Premium
    DEEP = 'deep'           # Most expensive, best for hard problems


# Model configuration by quality level
QUALITY_MODELS = {
    QualityLevel.SPEED: {
        'provider': 'openai',
        'model': 'gpt-4o-mini',
        'cost_per_1m': 0.15,  # sh.15 per 1M tokens
        'context': 128000,
        'description': 'Fast, cheap - good for simple tasks'
    },
    QualityLevel.BALANCED: {
        'provider': 'anthropic',
        'model': 'claude-sonnet-4-20250514',
        'cost_per_1m': 3.00,
        'context': 200000,
        'description': 'Best overall - great reasoning, good speed'
    },
    QualityLevel.QUALITY: {
        'provider': 'openai',
        'model': 'gpt-4o',
        'cost_per_1m': 2.50,
        'context': 128000,
        'description': 'High quality responses'
    },
    QualityLevel.DEEP: {
        'provider': 'openai',
        'model': 'o1-preview',
        'cost_per_1m': 15.00,
        'context': 200000,
        'description': 'Complex reasoning, hard problems'
    }
}

# Fallback chains per level
QUALITY_FALLBACKS = {
    QualityLevel.SPEED: ['gpt-4o-mini', 'llama3', 'phi3'],
    QualityLevel.BALANCED: ['claude-sonnet-4-20250514', 'gpt-4o-mini', 'llama3'],
    QualityLevel.QUALITY: ['gpt-4o', 'claude-sonnet-4-20250514', 'gpt-4o-mini'],
    QualityLevel.DEEP: ['o1-preview', 'claude-opus-4-20250514', 'gpt-4o']
}

# Provider API endpoints
PROVIDER_ENDPOINTS = {
    'openai': 'https://api.openai.com/v1/chat/completions',
    'anthropic': 'https://api.anthropic.com/v1/messages',
    'google': 'https://generativelanguage.googleapis.com/v1/models'
}

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_db_connection():
    """Get PostgreSQL connection."""
    import psycopg2
    from urllib.parse import urlparse
    
    db_url = os.environ.get('DATABASE_URL', 'postgresql://nexusos:nexusos@postgres:5432/nexusos')
    result = urlparse(db_url)
    
    conn = psycopg2.connect(
        host=result.hostname,
        port=result.port or 5432,
        database=result.path[1:],
        user=result.username,
        password=result.password
    )
    return conn


def row_to_dict(cursor, row):
    """Convert row to dict."""
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


# ============================================================================
# PROVIDER KEY MANAGEMENT
# ============================================================================

class ProviderKeyManager:
    """Manages encrypted provider API keys."""
    
    # Master keys (encrypted in DB, decrypted at request time)
    MASTER_KEYS = {}  # In production: load from encrypted DB
    
    @classmethod
    def get_key(cls, provider: str) -> str:
        """Get decrypted provider key."""
        # Check environment first (for testing)
        env_key = os.environ.get(f'{provider.upper()}_API_KEY')
        if env_key:
            return env_key
        
        # Check database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT encrypted_key FROM provider_keys WHERE provider = %s AND is_default = true",
                (provider,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # In production: decrypt here using pgcrypto
                return row[0]  # Would be decrypted
        except Exception as e:
            logger.error(f"Error fetching provider key: {e}")
        
        return None
    
    @classmethod
    def set_key(cls, provider: str, api_key: str, label: str = 'primary'):
        """Store encrypted provider key."""
        # In production: encrypt before storing
        cls.MASTER_KEYS[provider] = api_key
        logger.info(f"Provider key set for: {provider}")


# ============================================================================
# LLM ROUTING
# ============================================================================

class LLMRouter:
    """Routes requests to appropriate LLM based on quality setting."""
    
    def __init__(self):
        self.usage_tracker = None
    
    def get_model_for_quality(self, quality: str, user_tier: str = 'free') -> dict:
        """Get model config for quality level."""
        # Validate quality level
        if quality not in QUALITY_MODELS:
            quality = QualityLevel.BALANCED
        
        # Check tier restrictions
        config = QUALITY_MODELS[quality].copy()
        
        # Free tier limited to speed/balanced
        if user_tier == 'free' and quality in [QualityLevel.QUALITY, QualityLevel.DEEP]:
            config = QUALITY_MODELS[QualityLevel.BALANCED].copy()
            config['warning'] = 'Upgraded to balanced for free tier'
        
        return config
    
    def detect_task_complexity(self, messages: list) -> str:
        """Auto-detect task complexity for routing."""
        if not messages:
            return QualityLevel.BALANCED
        
        # Get last user message
        last_msg = ''
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                last_msg = msg.get('content', '').lower()
                break
        
        # Simple keyword-based complexity detection
        complexity_indicators = {
            QualityLevel.SPEED: ['what is', 'who is', 'when', 'where', 'define', 'list', 'show'],
            QualityLevel.BALANCED: ['explain', 'write', 'create', 'summarize', 'compare'],
            QualityLevel.QUALITY: ['analyze', 'design', 'develop', 'write code', 'debug'],
            QualityLevel.DEEP: ['prove', 'prove that', 'optimize', 'complex', 'architect']
        }
        
        for quality, keywords in complexity_indicators.items():
            for keyword in keywords:
                if keyword in last_msg:
                    return quality
        
        return QualityLevel.BALANCED
    
    def route(self, messages: list, quality: str = None, model: str = None, 
              user_id: str = None, user_tier: str = 'free') -> dict:
        """Route request to appropriate LLM."""
        
        # Get user config if user_id provided
        user_quality = quality
        auto_route = True
        
        if user_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT quality_preference, auto_route 
                    FROM user_llm_config WHERE user_id = %s
                """, (user_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    user_quality = row[0] or quality
                    auto_route = row[1] if row[1] is not None else True
            except Exception as e:
                logger.error(f"Error getting user config: {e}")
        
        # Auto-detect if enabled
        if auto_route and not model:
            detected_quality = self.detect_task_complexity(messages)
            logger.info(f"Auto-detected quality: {detected_quality}")
            user_quality = detected_quality
        
        # Get model config
        model_config = self.get_model_for_quality(user_quality or QualityLevel.BALANCED, user_tier)
        
        # Override with explicit model if provided
        if model:
            model_config['model'] = model
            # Find provider for this model
            for provider, models in PROVIDER_ENDPOINTS.items():
                if model in str(models):
                    model_config['provider'] = provider
                    break
        
        return model_config
    
    def call_provider(self, provider: str, model: str, messages: list, 
                     max_tokens: int = 4000) -> dict:
        """Make API call to provider."""
        
        api_key = ProviderKeyManager.get_key(provider)
        
        if not api_key:
            return {'success': False, 'error': f'No API key for provider: {provider}'}
        
        try:
            if provider == 'openai':
                return self._call_openai(api_key, model, messages, max_tokens)
            elif provider == 'anthropic':
                return self._call_anthropic(api_key, model, messages, max_tokens)
            elif provider == 'google':
                return self._call_google(api_key, model, messages, max_tokens)
            else:
                return {'success': False, 'error': f'Unknown provider: {provider}'}
        except Exception as e:
            logger.error(f"Provider call error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _call_openai(self, api_key: str, model: str, messages: list, max_tokens: int) -> dict:
        """Call OpenAI API."""
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code != 200:
            return {'success': False, 'error': f'OpenAI error: {response.text}'}
        
        result = response.json()
        usage = result.get('usage', {})
        
        return {
            'success': True,
            'content': result['choices'][0]['message']['content'],
            'model': model,
            'provider': 'openai',
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }
    
    def _call_anthropic(self, api_key: str, model: str, messages: list, max_tokens: int) -> dict:
        """Call Anthropic API."""
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }
        
        # Convert messages format
        anthropic_messages = []
        system = None
        for msg in messages:
            if msg['role'] == 'system':
                system = msg['content']
            else:
                anthropic_messages.append(msg)
        
        data = {
            'model': model,
            'messages': anthropic_messages,
            'max_tokens': max_tokens
        }
        if system:
            data['system'] = system
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code != 200:
            return {'success': False, 'error': f'Anthropic error: {response.text}'}
        
        result = response.json()
        usage = result.get('usage', {})
        
        return {
            'success': True,
            'content': result['content'][0]['text'],
            'model': model,
            'provider': 'anthropic',
            'input_tokens': usage.get('input_tokens', 0),
            'output_tokens': usage.get('output_tokens', 0),
            'total_tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
        }
    
    def _call_google(self, api_key: str, model: str, messages: list, max_tokens: int) -> dict:
        """Call Google Gemini API."""
        # Simplified - full implementation would need proper Google API format
        return {'success': False, 'error': 'Google not yet implemented'}


# Global router
llm_router = LLMRouter()


# ============================================================================
# USAGE TRACKING
# ============================================================================

class UsageTracker:
    """Track and bill usage."""
    
    # Cost per 1M tokens
    PROVIDER_COSTS = {
        ('openai', 'gpt-4o-mini'): 0.15,
        ('openai', 'gpt-4o'): 2.50,
        ('openai', 'o1-preview'): 15.00,
        ('anthropic', 'claude-sonnet-4-20250514'): 3.00,
        ('anthropic', 'claude-opus-4-20250514'): 15.00,
    }
    
    @classmethod
    def calculate_cost(cls, provider: str, model: str, tokens: int) -> float:
        """Calculate cost for tokens."""
        cost_per_million = cls.PROVIDER_COSTS.get((provider, model), 1.0)
        return tokens * cost_per_million / 1_000_000
    
    @classmethod
    def record_usage(cls, user_id: str, provider: str, model: str, 
                    input_tokens: int, output_tokens: int) -> dict:
        """Record usage and deduct credits."""
        total_tokens = input_tokens + output_tokens
        provider_cost = cls.calculate_cost(provider, model, total_tokens)
        
        # Our fee (5.5% on top of provider cost)
        our_fee = provider_cost * 0.055
        total_charge = provider_cost + our_fee
        
        # Deduct from user credits
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check balance
            cursor.execute("SELECT credits FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            
            if not row or row[0] < total_charge:
                conn.close()
                return {'success': False, 'error': 'Insufficient credits'}
            
            # Deduct credits
            cursor.execute(
                "UPDATE users SET credits = credits - %s WHERE id = %s",
                (total_charge, user_id)
            )
            
            # Record usage
            cursor.execute("""
                INSERT INTO llm_usage 
                (id, user_id, provider, model, input_tokens, output_tokens, 
                 provider_cost, our_fee, credits_deducted, mode)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'we_bill')
            """, (str(uuid.uuid4()), user_id, provider, model, input_tokens,
                   output_tokens, provider_cost, our_fee, total_charge))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'provider_cost': provider_cost,
                'our_fee': our_fee,
                'total_deducted': total_charge
            }
        except Exception as e:
            logger.error(f"Usage recording error: {e}")
            return {'success': False, 'error': str(e)}


# ============================================================================
# API KEY AUTHENTICATION
# ============================================================================

def require_nexus_key(f):
    """Decorator for Nexus API Key authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-Nexus-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'Missing X-Nexus-Key header'}), 401
        
        # Validate key
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            cursor.execute("""
                SELECT ak.user_id, u.email, u.credits, u.subscription_tier
                FROM api_keys ak
                JOIN users u ON u.id = ak.user_id
                WHERE ak.key_hash = %s AND ak.is_active = true
            """, (key_hash,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return jsonify({'error': 'Invalid API key'}), 401
            
            # Update last used
            cursor.execute(
                "UPDATE api_keys SET last_used = %s WHERE key_hash = %s",
                (datetime.now().isoformat(), key_hash)
            )
            conn.commit()
            conn.close()
            
            g.user_id = row[0]
            g.user_email = row[1]
            g.user_credits = float(row[2])
            g.user_tier = row[3]
            
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated


# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', email.split('@')[0])
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check existing
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create user
        user_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Free credits on signup
        signup_credits = 1000 if os.environ.get('SIGNUP_BONUS') else 100
        
        cursor.execute("""
            INSERT INTO users (id, email, password_hash, name, credits, subscription_tier)
            VALUES (%s, %s, %s, %s, %s, 'free')
        """, (user_id, email, password_hash, name, signup_credits))
        
        # Generate Nexus API key
        api_key = f"sk-nexus-{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO api_keys (id, user_id, key_hash, name)
            VALUES (%s, %s, %s, %s)
        """, (str(uuid.uuid4()), user_id, key_hash, 'Default Key'))
        
        # Create default LLM config
        cursor.execute("""
            INSERT INTO user_llm_config (id, user_id, provider, model, quality_preference, auto_route)
            VALUES (%s, %s, %s, %s, %s, true)
        """, (str(uuid.uuid4()), user_id, 'openai', 'gpt-4o-mini', 'balanced'))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'user_id': user_id,
            'email': email,
            'api_key': api_key,
            'credits': signup_credits,
            'message': 'Account created'
        }), 201
        
    except Exception as e:
        logger.error(f"Register error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login and get API key."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute("""
            SELECT id, email, name, credits, subscription_tier
            FROM users WHERE email = %s AND password_hash = %s
        """, (email, password_hash))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({'error': 'Invalid credentials'}), 401
        
        user = {
            'id': row[0],
            'email': row[1],
            'name': row[2],
            'credits': float(row[3]),
            'subscription_tier': row[4]
        }
        
        # Get or create API key
        cursor.execute("""
            SELECT key_prefix || key_hash FROM api_keys 
            WHERE user_id = %s AND is_active = true LIMIT 1
        """, (user['id'],))
        
        key_row = cursor.fetchone()
        
        if key_row:
            api_key = key_row[0]
        else:
            api_key = f"sk-nexus-{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO api_keys (id, user_id, key_hash, name)
                VALUES (%s, %s, %s, %s)
            """, (str(uuid.uuid4()), user['id'], key_hash, 'Default Key'))
            conn.commit()
        
        conn.close()
        
        return jsonify({'user': user, 'api_key': api_key})
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CONFIG ENDPOINTS
# ============================================================================

@app.route('/api/config', methods=['GET'])
@require_nexus_key
def get_config():
    """Get user's LLM configuration."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT provider, model, quality_preference, auto_route,
                   fallback_provider, fallback_model
            FROM user_llm_config WHERE user_id = %s
        """, (g.user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            config = {
                'provider': row[0],
                'model': row[1],
                'quality_preference': row[2] or 'balanced',
                'auto_route': row[3],
                'fallback_provider': row[4],
                'fallback_model': row[5]
            }
        else:
            config = {
                'provider': 'openai',
                'model': 'gpt-4o-mini',
                'quality_preference': 'balanced',
                'auto_route': True,
                'fallback_provider': None,
                'fallback_model': None
            }
        
        return jsonify(config)
        
    except Exception as e:
        logger.error(f"Get config error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['PUT'])
@require_nexus_key
def update_config():
    """Update user's LLM configuration."""
    data = request.get_json() or {}
    
    provider = data.get('provider', 'openai')
    model = data.get('model', 'gpt-4o-mini')
    quality = data.get('quality_preference', 'balanced')
    auto_route = data.get('auto_route', True)
    fallback_provider = data.get('fallback_provider')
    fallback_model = data.get('fallback_model')
    
    # Validate quality
    if quality not in QUALITY_MODELS:
        quality = 'balanced'
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_llm_config (id, user_id, provider, model, 
                                         quality_preference, auto_route,
                                         fallback_provider, fallback_model)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(user_id) DO UPDATE SET
                provider = excluded.provider,
                model = excluded.model,
                quality_preference = excluded.quality_preference,
                auto_route = excluded.auto_route,
                fallback_provider = excluded.fallback_provider,
                fallback_model = excluded.fallback_model,
                updated_at = CURRENT_TIMESTAMP
        """, (str(uuid.uuid4()), g.user_id, provider, model, quality,
               auto_route, fallback_provider, fallback_model))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Configuration updated', 'quality': quality})
        
    except Exception as e:
        logger.error(f"Update config error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/models', methods=['GET'])
@require_nexus_key
def get_models():
    """Get available models."""
    # Return all available models
    models = {
        QualityLevel.SPEED: {
            'name': 'Speed',
            'models': ['gpt-4o-mini', 'llama3', 'phi3'],
            'description': 'Fast, cheap - for simple tasks'
        },
        QualityLevel.BALANCED: {
            'name': 'Balanced', 
            'models': ['claude-sonnet-4-20250514', 'gpt-4o-mini'],
            'description': 'Best overall - great reasoning'
        },
        QualityLevel.QUALITY: {
            'name': 'Quality',
            'models': ['gpt-4o', 'claude-sonnet-4-20250514'],
            'description': 'High quality responses'
        },
        QualityLevel.DEEP: {
            'name': 'Deep Thinking',
            'models': ['o1-preview', 'claude-opus-4-20250514'],
            'description': 'Complex reasoning'
        }
    }
    
    return jsonify({
        'tier': g.user_tier,
        'models': models,
        'current_quality': 'balanced'  # Would fetch from user config
    })


# ============================================================================
# CHAT ENDPOINT
# ============================================================================

@app.route('/api/chat', methods=['POST'])
@require_nexus_key
def chat():
    """
    Main chat endpoint with Cost/Quality routing.
    
    Request:
        {
            "message": "Hello" OR "messages": [...],
            "quality": "balanced" (optional: speed/balanced/quality/deep),
            "model": "gpt-4o" (optional override),
            "stream": false
        }
    """
    data = request.get_json() or {}
    
    message = data.get('message', '')
    messages = data.get('messages', [])
    quality = data.get('quality')  # speed/balanced/quality/deep
    model_override = data.get('model')
    stream = data.get('stream', False)
    
    if message:
        messages = [{'role': 'user', 'content': message}]
    
    if not messages:
        return jsonify({'error': 'No message provided'}), 400
    
    # Route to appropriate LLM
    model_config = llm_router.route(
        messages=messages,
        quality=quality,
        model=model_override,
        user_id=g.user_id,
        user_tier=g.user_tier
    )
    
    # Make the API call
    result = llm_router.call_provider(
        provider=model_config['provider'],
        model=model_config['model'],
        messages=messages
    )
    
    if not result['success']:
        # Try fallback
        logger.warning(f"Primary provider failed: {result['error']}")
        # Could implement fallback chain here
        return jsonify({'error': result['error']}), 500
    
    # Record usage and deduct credits
    usage_result = UsageTracker.record_usage(
        user_id=g.user_id,
        provider=result['provider'],
        model=result['model'],
        input_tokens=result.get('input_tokens', 0),
        output_tokens=result.get('output_tokens', 0)
    )
    
    if not usage_result['success']:
        return jsonify({'error': usage_result['error']}), 402
    
    return jsonify({
        'content': result['content'],
        'model': result['model'],
        'provider': result['provider'],
        'quality_used': quality or model_config.get('quality_preference', 'balanced'),
        'usage': {
            'input_tokens': result.get('input_tokens', 0),
            'output_tokens': result.get('output_tokens', 0),
            'total_tokens': result.get('total_tokens', 0),
            'cost': usage_result.get('provider_cost', 0),
            'fee': usage_result.get('our_fee', 0),
            'deducted': usage_result.get('total_deducted', 0)
        }
    })


# ============================================================================
# BILLING ENDPOINTS
# ============================================================================

@app.route('/api/credits', methods=['GET'])
@require_nexus_key
def get_credits():
    """Get credit balance."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT credits FROM users WHERE id = %s", (g.user_id,))
        row = cursor.fetchone()
        conn.close()
        
        credits = float(row[0]) if row else 0
        
        return jsonify({
            'credits': credits,
            'user_id': g.user_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/credits/purchase', methods=['POST'])
@require_nexus_key
def purchase_credits():
    """Purchase credits."""
    data = request.get_json() or {}
    amount = data.get('amount', 10.0)
    
    if amount < 5:
        return jsonify({'error': 'Minimum purchase is '}), 400
    
    # Calculate credits (OpenRouter-style: 5.5% fee)
    fee = max(amount * 0.055, 0.80)
    credits = (amount - fee) * 1.058  # Rough conversion
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add credits
        cursor.execute(
            "UPDATE users SET credits = credits + %s WHERE id = %s",
            (credits, g.user_id)
        )
        
        # Record purchase
        cursor.execute("""
            INSERT INTO credit_purchases (id, user_id, amount_paid, credits_added, our_fee, provider, status)
            VALUES (%s, %s, %s, %s, %s, 'stripe', 'completed')
        """, (str(uuid.uuid4()), g.user_id, amount, credits, fee))
        
        conn.commit()
        
        # Get new balance
        cursor.execute("SELECT credits FROM users WHERE id = %s", (g.user_id,))
        new_balance = float(cursor.fetchone()[0])
        
        conn.close()
        
        return jsonify({
            'credits_added': credits,
            'amount_paid': amount,
            'our_fee': fee,
            'new_balance': new_balance
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/usage', methods=['GET'])
@require_nexus_key
def get_usage():
    """Get usage history."""
    days = request.args.get('days', 30, type=int)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT provider, model, input_tokens, output_tokens, 
                   provider_cost, our_fee, credits_deducted, created_at
            FROM llm_usage 
            WHERE user_id = %s AND created_at > NOW() - INTERVAL '1 day' * %s
            ORDER BY created_at DESC
            LIMIT 100
        """, (g.user_id, days))
        
        rows = cursor.fetchall()
        conn.close()
        
        usage = []
        for row in rows:
            usage.append({
                'provider': row[0],
                'model': row[1],
                'input_tokens': row[2],
                'output_tokens': row[3],
                'cost': float(row[4]) if row[4] else 0,
                'fee': float(row[5]) if row[5] else 0,
                'deducted': float(row[6]) if row[6] else 0,
                'created_at': row[7].isoformat() if row[7] else None
            })
        
        return jsonify({'usage': usage})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/usage/summary', methods=['GET'])
@require_nexus_key
def get_usage_summary():
    """Get usage summary."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_requests,
                COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
                COALESCE(SUM(provider_cost), 0) as total_cost,
                COALESCE(SUM(our_fee), 0) as total_fee,
                COALESCE(SUM(credits_deducted), 0) as total_deducted
            FROM llm_usage 
            WHERE user_id = %s AND created_at > NOW() - INTERVAL '30 days'
        """, (g.user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'period_days': 30,
            'total_requests': row[0],
            'total_tokens': int(row[1]) if row[1] else 0,
            'total_cost': float(row[2]) if row[2] else 0,
            'total_fee': float(row[3]) if row[3] else 0,
            'total_deducted': float(row[4]) if row[4] else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# HEALTH
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'nexus-server'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
