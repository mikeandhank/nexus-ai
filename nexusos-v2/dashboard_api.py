"""
NexusOS Real-time Dashboard API
"""

from flask import jsonify
import time
import os

def setup_dashboard_routes(app):
    """Add real-time dashboard routes"""
    
    @app.route('/api/dashboard', methods=['GET'])
    def dashboard():
        """Real-time system dashboard"""
        import psutil
        from flask import current_app
        
        # Base stats
        stats = {
            'timestamp': time.time(),
            'system': {
                'uptime': get_uptime(),
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        }
        
        # Get database connection from app
        try:
            use_pg = current_app.config.get('USE_PG', False)
            if use_pg:
                # Import here to avoid circular imports
                from api_server_v5 import get_pg_conn
                conn = get_pg_conn()
                cur = conn.cursor()
                
                # User count
                cur.execute("SELECT COUNT(*) FROM users")
                stats['users'] = cur.fetchone()[0]
                
                # Agent count
                cur.execute("SELECT COUNT(*) FROM agents")
                stats['agents'] = cur.fetchone()[0]
                
                # Conversation count
                cur.execute("SELECT COUNT(*) FROM conversations")
                stats['conversations'] = cur.fetchone()[0]
                
                # Message count
                cur.execute("SELECT COUNT(*) FROM messages")
                stats['messages'] = cur.fetchone()[0]
                
                # Today's usage
                cur.execute("""
                    SELECT COUNT(*), COALESCE(SUM(total_tokens), 0), COALESCE(SUM(cost_usd), 0)
                    FROM usage_stats 
                    WHERE created_at >= CURRENT_DATE
                """)
                row = cur.fetchone()
                stats['usage_today'] = {
                    'requests': row[0],
                    'tokens': row[1],
                    'cost_usd': float(row[2])
                }
                
                # Active sessions (last 30 min)
                cur.execute("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM conversations 
                    WHERE updated_at >= NOW() - INTERVAL '30 minutes'
                """)
                stats['active_sessions_30m'] = cur.fetchone()[0]
                
                conn.close()
        except Exception as e:
            stats['db_error'] = str(e)
        
        # Redis stats
        try:
            from api_server_v5 import redis_client
            if redis_client:
                info = redis_client.info()
                stats['redis'] = {
                    'connected': True,
                    'clients': info.get('connected_clients', 0),
                    'memory_used': info.get('used_memory_human', '0'),
                    'commands_processed': info.get('total_commands_processed', 0)
                }
        except:
            stats['redis'] = {'connected': False}
        
        return jsonify(stats)
    
    @app.route('/api/dashboard/agents', methods=['GET'])
    def dashboard_agents():
        """Real-time agent status"""
        try:
            from api_server_v5 import get_pg_conn, current_app
            if not current_app.config.get('USE_PG', False):
                return jsonify({'agents': []})
            
            conn = get_pg_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, status, model, created_at, updated_at
                FROM agents
                ORDER BY updated_at DESC
                LIMIT 50
            """)
            agents = []
            for row in cur.fetchall():
                agents.append({
                    'id': row[0],
                    'name': row[1],
                    'status': row[2],
                    'model': row[3],
                    'created_at': str(row[4]),
                    'updated_at': str(row[5])
                })
            conn.close()
            return jsonify({'agents': agents})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/dashboard/usage', methods=['GET'])
    def dashboard_usage():
        """Usage over time"""
        try:
            from api_server_v5 import get_pg_conn, current_app
            if not current_app.config.get('USE_PG', False):
                return jsonify({'error': 'PostgreSQL not available'})
            
            conn = get_pg_conn()
            cur = conn.cursor()
            
            # Last 7 days daily usage
            cur.execute("""
                SELECT DATE(created_at) as day,
                       COUNT(*) as requests,
                       COALESCE(SUM(total_tokens), 0) as tokens,
                       COALESCE(SUM(cost_usd), 0) as cost
                FROM usage_stats
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY day
            """)
            
            daily = []
            for row in cur.fetchall():
                daily.append({
                    'date': str(row[0]),
                    'requests': row[1],
                    'tokens': int(row[2]),
                    'cost_usd': float(row[3])
                })
            
            conn.close()
            return jsonify({'daily': daily})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


def get_uptime():
    """Get system uptime"""
    try:
        with open('/proc/uptime') as f:
            return float(f.readline().split()[0])
    except:
        return 0
