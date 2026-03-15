"""
NexusOS Usage Analytics Module
================================
Adds /api/usage endpoint for tracking token usage, costs, and agent activity.

This module integrates with the existing database's usage_stats table.
"""
import os
import sqlite3
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g

usage_bp = Blueprint('usage', __name__)

DB_PATH = os.environ.get("NEXUSOS_DB", "/opt/nexusos-data/nexusos.db")
USE_PG = os.environ.get('USE_PG', '').lower() in ('1', 'true', 'yes')

# Import PostgreSQL if available
if USE_PG:
    try:
        from database_v2 import get_db as get_pg_db
        _pg_db = get_pg_db
    except ImportError:
        USE_PG = False

def get_db():
    if USE_PG:
        return _pg_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== USAGE ANALYTICS ====================

@usage_bp.route('/api/usage', methods=['GET'])
def get_usage():
    """Get usage stats - requires auth"""
    # Check for auth (reusing auth logic from main app)
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Auth required'}), 401
    
    # Get date range from query params
    days = request.args.get('days', 7, type=int)
    user_id = request.args.get('user_id', None)  # None = all users
    
    conn = get_db()
    try:
        c = conn.cursor()
        
        # Base query - use PostgreSQL syntax
        if user_id:
            c.execute("""
                SELECT 
                    DATE(created_at) as date,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(requests) as requests,
                    SUM(cost_usd) as cost,
                    model,
                    provider
                FROM usage_stats 
                WHERE user_id = %s AND created_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(created_at), model, provider
                ORDER BY date DESC
            """, (user_id, days))
        else:
            c.execute("""
                SELECT 
                    DATE(created_at) as date,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(requests) as requests,
                    SUM(cost_usd) as cost,
                    model,
                    provider
                FROM usage_stats 
                WHERE created_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(created_at), model, provider
                ORDER BY date DESC
            """, (days,))
        
        rows = c.fetchall()
        
        # Aggregate totals
        total_input = sum(r['input_tokens'] or 0 for r in rows)
        total_output = sum(r['output_tokens'] or 0 for r in rows)
        total_tokens = sum(r['total_tokens'] or 0 for r in rows)
        total_requests = sum(r['requests'] or 0 for r in rows)
        total_cost = sum(r['cost'] or 0 for r in rows)
        
        return jsonify({
            'period_days': days,
            'summary': {
                'total_input_tokens': total_input,
                'total_output_tokens': total_output,
                'total_tokens': total_tokens,
                'total_requests': total_requests,
                'total_cost_usd': round(total_cost, 4)
            },
            'by_date': [dict(r) for r in rows]
        })
    finally:
        conn.close()

@usage_bp.route('/api/usage/summary', methods=['GET'])
def get_usage_summary():
    """Quick summary - total usage all time"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Auth required'}), 401
    
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT 
                COUNT(*) as total_requests,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0) as total_cost,
                COALESCE(SUM(requests), 0) as total_calls
            FROM usage_stats
        """)
        row = c.fetchone()
        return jsonify({
            'total_requests': row['total_requests'],
            'total_tokens': row['total_tokens'],
            'total_cost_usd': round(row['total_cost'], 4)
        })
    finally:
        conn.close()

@usage_bp.route('/api/usage/user/<target_user_id>', methods=['GET'])
def get_user_usage(target_user_id):
    """Get usage for specific user - admin only"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Auth required'}), 401
    
    days = request.args.get('days', 30, type=int)
    
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT 
                DATE(created_at) as date,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(requests) as requests,
                SUM(cost_usd) as cost,
                model,
                provider
            FROM usage_stats 
            WHERE user_id = %s AND created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at), model
            ORDER BY date DESC
        """, (target_user_id, days))
        
        rows = c.fetchall()
        
        total_tokens = sum(r['total_tokens'] or 0 for r in rows)
        total_cost = sum(r['cost'] or 0 for r in rows)
        
        return jsonify({
            'user_id': target_user_id,
            'period_days': days,
            'total_tokens': total_tokens,
            'total_cost_usd': round(total_cost, 4),
            'daily_breakdown': [dict(r) for r in rows]
        })
    finally:
        conn.close()

@usage_bp.route('/api/usage/track', methods=['POST'])
def track_usage():
    """Track a new usage event"""
    data = request.get_json()
    
    required = ['user_id', 'model', 'input_tokens', 'output_tokens']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400
    
    total_tokens = data['input_tokens'] + data['output_tokens']
    
    # Estimate cost (can be refined with actual pricing)
    cost_per_1k = {
        ('gpt-4', 'openai'): 0.03,
        ('gpt-4o', 'openai'): 0.005,
        ('gpt-4o-mini', 'openai'): 0.0002,
        ('claude-3-5-sonnet', 'anthropic'): 0.003,
        ('claude-3-haiku', 'anthropic'): 0.00025,
        ('default', 'default'): 0.001
    }
    model = data.get('model', 'unknown')
    provider = data.get('provider', 'default')
    rate = cost_per_1k.get((model, provider), cost_per_1k[('default', 'default')])
    cost = (total_tokens / 1000) * rate
    
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO usage_stats 
            (user_id, model, provider, input_tokens, output_tokens, total_tokens, requests, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            data['user_id'],
            model,
            provider,
            data['input_tokens'],
            data['output_tokens'],
            total_tokens,
            cost
        ))
        conn.commit()
        return jsonify({'success': True, 'cost_usd': round(cost, 6)})
    finally:
        conn.close()

# ==================== AGENT ACTIVITY TRACKING ====================

@usage_bp.route('/api/agents/stats', methods=['GET'])
def get_agent_stats():
    """Get agent activity statistics"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Auth required'}), 401
    
    conn = get_db()
    try:
        c = conn.cursor()
        
        # Get agent counts by status
        c.execute("""
            SELECT status, COUNT(*) as count 
            FROM agents 
            GROUP BY status
        """)
        status_counts = {r['status']: r['count'] for r in c.fetchall()}
        
        # Get recently active agents
        c.execute("""
            SELECT name, status, last_active, updated_at 
            FROM agents 
            ORDER BY updated_at DESC 
            LIMIT 10
        """)
        recent = [dict(r) for r in c.fetchall()]
        
        return jsonify({
            'by_status': status_counts,
            'recent_agents': recent
        })
    finally:
        conn.close()

# Integration: Add these routes to your Flask app
# from usage_analytics import usage_bp
# app.register_blueprint(usage_bp)
