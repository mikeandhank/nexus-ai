"""
NexusOS PostgreSQL Connection Pooling
With health checks and automatic reconnection.
"""

import os
import time
import threading
from contextlib import contextmanager

class ConnectionPool:
    """PostgreSQL connection pool with health checks"""
    
    def __init__(self, database_url, min_connections=2, max_connections=10, health_check_interval=30):
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval
        self.pool = []
        self.lock = threading.Lock()
        self.last_health_check = 0
        self.is_healthy = True
        
        # Initialize min connections
        self._init_pool()
        
        # Start health check thread
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()
    
    def _init_pool(self):
        """Initialize connection pool"""
        import psycopg2
        for _ in range(self.min_connections):
            try:
                conn = psycopg2.connect(self.database_url)
                self.pool.append(conn)
            except Exception as e:
                print(f"[ConnectionPool] Failed to create connection: {e}")
    
    @contextmanager
    def get_connection(self):
        """Get a connection from pool"""
        conn = None
        acquired = False
        
        try:
            with self.lock:
                if self.pool:
                    conn = self.pool.pop()
                    acquired = True
            
            # Test connection
            try:
                conn.isolation_level
                conn.autocommit = False
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                # Try to reconnect
                try:
                    import psycopg2
                    conn = psycopg2.connect(self.database_url)
                    yield conn
                    conn.commit()
                except:
                    # Create new connection
                    import psycopg2
                    conn = psycopg2.connect(self.database_url)
                    yield conn
                    conn.commit()
        finally:
            if conn and acquired:
                with self.lock:
                    if len(self.pool) < self.max_connections:
                        self.pool.append(conn)
                    else:
                        conn.close()
    
    def _health_check_loop(self):
        """Background health check"""
        import psycopg2
        while True:
            time.sleep(self.health_check_interval)
            try:
                with self.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    self.is_healthy = True
                    print("[ConnectionPool] Health check OK")
            except Exception as e:
                self.is_healthy = False
                print(f"[ConnectionPool] Health check FAILED: {e}")
    
    def get_status(self):
        """Get pool status"""
        return {
            'healthy': self.is_healthy,
            'active_connections': len(self.pool),
            'min_connections': self.min_connections,
            'max_connections': self.max_connections,
            'last_check': self.last_health_check
        }
    
    def close_all(self):
        """Close all connections"""
        with self.lock:
            for conn in self.pool:
                try:
                    conn.close()
                except:
                    pass
            self.pool.clear()


# Global pool instance
_pool = None

def get_pool():
    """Get or create connection pool"""
    global _pool
    if _pool is None:
        database_url = os.environ.get('DATABASE_URL', '')
        if database_url:
            _pool = ConnectionPool(database_url)
    return _pool

def setup_pool_routes(app):
    """Add pool status route"""
    @app.route('/api/pool/status', methods=['GET'])
    def pool_status():
        pool = get_pool()
        if pool:
            return pool.get_status()
        return {'error': 'Pool not initialized'}, 500
