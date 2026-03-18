"""
SIEM Export - Audit Log Export for Compliance
=============================================
Exports audit logs in formats compatible with Splunk, ELK, SumoLogic, etc.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SIEMExporter:
    """
    SIEM Export for Enterprise Compliance
    
    Supports:
    - Splunk HEC (HTTP Event Collector)
    - Elasticsearch/Bulk API
    - SumoLogic
    - JSON Lines (file-based)
    - Syslog
    """
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.environ.get('DATABASE_URL',
            'postgresql://nexusos:nexusos@localhost:5432/nexusos')
    
    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    # ========== LOG FETCHING ==========
    
    def fetch_logs(self, since: datetime = None, until: datetime = None,
                   user_id: str = None, event_type: str = None,
                   limit: int = 1000) -> List[Dict]:
        """
        Fetch audit logs with filters.
        
        Args:
            since: Start time (default: 24h ago)
            until: End time
            user_id: Filter by user
            event_type: Filter by event type
            limit: Max records to return
        """
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if since:
            query += " AND timestamp >= %s"
            params.append(since)
        
        if until:
            query += " AND timestamp <= %s"
            params.append(until)
        
        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)
        
        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    # ========== SPLUNK EXPORT ==========
    
    def export_splunk(self, logs: List[Dict], hec_url: str, hec_token: str) -> Dict:
        """
        Export logs to Splunk via HEC.
        
        Expected log format:
        {
            "timestamp": "2026-03-16T12:00:00Z",
            "event_type": "user.login",
            "user_id": "user123",
            "ip_address": "192.168.1.1",
            "status": "success",
            "details": {}
        }
        """
        import requests
        
        results = {"success": 0, "failed": 0, "errors": []}
        
        for log in logs:
            event = {
                "time": log.get("timestamp", "").isoformat() if isinstance(log.get("timestamp"), datetime) else log.get("timestamp"),
                "host": "nexusos",
                "source": "nexusos-audit",
                "sourcetype": "nexusos:audit",
                "index": "nexusos",
                "event": log
            }
            
            try:
                response = requests.post(
                    hec_url,
                    json=event,
                    headers={
                        "Authorization": f"Splunk {hec_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Status {response.status_code}")
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(e))
        
        return results
    
    # ========== ELASTICSEARCH EXPORT ==========
    
    def export_elasticsearch(self, logs: List[Dict], es_url: str, 
                           index: str = "nexusos-audit") -> Dict:
        """
        Export logs to Elasticsearch via Bulk API.
        """
        import requests
        
        bulk_lines = []
        
        for log in logs:
            # Index line
            doc_id = log.get("id", "")
            bulk_lines.append(json.dumps({
                "index": {
                    "_index": index,
                    "_id": doc_id
                }
            }))
            
            # Document line
            bulk_lines.append(json.dumps(log))
        
        # Join with newlines
        body = "\n".join(bulk_lines) + "\n"
        
        try:
            response = requests.post(
                f"{es_url}/_bulk",
                data=body.encode(),
                headers={
                    "Content-Type": "application/x-ndjson"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "indexed": result.get("items", []).__len__(),
                    "errors": result.get("errors", False)
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== JSON LINES EXPORT ==========
    
    def export_jsonl(self, logs: List[Dict], filepath: str) -> Dict:
        """
        Export logs to JSON Lines file.
        """
        try:
            with open(filepath, 'w') as f:
                for log in logs:
                    f.write(json.dumps(log) + '\n')
            
            return {
                "success": True,
                "file": filepath,
                "records": len(logs)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== SYSLOG EXPORT ==========
    
    def export_syslog(self, logs: List[Dict], syslog_host: str = "localhost",
                     syslog_port: int = 514) -> Dict:
        """
        Export logs via syslog protocol.
        """
        import socket
        
        results = {"success": 0, "failed": 0}
        
        # RFC 3164 syslog format
        for log in logs:
            timestamp = log.get("timestamp", "")
            event_type = log.get("event_type", "unknown")
            user_id = log.get("user_id", "unknown")
            message = f"NexusOS [{event_type}] user={user_id}"
            
            # Syslog message (RFC 3164)
            syslog_msg = f"<134>{timestamp} nexusos: {message}\n"
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(syslog_msg.encode(), (syslog_host, syslog_port))
                sock.close()
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
        
        return results
    
    # ========== COMPLIANCE EXPORTS ==========
    
    def export_compliance_report(self, since: datetime = None) -> Dict:
        """
        Generate a compliance report with all required fields.
        """
        since = since or (datetime.utcnow() - timedelta(days=30))
        
        logs = self.fetch_logs(since=since)
        
        # Summarize by event type
        by_type = {}
        by_user = {}
        by_status = {}
        
        for log in logs:
            event_type = log.get("event_type", "unknown")
            user_id = log.get("user_id", "unknown")
            status = log.get("status", "unknown")
            
            by_type[event_type] = by_type.get(event_type, 0) + 1
            by_user[user_id] = by_user.get(user_id, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "report_generated": datetime.utcnow().isoformat(),
            "period_start": since.isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "total_events": len(logs),
            "by_event_type": by_type,
            "by_user": by_user,
            "by_status": by_status,
            "logs": logs  # Full log data
        }
    
    # ========== SCHEMA ==========
    
    def get_schema(self) -> Dict:
        """
        Return the audit log schema for SIEM integration.
        """
        return {
            "fields": {
                "timestamp": "ISO8601 timestamp",
                "event_type": "Event category (user.login, agent.start, tool.use, etc.)",
                "user_id": "User identifier",
                "user_email": "User email",
                "ip_address": "Source IP",
                "user_agent": "HTTP user agent",
                "status": "success|failure|error",
                "resource": "Affected resource",
                "action": "Action performed",
                "details": "JSON object with additional context",
                "agent_id": "Agent identifier (if agent event)",
                "tool_name": "Tool used (if tool event)",
                "request_id": "Request tracking ID",
                "session_id": "Session identifier"
            },
            "event_types": [
                "user.login",
                "user.logout", 
                "user.register",
                "user.password_change",
                "agent.create",
                "agent.start",
                "agent.stop",
                "agent.delete",
                "tool.use",
                "api.call",
                "config.change",
                "security.alert"
            ],
            "recommended_indexes": {
                "splunk": "nexusos-audit",
                "elasticsearch": "nexusos-audit",
                "sumologic": "NexusOS/Audit"
            }
        }


# Singleton
_exporter = None

def get_siem_exporter(db_url: str = None) -> SIEMExporter:
    global _exporter
    if _exporter is None:
        _exporter = SIEMExporter(db_url)
    return _exporter
