"""
NexusOS Backup & Restore API
"""

import os
import json
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify

def setup_backup_routes(app):
    """Add backup and restore routes"""
    
    @app.route('/api/backup', methods=['POST'])
    def create_backup():
        """Create a backup of database and agent configs"""
        from flask import current_app
        
        backup_dir = os.environ.get('NEXUSOS_BACKUP_DIR', '/opt/nexusos-data/backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{backup_dir}/nexusos_backup_{timestamp}.tar.gz"
        
        # Files to backup
        files_to_backup = [
            '/opt/nexusos-data/nexusos.db',
            '/opt/nexusos-data/agents/',
        ]
        
        # Create tar archive
        try:
            # Filter existing files
            existing_files = [f for f in files_to_backup if os.path.exists(f)]
            
            if existing_files:
                result = subprocess.run(
                    ['tar', '-czf', backup_file] + existing_files,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    size = os.path.getsize(backup_file)
                    return jsonify({
                        'status': 'success',
                        'backup_file': backup_file,
                        'size_bytes': size,
                        'timestamp': timestamp
                    })
                else:
                    return jsonify({'status': 'error', 'message': result.stderr}), 500
            else:
                return jsonify({'status': 'error', 'message': 'No files to backup'}), 400
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/backup', methods=['GET'])
    def list_backups():
        """List available backups"""
        backup_dir = os.environ.get('NEXUSOS_BACKUP_DIR', '/opt/nexusos-data/backups')
        
        if not os.path.exists(backup_dir):
            return jsonify({'backups': []})
        
        backups = []
        for f in os.listdir(backup_dir):
            if f.endswith('.tar.gz'):
                path = os.path.join(backup_dir, f)
                backups.append({
                    'file': f,
                    'size': os.path.getsize(path),
                    'created': datetime.fromtimestamp(os.path.getctime(path)).isoformat()
                })
        
        return jsonify({'backups': sorted(backups, key=lambda x: x['created'], reverse=True)})
    
    @app.route('/api/backup/restore', methods=['POST'])
    def restore_backup():
        """Restore from a backup file"""
        data = request.json or {}
        backup_file = data.get('backup_file')
        
        if not backup_file:
            return jsonify({'status': 'error', 'message': 'backup_file required'}), 400
        
        # Security: only allow restore from within backup dir
        backup_dir = os.environ.get('NEXUSOS_BACKUP_DIR', '/opt/nexusos-data/backups')
        full_path = os.path.abspath(os.path.join(backup_dir, os.path.basename(backup_file)))
        
        if not full_path.startswith(backup_dir):
            return jsonify({'status': 'error', 'message': 'Invalid path'}), 400
        
        if not os.path.exists(full_path):
            return jsonify({'status': 'error', 'message': 'Backup file not found'}), 404
        
        try:
            # Extract to temp location first
            result = subprocess.run(
                ['tar', '-xzf', full_path, '-C', '/'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return jsonify({'status': 'success', 'message': 'Backup restored. Restart required.'})
            else:
                return jsonify({'status': 'error', 'message': result.stderr}), 500
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
