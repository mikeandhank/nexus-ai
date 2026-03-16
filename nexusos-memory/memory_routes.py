"""
Memory Consolidation API Routes

Add to api_server_v5.py:
- GET /api/memory/profile - View what the agent knows about you
- GET /api/memory/timeline - Chronological memory timeline
- POST /api/memory/consolidate - Trigger manual consolidation
"""

from flask import Blueprint, jsonify, request, g

memory_bp = Blueprint('memory', __name__)

def register_memory_routes(app, get_db, get_consolidation, get_memory_visualizer):
    """Register memory consolidation routes"""
    
    @app.route('/api/memory/profile', methods=['GET'])
    @app.route('/api/memory/consolidate', methods=['POST'])
    @app.route('/api/memory/timeline', methods=['GET'])
    
    # Profile: See what the agent knows
    @app.route('/api/memory/profile', methods=['GET'])
    @require_auth
    def memory_profile():
        """Get memory profile showing what the agent knows about you"""
        visualizer = get_memory_visualizer()
        profile = visualizer.get_user_memory_profile(g.user_id)
        return jsonify(profile)
    
    # Timeline: Chronological view
    @app.route('/api/memory/timeline', methods=['GET'])
    @require_auth
    def memory_timeline():
        """Get chronological timeline of memories"""
        days = request.args.get('days', 7, type=int)
        visualizer = get_memory_visualizer()
        timeline = visualizer.get_memory_timeline(g.user_id, days=days)
        return jsonify({'timeline': timeline})
    
    # Trigger consolidation manually
    @app.route('/api/memory/consolidate', methods=['POST'])
    @require_auth
    def trigger_consolidation():
        """Manually trigger memory consolidation"""
        consolidation = get_consolidation()
        result = consolidation.run_consolidation(g.user_id)
        return jsonify({'status': 'completed', 'result': result})
