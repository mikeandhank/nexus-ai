"""
Credit & Balance API - Live balance for customer portal
========================================================
GET /api/credits - Get current balance
POST /api/credits/purchase - Purchase credits
GET /api/usage/live - Get real-time usage
"""

from flask import Blueprint, jsonify, request
from datetime import datetime

credits_bp = Blueprint('credits', __name__)

# Extended model pricing (50+ models)
MODEL_PRICING = {
    # OpenAI
    "openai/gpt-4o": {"input": 0.01, "output": 0.03, "provider": "openai"},
    "openai/gpt-4o-mini": {"input": 0.0015, "output": 0.006, "provider": "openai"},
    "openai/gpt-4-turbo": {"input": 0.03, "output": 0.06, "provider": "openai"},
    "openai/gpt-4": {"input": 0.06, "output": 0.12, "provider": "openai"},
    "openai/gpt-3.5-turbo": {"input": 0.002, "output": 0.008, "provider": "openai"},
    
    # Anthropic
    "anthropic/claude-3.5-sonnet": {"input": 0.003, "output": 0.015, "provider": "anthropic"},
    "anthropic/claude-3-opus": {"input": 0.015, "output": 0.075, "provider": "anthropic"},
    "anthropic/claude-3-sonnet": {"input": 0.003, "output": 0.015, "provider": "anthropic"},
    "anthropic/claude-3-haiku": {"input": 0.00025, "output": 0.00125, "provider": "anthropic"},
    
    # Meta
    "meta-llama/llama-3.1-405b-instruct": {"input": 0.0032, "output": 0.0032, "provider": "meta"},
    "meta-llama/llama-3.1-70b-instruct": {"input": 0.0009, "output": 0.0009, "provider": "meta"},
    "meta-llama/llama-3.1-8b-instruct": {"input": 0.0002, "output": 0.0002, "provider": "meta"},
    "meta-llama/llama-3-70b-instruct": {"input": 0.0008, "output": 0.0008, "provider": "meta"},
    "meta-llama/llama-3-8b-instruct": {"input": 0.0002, "output": 0.0002, "provider": "meta"},
    
    # Google
    "google/gemini-pro-1.5": {"input": 0.00125, "output": 0.005, "provider": "google"},
    "google/gemini-pro": {"input": 0.00125, "output": 0.005, "provider": "google"},
    "google/gemini-flash-1.5": {"input": 0.000075, "output": 0.0003, "provider": "google"},
    
    # Mistral
    "mistralai/mistral-large": {"input": 0.002, "output": 0.006, "provider": "mistral"},
    "mistralai/mistral-medium": {"input": 0.0014, "output": 0.0046, "provider": "mistral"},
    "mistralai/mistral-small": {"input": 0.0006, "output": 0.002, "provider": "mistral"},
    "mistralai/mistral-7b-instruct": {"input": 0.0002, "output": 0.0002, "provider": "mistral"},
    
    # Cohere
    "cohere/command-r-plus": {"input": 0.003, "output": 0.015, "provider": "cohere"},
    "cohere/command-r": {"input": 0.0005, "output": 0.0015, "provider": "cohere"},
    
    # DeepSeek
    "deepseek/deepseek-chat": {"input": 0.00014, "output": 0.00028, "provider": "deepseek"},
    "deepseek/deepseek-coder": {"input": 0.00014, "output": 0.00028, "provider": "deepseek"},
    
    # Anthropic (Claude via OpenRouter)
    "anthropic/claude-3.5-sonnet-20241022": {"input": 0.003, "output": 0.015, "provider": "anthropic"},
    "anthropic/claude-3-opus-20240229": {"input": 0.015, "output": 0.075, "provider": "anthropic"},
    "anthropic/claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015, "provider": "anthropic"},
    "anthropic/claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125, "provider": "anthropic"},
    
    # OpenAI via OpenRouter
    "openai/gpt-4o-20241120": {"input": 0.01, "output": 0.03, "provider": "openai"},
    "openai/gpt-4o-mini-20240718": {"input": 0.0015, "output": 0.006, "provider": "openai"},
    "openai/gpt-4-turbo-20240409": {"input": 0.03, "output": 0.06, "provider": "openai"},
    
    # Qwen
    "qwen/qwen-2-72b-instruct": {"input": 0.0009, "output": 0.001, "provider": "qwen"},
    "qwen/qwen-2-7b-instruct": {"input": 0.0002, "output": 0.0002, "provider": "qwen"},
    
    # Microsoft
    "microsoft/wizardlm-2-8x22b": {"input": 0.0012, "output": 0.0012, "provider": "microsoft"},
    "microsoft/wizardlm-2-7b": {"input": 0.0002, "output": 0.0002, "provider": "microsoft"},
    
    # Nvidia
    "nvidia/nemotron-70b-instruct": {"input": 0.0009, "output": 0.0009, "provider": "nvidia"},
    
    # Fireworks
    "fireworks/firefunction-v2": {"input": 0.003, "output": 0.003, "provider": "fireworks"},
    "fireworks/fireagent-7b": {"input": 0.0002, "output": 0.0002, "provider": "fireworks"},
    
    # Together
    "together/llama-3-8b-chat": {"input": 0.0002, "output": 0.0002, "provider": "together"},
    "together/llama-3-70b-chat": {"input": 0.0008, "output": 0.0008, "provider": "together"},
    
    # Perplexity
    "perplexity/pplx-7b-online": {"input": 0.001, "output": 0.001, "provider": "perplexity"},
    "perplexity/pplx-70b-online": {"input": 0.001, "output": 0.001, "provider": "perplexity"},
    
    # 01.AI
    "01-ai/yi-large": {"input": 0.003, "output": 0.015, "provider": "01-ai"},
    "01-ai/yi-medium": {"input": 0.001, "output": 0.003, "provider": "01-ai"},
    
    # Local/Ollama (fallback pricing)
    "ollama/llama3": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/llama3.1": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/codellama": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/mistral": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/phi3": {"input": 0.0, "output": 0.0, "provider": "ollama"},
}

