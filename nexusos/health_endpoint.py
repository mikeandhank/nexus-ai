"""
NexusOS Enterprise - Health Check Endpoint
Add this to api_server_v5.py for production monitoring
"""

# Add this import at the top of api_server_v5.py:
# import psycopg2

# Add this function and endpoint to api_server_v5.py:

def check_postgres_health():
    """Check PostgreSQL connection."""
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL', '')
        if DATABASE_URL:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            conn.close()
            return True
    except:
        pass
    return False

def check_redis_health():
    """Check Redis connection."""
    try:
        import redis
        r = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
        r.ping()
        return True
    except:
        return False

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring systems.
    Returns status of all dependencies.
    """
    pg_health = check_postgres_health()
    redis_health = check_redis_health()
    
    status = "healthy" if pg_health else "degraded"
    
    return jsonify({
        "status": status,
        "version": "5.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": {
            "postgresql": {
                "status": "connected" if pg_health else "disconnected",
                "healthy": pg_health
            },
            "redis": {
                "status": "connected" if redis_health else "disconnected", 
                "healthy": redis_health
            },
            "llm_manager": {
                "status": "running",
                "healthy": llm_manager is not None
            }
        },
        "infrastructure": {
            "postgres": "connected" if pg_health else "disconnected",
            "redis": "connected" if redis_health else "disconnected"
        }
    }), 200 if pg_health else 503