SERVICE_FEE_PERCENT = 0.055  # 5.5%


@credits_bp.route('/api/credits', methods=['GET'])
def get_credits():
    """Get current user's credit balance - LIVE"""
    from flask import g
    
    user_id = g.get('user_id')
    if not user_id:
        # For demo/testing
        user_id = request.args.get('user_id', 'demo')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get balance
    cursor.execute("""
        SELECT balance, total_spent, total_reloaded, updated_at 
        FROM user_balances 
        WHERE user_id = %s
    """, (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({
            'balance': 0.0,
            'total_spent': 0.0,
            'total_reloaded': 0.0,
            'currency': 'USD'
        })
    
    return jsonify({
        'balance': float(row[0] or 0),
        'total_spent': float(row[1] or 0),
        'total_reloaded': float(row[2] or 0),
        'last_updated': row[3].isoformat() if row[3] else None,
        'currency': 'USD'
    })


@credits_bp.route('/api/credits/purchase', methods=['POST'])
def purchase_credits():
    """Purchase credits - adds balance"""
    from flask import g
    import uuid
    
    user_id = g.get('user_id')
    data = request.get_json() or {}
    
    # Get amount from request
    credits_desired = data.get('credits', 0)
    if not credits_desired:
        return jsonify({'error': 'Credits amount required'}), 400
    
    if user_id is None:
        return jsonify({'error': 'Authentication required'}), 401
    
    base_amount = float(credits_desired)
    service_fee = base_amount * SERVICE_FEE_PERCENT
    total_charged = base_amount + service_fee
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update balance
    cursor.execute("""
        INSERT INTO user_balances (user_id, balance, total_reloaded, updated_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            balance = user_balances.balance + %s,
            total_reloaded = user_balances.total_reloaded + %s,
            updated_at = NOW()
    """, (user_id, base_amount, base_amount, base_amount, base_amount))
    
    # Record transaction
    cursor.execute("""
        INSERT INTO credit_transactions 
        (id, user_id, transaction_type, amount, credits, service_fee, total_charged, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """, (str(uuid.uuid4()), user_id, 'purchase', total_charged, credits_desired, service_fee, total_charged, 'pending'))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'credits_added': credits_desired,
        'base_amount': base_amount,
        'service_fee': service_fee,
        'total_charged': total_charged,
        'new_balance': base_amount  # Would fetch actual balance in production
    })


@credits_bp.route('/api/usage/live', methods=['GET'])
def live_usage():
    """Get real-time usage for current user"""
    from flask import g
    
    user_id = g.get('user_id')
    if not user_id:
        user_id = request.args.get('user_id', 'demo')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get today's usage
    cursor.execute("""
        SELECT 
            COALESCE(SUM(total_tokens), 0) as total_tokens,
            COALESCE(SUM(cost_usd), 0) as total_cost,
            COALESCE(SUM(requests), 0) as total_requests,
            model,
            provider
        FROM usage_stats 
        WHERE user_id = %s AND created_at >= CURRENT_DATE
        GROUP BY model, provider
    """, (user_id,))
    
    rows = cursor.fetchall()
    
    # Get balance
    cursor.execute("SELECT balance FROM user_balances WHERE user_id = %s", (user_id,))
    balance_row = cursor.fetchone()
    current_balance = float(balance_row[0]) if balance_row else 0
    
    conn.close()
    
    return jsonify({
        'user_id': user_id,
        'current_balance': current_balance,
        'today': {
            'total_tokens': sum(r[0] for r in rows),
            'total_cost': sum(r[1] for r in rows),
            'total_requests': sum(r[2] for r in rows),
            'by_model': [
                {
                    'model': r[3],
                    'provider': r[4],
                    'tokens': r[0],
                    'cost': r[1],
                    'requests': r[2]
                } for r in rows
            ]
        }
    })


def get_db_connection():
    """Get database connection"""
    import os
    db_url = os.environ.get('DATABASE_URL', 'postgresql://lipaira:lipaira@postgres:5432/lipaira')
    
    if db_url.startswith('postgresql://'):
        import psycopg2
        # Parse connection string
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/')
        )
    else:
        import sqlite3
        return sqlite3.connect('lipaira.db')


# Helper to calculate cost from tokens
def calculate_token_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for a request based on model pricing"""
    model_info = MODEL_PRICING.get(model, {"input": 0.01, "output": 0.01})
    
    input_cost = (input_tokens / 1000) * model_info["input"]
    output_cost = (output_tokens / 1000) * model_info["output"]
    
    return input_cost + output_cost


# Usage tracking middleware
def track_usage_and_deduct(user_id: str, model: str, input_tokens: int, output_tokens: int):
    """Track usage and deduct from balance atomically"""
    cost = calculate_token_cost(model, input_tokens, output_tokens)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert usage record
    cursor.execute("""
        INSERT INTO usage_stats 
        (user_id, model, provider, input_tokens, output_tokens, total_tokens, requests, cost_usd, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, 1, %s, NOW())
    """, (user_id, model, MODEL_PRICING.get(model, {}).get('provider', 'unknown'),
          input_tokens, output_tokens, input_tokens + output_tokens, cost))
    
    # Deduct from balance
    cursor.execute("""
        UPDATE user_balances 
        SET balance = balance - %s, 
            total_spent = total_spent + %s,
            updated_at = NOW()
        WHERE user_id = %s
        AND balance >= %s
    """, (cost, cost, user_id, cost))
    
    conn.commit()
    conn.close()
    
    return cost
